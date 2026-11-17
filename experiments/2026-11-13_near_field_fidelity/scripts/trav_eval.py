import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, json, glob, os, re; sys.path.insert(0,_HERE)
import cv2, numpy as np
from common import sgbm, lrcheck, CFG, sift_matches
D=POLAR_DIR+'trav/'
def ym(p,k):
    fs=cv2.FileStorage(p,cv2.FILE_STORAGE_READ); return fs.getNode(k).mat()
K1=ym(D+'left_intrinsics.yml','camera_matrix');D1=ym(D+'left_intrinsics.yml','distortion_coefficients')
K2=ym(D+'right_intrinsics.yml','camera_matrix');D2=ym(D+'right_intrinsics.yml','distortion_coefficients')
R=ym(D+'extrinsics.yml','rotation_matrix');T=ym(D+'extrinsics.yml','translation_vector')
S=(2048,2048); R1,R2,P1,P2,Q,_,_=cv2.stereoRectify(K1,D1,K2,D2,S,R,T,flags=cv2.CALIB_ZERO_DISPARITY,alpha=0,newImageSize=(1024,1024))
mL=cv2.initUndistortRectifyMap(K1,D1,R1,P1,(1024,1024),cv2.CV_32FC1); mR=cv2.initUndistortRectifyMap(K2,D2,R2,P2,(1024,1024),cv2.CV_32FC1)
f=P1[0,0]; B=float(np.linalg.norm(T)); print('rectified f %.1f (1024 px) baseline %.3f m'%(f,B))
sys.argv=['x']; 
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import polar_eval_lib as PL
res={}
H=1024; NEAR=slice(2*H//3,H)
for fn in sorted(glob.glob(D+'T*_L_*.png')):
    tag=os.path.basename(fn)[:7]; t=int(tag[1])
    L=cv2.remap(cv2.imread(fn,0),*mL,cv2.INTER_AREA if False else cv2.INTER_LINEAR); Rr=cv2.remap(cv2.imread(fn.replace('_L_','_R_'),0),*mR,cv2.INTER_LINEAR)
    vr=[cv2.remap(np.full((2048,2048),255,np.uint8),*m,cv2.INTER_NEAREST)==255 for m in (mL,mR)]
    # residual vertical misalignment (rig moved between mounts): fit dy = a x + b y + c on SIFT, warp right image rows
    qa,qb=sift_matches(L,Rr,maxdy=8); dy=qa[:,1]-qb[:,1]; A=np.c_[qb[:,0],qb[:,1],np.ones(len(dy))]; w=np.abs(dy-np.median(dy))<2
    for _ in range(4):
        cy_,*_=np.linalg.lstsq(A[w],dy[w],rcond=None); w=np.abs(dy-A@cy_)<1
    dy_before=float(np.median(np.abs(dy)))
    Yg,Xg=np.indices(Rr.shape,dtype=np.float32); Rr=cv2.remap(Rr,Xg,(Yg-(cy_[0]*Xg+cy_[1]*Yg+cy_[2])).astype(np.float32),cv2.INTER_LINEAR)
    vr[1]=cv2.remap(vr[1].astype(np.uint8),Xg,(Yg-(cy_[0]*Xg+cy_[1]*Yg+cy_[2])).astype(np.float32),cv2.INTER_NEAREST)>0
    pa,pb=sift_matches(L,Rr); d=pa[:,0]-pb[:,0]; near=pa[:,1]>=2*H//3
    X=np.c_[pa[near,0],pa[near,1],np.ones(near.sum())]; w=np.ones(near.sum(),bool)
    for _ in range(6):
        c,*_=np.linalg.lstsq(X[w],d[near][w],rcond=None); rr=d[near]-X@c; w=np.abs(rr)<3*max(1.4826*np.median(np.abs(rr[w])),1)
    out=dict(vertical_misalignment_before_px=dy_before,vertical_resid_after_px=float(np.median(np.abs(pa[:,1]-pb[:,1]))),traverse=t,height_m={1:1.3,2:1.3,4:0.65,5:0.65}[t],pitch_deg={1:14,2:25,4:14,5:25}[t],near_shear_px_per_row=float(c[1]),near_sift_disp_med=float(np.median(d[near])),n_sift_near=int(near.sum()))
    first=None
    for var in ['production','slanted']:
        if var=='production':
            dl=sgbm(L,Rr,CFG); dr=sgbm(Rr,L,CFG,True); lr,sampled=lrcheck(dl,dr); ret=dl>=0
        else:
            nearmask=np.zeros(L.shape,bool); nearmask[NEAR]=True
            dl,lr,sampled,_=PL.slant(L,Rr,np.where(nearmask,first,np.nan)); ret=lr<99
        v08,v11=PL.downstream(L,Rr,dl,lr,sampled,vr); cons=ret&(lr<=1)
        ml=vr[0][NEAR]
        ix=np.rint(pa[near,0]).astype(int); iy=np.rint(pa[near,1]).astype(int); okc=cons[iy,ix]; e=np.abs(dl[iy,ix]-d[near])[okc]
        out[var]=dict(returned=float(ret[NEAR][ml].mean()),lr_consistent=float(cons[NEAR][ml].mean()),after_r08=float(v08[NEAR][ml].mean()),after_r11=float(v11[NEAR][ml].mean()),
                      sift_med_err=float(np.median(e)) if len(e) else None,sift_within1=float((e<=1).mean()) if len(e) else None)
        if var=='production': first=np.where(cons,dl,np.nan)
    res[tag]=out
    p,s=out['production'],out['slanted']
    print(tag,'h %.2f pitch %d shear %.2f dy %.2f->%.2f'%(out['height_m'],out['pitch_deg'],out['near_shear_px_per_row'],dy_before,out['vertical_resid_after_px']),'| PROD ret %.2f lr %.2f r08 %.2f r11 %.2f'%(p['returned'],p['lr_consistent'],p['after_r08'],p['after_r11']),'| SLANT lr %.2f r08 %.2f r11 %.2f sift %.2f/%.2f'%(s['lr_consistent'],s['after_r08'],s['after_r11'],s['sift_med_err'] or -1,s['sift_within1'] or -1),flush=True)
json.dump(res,open(OUT_DIR+'polar_traverse.json','w'),indent=1)
