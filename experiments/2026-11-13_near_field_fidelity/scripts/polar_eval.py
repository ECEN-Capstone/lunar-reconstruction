import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, json, glob, os; sys.path.insert(0,_HERE)
from polar_common import *
from common import sgbm, lrcheck, CFG, sift_matches
f=1991.49; cx=965.756; cy=599.847; B=float(np.linalg.norm(T))
R1,R2,P1,P2,Q,_,_=cv2.stereoRectify(K1,D1,K2,D2,S,R,T,flags=cv2.CALIB_ZERO_DISPARITY,alpha=1)
Kn=np.array([[f,0,cx],[0,f,cy],[0,0,1]])
mL=cv2.initUndistortRectifyMap(K1,D1,R1,Kn,S,cv2.CV_32FC1); mR=cv2.initUndistortRectifyMap(K2,D2,R2,Kn,S,cv2.CV_32FC1)
def gt_disp(pos):
    g=cv2.imread(D+f'GroundTruth_RectifiedRangeMaps/Terrain03/{pos}_org-XYZ.tif',cv2.IMREAD_UNCHANGED).astype(np.float64)/1000
    ok=np.isfinite(g).all(2)&(np.abs(g).sum(2)>0); v=np.load(OUT_DIR+f'polar_{pos}_KRC.npy'); Rm=v[9:18].reshape(3,3)
    Z=-(g@Rm[2]); d=np.where(ok&(Z>0),f*B/np.where(Z>0,Z,1),np.nan); return d.astype(np.float32),np.where(ok,Z,np.nan)
def downstream(L,Rimg,dl,lr,sampled,valid_rect):
    yy,xx=np.indices(dl.shape,dtype=np.float32); xr=xx-dl
    right_valid=cv2.remap(valid_rect[1].astype(np.uint8),xr,yy,cv2.INTER_NEAREST)>0
    ri=cv2.remap(Rimg,xr,yy,cv2.INTER_LINEAR); im=L.astype(np.float32)
    std=np.sqrt(np.maximum(cv2.boxFilter(im*im,-1,(7,7))-cv2.boxFilter(im,-1,(7,7))**2,0))
    bad=[cv2.dilate(((x<=5)|(x>=250)).astype(np.uint8),np.ones((3,3),np.uint8))==0 for x in (L,Rimg)]
    fl=dict(inside=valid_rect[0]&right_valid&(xr>=0)&(xr<dl.shape[1]-1),range=(dl>=16)&(dl<511),lr=(lr<=1)&(sampled<=-16),
        illum=(L>5)&(L<250)&(ri>5)&(ri<250),textured=std>=2,rawinfo=bad[0]&(cv2.remap(bad[1].astype(np.uint8),xr,yy,cv2.INTER_NEAREST)>0))
    v08=np.logical_and.reduce(list(fl.values()))
    med=cv2.medianBlur(dl,5); nb=cv2.boxFilter(v08.astype(np.float32),-1,(5,5),normalize=False)
    b=np.zeros(dl.shape,bool); b[16:-16,16:-16]=True
    v11=v08&b&(dl>=32)&(np.abs(dl-med)<=2)&(nb>=8)
    n,lab,st,_=cv2.connectedComponentsWithStats(v11.astype(np.uint8),8); keep=st[:,cv2.CC_STAT_AREA]>=200; keep[0]=False; v11&=keep[lab]
    return v08,v11
def slant(L,Rimg,dgt_first):
    ok=np.isfinite(dgt_first)
    yy,xx=np.nonzero(ok); idx=np.random.default_rng(0).choice(len(yy),min(20000,len(yy)),replace=False)
    X=np.c_[xx[idx],yy[idx],np.ones(len(idx))]; dd=dgt_first[yy[idx],xx[idx]]; w=np.ones(len(dd),bool)
    for _ in range(8):
        c,*_=np.linalg.lstsq(X[w],dd[w],rcond=None); res=dd-X@c; w=np.abs(res)<3*max(1.4826*np.median(np.abs(res[w])),2)
    Y,Xg=np.indices(L.shape,dtype=np.float32); dg=np.clip(c[0]*Xg+c[1]*Y+c[2],0,None).astype(np.float32)
    Rw=cv2.remap(Rimg,Xg-dg,Y,cv2.INTER_LINEAR); cfg=dict(CFG); cfg.update(min_disparity=-64,num_disparities=192)
    rl=sgbm(L,Rw,cfg); rr=sgbm(Rw,L,cfg,True); lrw,sw=lrcheck(rl,rr)
    dl=(dg+rl*(1-c[0])).astype(np.float32); inv=rl<-64; dl[inv]=-1/16
    lr=np.where(inv,99,lrw).astype(np.float32); lr[np.abs(sw)>1000]=99; sampled=np.where(inv,0,-dl).astype(np.float32)
    return dl,lr,sampled,c
res={}; keep={}
for pos in ['PosA','PosC']:
    dgt,Zgt=gt_disp(pos); okgt=np.isfinite(dgt)
    rows=np.nonzero(okgt.any(1))[0]; r0,r1=rows[0],rows[-1]; near=np.zeros_like(okgt); near[r0+2*(r1-r0)//3:r1+1]=True; near&=okgt
    # GT ground shear in the near band: d vs row
    yy,xx=np.nonzero(near); A=np.c_[xx,yy,np.ones(len(xx))]; cg,*_=np.linalg.lstsq(A,dgt[near],rcond=None)
    for fn in sorted(glob.glob(D+f'sel2/{pos}_1500_Loff_*_L_*.png')):
        tag=os.path.basename(fn).replace('_L_','_').replace('.png','')
        Lr=cv2.remap(np.clip(cv2.imread(fn,-1)/16,0,255).astype(np.uint8),*mL,cv2.INTER_LINEAR)
        Rr=cv2.remap(np.clip(cv2.imread(fn.replace('_L_','_R_'),-1)/16,0,255).astype(np.uint8),*mR,cv2.INTER_LINEAR)
        pa,pb=sift_matches(Lr,Rr,maxdy=3); ix=np.rint(pa[:,0]).astype(int); iy=np.rint(pa[:,1]).astype(int); gg=dgt[iy,ix]; okk=np.isfinite(gg)
        ee=(pa[okk,0]-pb[okk,0])-gg[okk]; A=np.c_[pa[okk,0],pa[okk,1],np.ones(okk.sum())]; w=np.ones(len(ee),bool)
        for _ in range(5):
            cb,*_=np.linalg.lstsq(A[w],ee[w],rcond=None); rr_=ee-A@cb; w=np.abs(rr_)<3*max(1.4826*np.median(np.abs(rr_[w])),.3)
        Y_,X_=np.indices(dgt.shape); dgt_c=dgt+(cb[0]*X_+cb[1]*Y_+cb[2]).astype(np.float32); Zc=f*B/dgt_c
        vr=[cv2.remap(np.full(S[::-1],255,np.uint8),*m,cv2.INTER_NEAREST)==255 for m in (mL,mR)]
        out={'near_rows':[int(r0+2*(r1-r0)//3),int(r1)],'gt_near_depth_m':np.nanpercentile(Zgt[near],[5,50,95]).round(2).tolist(),
             'gt_near_shear_px_per_row':float(cg[1]),'gt_near_disp':np.nanpercentile(dgt[near],[5,95]).round(0).tolist(),
             'gt_alignment_correction_from_SIFT':cb.tolist(),'sift_vs_gt_resid_MAD_px':float(np.median(np.abs(rr_[w]))),'n_sift':int(okk.sum()),
             'near_median_DN8':float(np.median(Lr[near]))}
        for var in ['production','slanted']:
            if var=='production':
                dl=sgbm(Lr,Rr,CFG); dr=sgbm(Rr,Lr,CFG,True); lr,sampled=lrcheck(dl,dr); ret=dl>=0
            else:
                dl,lr,sampled,c=slant(Lr,Rr,np.where(near,keep['dl'],np.nan)); ret=lr<99
            v08,v11=downstream(Lr,Rr,dl,lr,sampled,vr); cons=ret&(lr<=1)
            e=np.abs(dl-dgt_c)
            rec={}
            for band,m in [('near',near),('all',okgt)]:
                n=m.sum()
                rec[band]=dict(returned=float((ret&m).sum()/n),lr_consistent=float((cons&m).sum()/n),after_r08=float((v08&m).sum()/n),after_r11=float((v11&m).sum()/n),
                    r11_median_err_px=float(np.median(e[v11&m])) if (v11&m).any() else None,r11_within1px=float((e[v11&m]<=1).mean()) if (v11&m).any() else None,
                    r11_median_depth_err_mm=float(1000*np.median(np.abs(f*B/dl[v11&m]-Zc[v11&m]))) if (v11&m).any() else None,
                    lrcons_within1px=float((e[cons&m]<=1).mean()) if (cons&m).any() else None)
            out[var]=rec
            if var=='production': keep['dl']=np.where(cons,dl,np.nan)
            np.save(OUT_DIR+f'polar_{tag}_{var}_v11.npy',v11)
        cv2.imwrite(OUT_DIR+f'polar_{tag}_L.png',Lr); np.save(OUT_DIR+f'polar_{pos}_dgt.npy',dgt)
        res[tag]=out
        p,s=out['production']['near'],out['slanted']['near']
        print(tag,'shear %.2f px/row'%out['gt_near_shear_px_per_row'],'near depth',out['gt_near_depth_m'],'| PROD ret %.2f lr %.2f r08 %.2f r11 %.2f err %.2fpx w1 %.2f dz %.1fmm'%(p['returned'],p['lr_consistent'],p['after_r08'],p['after_r11'],p['r11_median_err_px'] or -1,p['r11_within1px'] or -1,p['r11_median_depth_err_mm'] or -1),
              '| SLANT lr %.2f r11 %.2f err %.2f w1 %.2f'%(s['lr_consistent'],s['after_r11'],s['r11_median_err_px'] or -1,s['r11_within1px'] or -1),flush=True)
json.dump(res,open(OUT_DIR+'polar_stereo.json','w'),indent=1)
