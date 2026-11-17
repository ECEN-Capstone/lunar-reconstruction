import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, json, pickle, time
sys.path.insert(0,_HERE)
from common import *
SIFT = pickle.load(open(OUT_DIR+'sift.pkl', 'rb'))
RAW = ROOT_DIR+'chandrayaan-3-navcam-sorted/'

def raw_good(r):
    ob = r['prov']['observation']; H = [np.array(h) for h in r['prov']['homographies']]
    good = []
    for k, h in zip(['nrl_left_path', 'nrr_right_path'], H):
        src = cv2.imread(RAW + ob[k], 0)
        bad = ((src <= 5) | (src >= 250)).astype(np.uint8); bad = cv2.dilate(bad, np.ones((3, 3), np.uint8))
        good.append(cv2.warpPerspective((1 - bad) * 255, h, (1024, 1024)) == 255)
        if k == 'nrl_left_path':  # undilated: only the pixel itself clipped
            b0 = ((src <= 5) | (src >= 250)).astype(np.uint8) * 255
            left_nodil = cv2.warpPerspective(b0, h, (1024, 1024)) < 128
    good.append(left_nodil)
    return good

def downstream(r, dl, lr, sampled, rawg, raw_mode='strict'):
    """r08 per-pixel filters then r11 support filter, as in stereo.py / filter_clouds.py."""
    yy, xx = np.indices(dl.shape, dtype=np.float32); xr = xx - dl
    H = [np.array(h) for h in r['prov']['homographies']]
    ml = cv2.warpPerspective(np.full((1024, 1024), 255, np.uint8), H[0], (1024, 1024)) == 255
    mr = cv2.warpPerspective(np.full((1024, 1024), 255, np.uint8), H[1], (1024, 1024)) == 255
    right_valid = cv2.remap(mr.astype(np.uint8), xr, yy, cv2.INTER_NEAREST) > 0
    right_int = cv2.remap(r['R'], xr, yy, cv2.INTER_LINEAR)
    im = r['L'].astype(np.float32); w = (7, 7)
    std = np.sqrt(np.maximum(cv2.boxFilter(im * im, -1, w) - cv2.boxFilter(im, -1, w) ** 2, 0))
    f = dict(inside=ml & right_valid & (xr >= 0) & (xr < 1023),
             range=(dl >= 16) & (dl < 511),
             lr=(lr <= 1) & (sampled <= -16),
             illum=(r['L'] > 5) & (r['L'] < 250) & (right_int > 5) & (right_int < 250),
             textured=std >= 2,
             rawinfo=(rawg[0] & (cv2.remap(rawg[1].astype(np.uint8), xr, yy, cv2.INTER_NEAREST) > 0)) if raw_mode == 'strict' else rawg[2])
    v08 = np.logical_and.reduce(list(f.values()))
    # r11
    src = np.zeros((1024, 1024), np.uint8); src[16:-16, 16:-16] = 255
    gl = cv2.warpPerspective(src, H[0], (1024, 1024)) == 255; gr = cv2.warpPerspective(src, H[1], (1024, 1024)) == 255
    right_ok = cv2.remap(gr.astype(np.uint8), xr, yy, cv2.INTER_NEAREST) > 0
    med = cv2.medianBlur(dl, 5)
    nb = cv2.boxFilter(v08.astype(np.float32), -1, (5, 5), normalize=False)
    v11 = v08 & gl & right_ok & (dl >= 32) & (np.abs(dl - med) <= 2) & (nb >= 8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(v11.astype(np.uint8), 8)
    keep = st[:, cv2.CC_STAT_AREA] >= 200; keep[0] = False; v11 &= keep[lab]
    return f, v08, v11, ml

def sift_agree(o, dl, mask):
    pa, pb = SIFT[o]['pa'][0::2], SIFT[o]['pb'][0::2]; ix = np.rint(pa[:, 0]).astype(int); iy = np.rint(pa[:, 1]).astype(int)
    near = iy >= 683; ok = near & mask[iy, ix]
    if ok.sum() == 0: return dict(n_sift_near=int(near.sum()), n_eval=0)
    e = np.abs(dl[iy[ok], ix[ok]] - (pa[ok, 0] - pb[ok, 0]))
    return dict(n_sift_near=int(near.sum()), n_eval=int(ok.sum()), recall=float(ok.sum() / near.sum()),
                med_err=float(np.median(e)), within1=float((e <= 1).mean()), within3=float((e <= 3).mean()))

def ground_prior(o, r=None, source='sift'):
    """Robust plane d = a x + b y + c fitted to near-field rows >= 600.
    source='sift': SIFT matches (odd-indexed only, even ones kept for evaluation);
    source='pass1': the existing r08 SGBM left-right-consistent disparities (no SIFT)."""
    if source == 'sift':
        pa, pb = SIFT[o]['pa'][1::2], SIFT[o]['pb'][1::2]; d = pa[:, 0] - pb[:, 0]; sel = pa[:, 1] >= 600
        X = np.c_[pa[sel, 0], pa[sel, 1], np.ones(sel.sum())]; dd = d[sel]
    else:
        ok = (r['lr'] <= 1) & (r['dl'] >= 16); ok[:600] = False; ok &= r['m_inside_rectification']
        yy, xx = np.nonzero(ok); idx = np.random.default_rng(0).choice(len(yy), min(20000, len(yy)), replace=False)
        yy, xx = yy[idx], xx[idx]; dd = r['dl'][yy, xx]; X = np.c_[xx, yy, np.ones(len(yy))]
    w = np.ones(len(dd), bool)
    for _ in range(8):
        c, *_ = np.linalg.lstsq(X[w], dd[w], rcond=None); res = dd - X @ c
        s = max(1.4826 * np.median(np.abs(res[w])), 2); w = np.abs(res) < 3 * s
    return c, float(w.mean()), float(np.median(np.abs(res[w])))

def run_variant(r, name, o):
    L, R = r['L'], r['R']; cfg = dict(CFG)
    if name == 'r08':
        dl, dr = r['dl'], r['dr']
    elif name == 'relaxed':
        cfg.update(uniqueness_ratio=5, speckle_window_size=0); dl = sgbm(L, R, cfg); dr = sgbm(R, L, cfg, True)
    elif name.startswith('block'):
        b = int(name[5:]); cfg.update(block_size=b); dl = sgbm(L, R, cfg); dr = sgbm(R, L, cfg, True)
    elif name.startswith('half'):
        Ls = cv2.resize(L, (512, 512), interpolation=cv2.INTER_AREA); Rs = cv2.resize(R, (512, 512), interpolation=cv2.INTER_AREA)
        cfg.update(num_disparities=256)
        if name == 'half_relaxed': cfg.update(uniqueness_ratio=5, speckle_window_size=0)
        a = sgbm(Ls, Rs, cfg); b = sgbm(Rs, Ls, cfg, True)
        up = lambda z: np.where(cv2.resize(z, (1024, 1024), interpolation=cv2.INTER_NEAREST) == cv2.resize(z, (1024, 1024), interpolation=cv2.INTER_NEAREST), cv2.resize(z, (1024, 1024), interpolation=cv2.INTER_LINEAR), 0) * 2
        # invalid stays invalid: SGBM invalid = minDisparity-1 (scaled); mark explicitly
        inva = cv2.resize((a < 0).astype(np.uint8), (1024, 1024), interpolation=cv2.INTER_NEAREST) > 0
        invb = cv2.resize((b > 0).astype(np.uint8) | (b <= -256).astype(np.uint8), (1024, 1024), interpolation=cv2.INTER_NEAREST) > 0
        dl = cv2.resize(a, (1024, 1024), interpolation=cv2.INTER_LINEAR) * 2; dl[inva] = -1 / 16
        dr = cv2.resize(b, (1024, 1024), interpolation=cv2.INTER_LINEAR) * 2; dr[invb] = 1 / 16
    elif name.startswith('slant'):
        c, inl, res = ground_prior(o, r, 'pass1' if 'pass1' in name else 'sift')
        yy, xx = np.indices(L.shape, dtype=np.float32)
        dg = np.clip(c[0] * xx + c[1] * yy + c[2], 0, None).astype(np.float32)
        Rw = cv2.remap(R, xx - dg, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        cfg.update(min_disparity=-64, num_disparities=192)
        if 'relaxed' in name: cfg.update(uniqueness_ratio=5, speckle_window_size=0)
        rl = sgbm(L, Rw, cfg)
        # reverse: right' -> left; SGBM reverse sign convention in sgbm(): low=-min-n+1
        rr = sgbm(Rw, L, cfg, True)
        invl = rl < -64; invr = rr > 64
        # LR check in warped domain
        lrw, sampw = lrcheck(rl, rr)
        dl = (dg + rl * (1 - c[0])).astype(np.float32); dl[invl] = -1 / 16  # exact: d = r + dg(x - r, y)
        # express as standard (lr, sampled) for downstream: consistency computed in warped domain
        lr = np.where(invl, 99, lrw).astype(np.float32); sampled = np.where(invl, 0, -dl).astype(np.float32)
        lr[np.abs(sampw) > 1000] = 99
        return dl, lr, sampled, dict(prior=c.tolist(), prior_inlier=inl, prior_med_res=res)
    lr, sampled = lrcheck(dl, dr)
    return dl, lr, sampled, {}

if __name__ == '__main__':
    names = sys.argv[1].split(','); obs = sys.argv[2].split(',') if len(sys.argv) > 2 else OBS
    out = {}
    for o in obs:
        r = load(o); rawg = raw_good(r)
        for nm in names:
            t = time.time(); dl, lr, sampled, extra = run_variant(r, nm, o)
            f, v08, v11, ml = downstream(r, dl, lr, sampled, rawg)
            den = ml[NEAR]; midden = ml[MID]
            ret = (dl >= 0) if not nm.startswith('slant') else (lr < 99)
            cons = ret & (lr <= 1)
            rec = dict(returned=float(ret[NEAR][den].mean()), lr_consistent=float(cons[NEAR][den].mean()),
                       after_r08=float(v08[NEAR][den].mean()), after_r11=float(v11[NEAR][den].mean()),
                       mid_lr_consistent=float(cons[MID][midden].mean()), mid_after_r11=float(v11[MID][midden].mean()),
                       sift_vs_lrcons=sift_agree(o, dl, cons), seconds=round(time.time() - t, 1), **extra)
            # near-field LR error median among returned
            rec['near_lr_err_med'] = float(np.median(lr[NEAR][den & ret[NEAR]])) if (den & ret[NEAR]).any() else None
            rec['mid_lr_err_med'] = float(np.median(lr[MID][midden & ret[MID]])) if (midden & ret[MID]).any() else None
            out[f'{o}/{nm}'] = rec
            np.save(OUT_DIR+f'd_{o}_{nm}.npy', np.where(cons, dl, np.nan).astype(np.float32))
            np.save(OUT_DIR+f'v_{o}_{nm}.npy', np.stack([v08, v11]))
            print(o, nm, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec.items() if k not in ('prior',)}), flush=True)
    json.dump(out, open(OUT_DIR+'variants_' + sys.argv[1].replace(',', '_') + '.json', 'w'), indent=1)
