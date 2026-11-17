import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import cv2, numpy as np, json
B=ROOT_DIR+'artifacts/runs/'
OBS=['044','045','046','047','048']
CFG=json.load(open(ROOT_DIR+'configs/terrain.json'))
FCFG=json.load(open(ROOT_DIR+'configs/filtering.json'))
def load(o):
    d=B+f'r08_quality_batch/obs_{o}/'
    r=dict(L=cv2.imread(d+'rectified_left.png',0),R=cv2.imread(d+'rectified_right.png',0),
           dl=np.load(d+'disparity_left_px.npy'),dr=np.load(d+'disparity_right_px.npy'),lr=np.load(d+'left_right_error_px.npy'),
           v08=cv2.imread(d+'validity_mask.png',0)>0,v11=cv2.imread(B+f'r11_filtered_batch/obs_{o}/validity_mask.png',0)>0,
           prov=json.load(open(d+'provenance.json')))
    for m in ['disparity_range','illuminated','inside_rectification','left_right_consistent','raw_information_present','textured']:
        r['m_'+m]=cv2.imread(d+f'mask_{m}.png',0)>0
    return r
def sgbm(left,right,cfg,reverse=False):
    n,block=cfg['num_disparities'],cfg['block_size']
    low=-cfg['min_disparity']-n+1 if reverse else cfg['min_disparity']
    s=cv2.StereoSGBM_create(minDisparity=low,numDisparities=n,blockSize=block,P1=cfg.get('P1',8*block*block),P2=cfg.get('P2',32*block*block),
        disp12MaxDiff=cfg.get('disp12',1),preFilterCap=31,uniquenessRatio=cfg['uniqueness_ratio'],
        speckleWindowSize=cfg['speckle_window_size'],speckleRange=cfg['speckle_range'],mode=cfg.get('mode',cv2.STEREO_SGBM_MODE_SGBM_3WAY))
    if cfg.get('pad_search',True):
        left=np.pad(left,((0,0),(n,n)));right=np.pad(right,((0,0),(n,n)))
        return s.compute(left,right)[:,n:-n].astype(np.float32)/16.
    return s.compute(left,right).astype(np.float32)/16.
def lrcheck(dl,dr):
    yy,xx=np.indices(dl.shape,dtype=np.float32)
    sampled=cv2.remap(dr,xx-dl,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=-10000)
    return np.abs(dl+sampled),sampled
NEAR=slice(683,1024); MID=slice(341,683)
def sift_matches(L,R,ratio=0.75,maxdy=1.5):
    s=cv2.SIFT_create(nfeatures=20000)
    ka,da=s.detectAndCompute(L,None); kb,db=s.detectAndCompute(R,None)
    m=cv2.BFMatcher().knnMatch(da,db,k=2)
    good=[a for a,b in m if a.distance<ratio*b.distance]
    pa=np.array([ka[g.queryIdx].pt for g in good]); pb=np.array([kb[g.trainIdx].pt for g in good])
    ok=(np.abs(pa[:,1]-pb[:,1])<maxdy)&(pa[:,0]-pb[:,0]>0)
    return pa[ok],pb[ok]
def inside_left(r):
    return r['m_inside_rectification'] | (cv2.warpPerspective(np.full((1024,1024),255,np.uint8),np.array(r['prov']['homographies'][0]),(1024,1024))==255)
