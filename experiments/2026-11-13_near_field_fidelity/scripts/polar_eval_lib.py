import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, json, glob, os; sys.path.insert(0,_HERE)
import cv2, numpy as np
from common import sgbm, lrcheck, CFG, sift_matches

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
