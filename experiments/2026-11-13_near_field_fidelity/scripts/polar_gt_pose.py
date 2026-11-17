"""POLAR Stereo: recover the projection of the organized ground-truth maps (DLT on pixel grid -> K, R; camera at origin)."""
import os, sys; _HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,_HERE)
from polar_common import *
from scipy.linalg import rq
OUT_DIR=os.environ.get('NF_OUT',os.path.join(_HERE,'..','results'))+'/'
for pos in ['PosA','PosC']:
    g=cv2.imread(D+f'GroundTruth_RectifiedRangeMaps/Terrain03/{pos}_org-XYZ.tif',cv2.IMREAD_UNCHANGED).astype(np.float64)/1000
    ok=np.isfinite(g).all(2)&(np.abs(g).sum(2)>0); yy,xx=np.nonzero(ok); P=g[ok]
    idx=np.random.default_rng(2).choice(len(P),4000,replace=False); A=[]
    for (x,y,z),uu,vv in zip(P[idx],xx[idx].astype(float),yy[idx].astype(float)):
        A.append([x,y,z,1,0,0,0,0,-uu*x,-uu*y,-uu*z,-uu]); A.append([0,0,0,0,x,y,z,1,-vv*x,-vv*y,-vv*z,-vv])
    Pm=np.linalg.svd(np.array(A))[2][-1].reshape(3,4); Pm/=np.linalg.norm(Pm[2,:3])
    K,Rm=rq(Pm[:,:3]); Sg=np.diag(np.sign(np.diag(K))); K=K@Sg; Rm=Sg@Rm
    if np.linalg.det(Rm)<0: Pm=-Pm; K,Rm=rq(Pm[:,:3]); Sg=np.diag(np.sign(np.diag(K))); K=K@Sg; Rm=Sg@Rm
    K=K/K[2,2]; Cc=-np.linalg.inv(Pm[:,:3])@Pm[:,3]
    print(pos,'K',np.round(K,2).tolist(),'C',Cc.round(4)); np.save(OUT_DIR+f'polar_{pos}_KRC.npy',np.r_[K.ravel(),Rm.ravel(),Cc])
