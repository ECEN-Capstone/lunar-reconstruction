"""Inventory every source file and assess stereo geometry before dense matching."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import cv2
from PIL import Image, ImageDraw
from .geometry import ROOT, CAL, camera, decompose, rectification, transform_pixels

DATA = ROOT / 'chandrayaan-3-navcam-sorted'
OUT = ROOT / 'artifacts/investigation'


def matches(left, right):
    """Mutual SIFT ratio matches, then robust F used only to reject outliers."""
    sift = cv2.SIFT_create(nfeatures=8000, contrastThreshold=0.02)
    ka, da = sift.detectAndCompute(left, None)
    kb, db = sift.detectAndCompute(right, None)
    if da is None or db is None:
        return np.empty((0, 2)), np.empty((0, 2))
    bf = cv2.BFMatcher()
    forward = [(a.queryIdx,a.trainIdx) for a,b in bf.knnMatch(da,db,k=2) if a.distance < .75*b.distance]
    backward = {(a.trainIdx,a.queryIdx) for a,b in bf.knnMatch(db,da,k=2) if a.distance < .75*b.distance}
    mutual = [p for p in forward if p in backward]
    a = np.float32([ka[i].pt for i,j in mutual]).reshape(-1,2)
    b = np.float32([kb[j].pt for i,j in mutual]).reshape(-1,2)
    if len(a) < 12:
        return a,b
    _, mask = cv2.findFundamentalMat(a,b,cv2.FM_RANSAC,1.,.999)
    if mask is None:
        return a[:0],b[:0]
    return a[mask.ravel()>0], b[mask.ravel()>0]


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cv2.setNumThreads(4)
    cv2.setRNGSeed(42)
    files, duplicates = [], defaultdict(list)
    for root in [DATA, ROOT/'chandrayaan-3-documentation']:
        for p in sorted(root.rglob('*')):
            if not p.is_file(): continue
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            rec = dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=digest)
            if p.suffix == '.png':
                with Image.open(p) as im:
                    ar = np.array(im)
                    rec.update(size=im.size,mode=im.mode,metadata=im.info,min=int(ar.min()),max=int(ar.max()),mean=float(ar.mean()),dark_fraction=float((ar<=5).mean()),saturated_fraction=float((ar>=250).mean()))
                    duplicates[hashlib.sha256(ar.tobytes()).hexdigest()].append(rec['path'])
            elif p.suffix == '.xml':
                tree = ET.parse(p)
                rec['xml_root'] = tree.getroot().tag
                rec['xml_fields'] = {e.tag.split('}')[-1]:e.text.strip() for e in tree.iter() if e.text and e.text.strip() and len(e)==0}
            elif p.parent == CAL and p.suffix == '.txt' and any(s in p.name for s in ['_gain', '_offset']):
                ar = np.loadtxt(p,delimiter=',')
                rec.update(shape=ar.shape,min=float(ar.min()),max=float(ar.max()),finite=bool(np.isfinite(ar).all()))
            files.append(rec)
    (OUT/'inventory.json').write_text(json.dumps(files,indent=2))
    (OUT/'duplicate_pixels.json').write_text(json.dumps([v for v in duplicates.values() if len(v)>1],indent=2))
    cal = {}
    for side in ['left','right']:
        c,m = camera(side); k,r = decompose(m)
        cal[side] = dict(C=c.tolist(),M=m.tolist(),A_norm=float(np.linalg.norm(m[2])),K=k.tolist(),R=r.tolist())
    k,r,b,hs = rectification()
    cal.update(baseline_calibration_units=b,rectified_K=k.tolist(),rectified_R=r.tolist(),homographies=[h.tolist() for h in hs],units='unspecified in source')
    (OUT/'calibration.json').write_text(json.dumps(cal,indent=2))
    rows = list(csv.DictReader((DATA/'stereo_pairs.csv').open()))
    results=[]
    sheet=Image.new('RGB',(8*180,7*204),'#222222'); draw=ImageDraw.Draw(sheet)
    for n,row in enumerate(rows):
        imgs=[cv2.imread(str(DATA/row[key]),cv2.IMREAD_GRAYSCALE) for key in ['nrl_left_path','nrr_right_path']]
        assert all(im.shape==(1024,1024) for im in imgs)
        a,bp=matches(*imgs)
        np.savez_compressed(OUT/(row['observation_id']+'_matches.npz'),left=a,right=bp)
        rec=dict(observation=row['observation_id'],matches=len(a))
        for interpretation in ['literal','normalize_axis_only']:
            _,_,_,h=rectification(interpretation=interpretation)
            if len(a):
                aa,bb=transform_pixels(a,h[0]),transform_pixels(bp,h[1])
                residual=aa[:,1]-bb[:,1]
                rec[interpretation]=dict(median_abs_y=float(np.median(abs(residual))),p90_abs_y=float(np.percentile(abs(residual),90)),median_signed_y=float(np.median(residual)),median_disparity=float(np.median(aa[:,0]-bb[:,0])),within_1px=float((abs(residual)<1).mean()))
        results.append(rec)
        im=Image.fromarray(imgs[0]).resize((180,180)); x,y=(n%8)*180,(n//8)*204
        sheet.paste(im,(x,y)); draw.text((x+4,y+182),f"{row['observation_id']}  MID {row['sequence_id']}",fill='white')
        print(json.dumps(rec),flush=True)
        (OUT/'stereo_geometry.json').write_text(json.dumps(results,indent=2))
    sheet.save(OUT/'raw_left_contact_sheet.jpg')


if __name__=='__main__': main()
