import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, json, io, contextlib; sys.path.insert(0,_HERE)
with contextlib.redirect_stdout(io.StringIO()):
    from trace import load, C, G, TR, np
from scipy.spatial import Delaunay
U=ROOT_DIR+''
f=1400.9789644404393
def xyz_from(dl,valid,Bm):
    yy,xx=np.indices(dl.shape); Z=np.where(valid,f*Bm/np.where(valid,dl,1),np.nan)
    return np.stack([(xx-511.5)*Z/f,(yy-511.5)*Z/f,Z],-1)
def fuse(variant):
    pts=[];ids=[]
    for i,key in enumerate(TR):
        o=key[4:]; r=load(o); Bm=r['prov']['baseline_calibration_units']
        if variant=='production': dl=r['dl']; v=r['v11']
        else: dl=np.load(OUT_DIR+f'dl_{o}_{variant}.npy'); v=np.load(OUT_DIR+f'v11_{o}_{variant}.npy')
        ar=xyz_from(dl,v,Bm)[::2,::2]; ok=np.isfinite(ar).all(2); p=ar[ok]; T=np.array(TR[key]); p=p@T[:3,:3].T+T[:3,3]
        pts.append(p); ids.append(np.full(len(p),i))
    P=np.concatenate(pts); I=np.concatenate(ids); vox=Bm*0.025
    cells=np.floor(P/vox).astype(np.int64); u,inv=np.unique(cells,axis=0,return_inverse=True); cnt=np.bincount(inv)
    mean=np.column_stack([np.bincount(inv,weights=P[:,j])/cnt for j in range(3)])
    R=np.array(load('044')['prov']['R_rectified_from_source'])
    return (mean@R+C)*0.001
def grid(Pm, step=0.05):
    xy=G['xy_m']; x0=xy[0,0,0]-step/2; y0=xy[0,0,1]-step/2  # same lattice as production
    k=np.floor((Pm[:,:2]-[x0,y0])/step).astype(int)
    ok=(k[:,0]>=0)&(k[:,1]>=0)&(k[:,0]<xy.shape[0])&(k[:,1]<xy.shape[1])
    lin=k[ok,0]*xy.shape[1]+k[ok,1]; cnt=np.bincount(lin,minlength=xy.shape[0]*xy.shape[1]).reshape(xy.shape[:2])
    return cnt>=2
prod_lab=G['labels']; hull=prod_lab>0
cams={k:(np.array(v)[:3,3]@np.array(load('044')['prov']['R_rectified_from_source'])+C)*0.001 for k,v in TR.items()}
camxy=np.array([c[:2] for c in cams.values()])
xy=G['xy_m']; dmin=np.min(np.linalg.norm(xy[...,None,:]-camxy[None,None],axis=-1),axis=-1)
out={}
for variant in ['production','slant+rawleft','hybrid']:
    Pm=fuse(variant); obs=grid(Pm)
    rec=dict(fused_voxels=len(Pm),observed_cells_in_production_hull=int((obs&hull).sum()),observed_fraction_of_hull=float((obs&hull).sum()/hull.sum()),
             near_cells_within_2m_of_a_camera=int((hull&(dmin<2)).sum()),near_observed=float((obs&hull&(dmin<2)).sum()/(hull&(dmin<2)).sum()),
             observed_outside_hull=int((obs&~hull).sum()))
    out[variant]=rec; print(variant,json.dumps(rec)); np.save(OUT_DIR+f'grid_obs_{variant}.npy',obs)
print('production labels: observed',int((prod_lab==1).sum()),'hull',int(hull.sum()),'frac %.3f'%((prod_lab==1).sum()/hull.sum()),'near frac %.3f'%(((prod_lab==1)&(dmin<2)).sum()/(hull&(dmin<2)).sum()))
json.dump(out,open(OUT_DIR+'fuse_grid.json','w'),indent=1); np.save(OUT_DIR+'dmin.npy',dmin)
