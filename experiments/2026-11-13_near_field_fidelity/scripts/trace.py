import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, json; sys.path.insert(0,_HERE)
from common import *
U=ROOT_DIR+''
import re
txt=open(U+'chandrayaan-3-documentation/nav/calibration/ch3_nav_left_cahv.txt').read()
C=np.fromstring(re.search(r'^C\s*=([^\n]+)',txt,re.M)[1],sep=' ')
TR=json.load(open(U+'artifacts/runs/r12_registration/component_obs_044/camera_trajectory.json'))['T_component_from_camera']
G=np.load(U+'output/largest_terrain/component_obs_044/terrain_grids.npz')
ROCKS={'044':dict(box=(255,692,390,752),name='obs_044 near rock (lower left)'),
       '047':dict(box=(565,840,615,885),name='obs_047 rock (lower right)'),
       '048':dict(box=(545,832,580,868),name='obs_048 rock (lower centre)')}
def to_rover(o,xyz,R):
    T=np.array(TR[f'obs_{o}']); p=xyz@T[:3,:3].T+T[:3,3]
    return (p@R+C)*0.001
def pts(o,d,mask,r):
    f=r['prov']['K'][0][0]; Bm=r['prov']['baseline_calibration_units']
    yy,xx=np.nonzero(mask&np.isfinite(d)&(d>0)); Z=f*Bm/d[yy,xx]
    xyz=np.c_[(xx-511.5)*Z/f,(yy-511.5)*Z/f,Z]
    return to_rover(o,xyz,np.array(r['prov']['R_rectified_from_source'])),yy,xx
def grid_cells(P,step):
    k=np.floor(P[:,:2]/step).astype(int); u,inv=np.unique(k,axis=0,return_inverse=True)
    med=np.array([np.median(P[inv==i,2]) for i in range(len(u))]); cnt=np.bincount(inv)
    return u,med,cnt
out={}
for o,rk in ROCKS.items():
    r=load(o); x0,y0,x1,y1=rk['box']; box=np.zeros((1024,1024),bool); box[y0:y1,x0:x1]=True
    ret=(r['dl']>=0)&box; cons=ret&(r['lr']<=1)
    ds=np.load(OUT_DIR+f'd_{o}_slant_pass1.npy'); vs=np.load(OUT_DIR+f'v_{o}_slant_pass1.npy')
    v08,v11=r['v08'],r['v11']
    meshv=np.zeros_like(box); meshv[::3,::3]=v11[::3,::3]
    # right-visibility of the box using slant disparity (or prior)
    dsb=ds[box]; vis=None
    xr=(np.indices((1024,1024))[1]-np.nan_to_num(ds,nan=0))[box]
    n=box.sum()
    rec=dict(rock=rk['name'],box_xyxy=rk['box'],pixels=int(n),
        r08_sgbm_returned=float(ret.sum()/n),r08_lr_consistent=float(cons.sum()/n),r08_after_filters=float((v08&box).sum()/n),
        r11_after_support=float((v11&box).sum()/n),r11_pair_mesh_vertices=int((meshv&box).sum()),
        slant_lr_consistent=float((np.isfinite(ds)&box).sum()/n),slant_after_r08=float((vs[0]&box).sum()/n),slant_after_r11=float((vs[1]&box).sum()/n),
        slant_disparity_p5_50_95=np.nanpercentile(dsb,[5,50,95]).round(1).tolist() if np.isfinite(dsb).any() else None)
    # 3D: slant points in box, plus surrounding ground ring
    ring=np.zeros_like(box); ring[max(0,y0-40):y1+40,max(0,x0-60):x1+60]=True; ring&=~box
    P,yy,xx=pts(o,ds,box&vs[1],r); Pg,_,_=pts(o,ds,ring&vs[1],r)
    P0,_,_=pts(o,np.where(v11,r['dl'],np.nan),box,r)
    if len(P) and len(Pg):
        # local ground plane from ring (rover frame), relief = height above plane
        A=np.c_[Pg[:,:2],np.ones(len(Pg))]; cpl,*_=np.linalg.lstsq(A,Pg[:,2],rcond=None)
        h=P[:,2]-np.c_[P[:,:2],np.ones(len(P))]@cpl
        rec['slant_points_on_rock']=len(P); rec['r11_points_on_rock']=len(P0)
        rec['rock_range_m']=float(np.median(np.linalg.norm(P-(C*0.001),axis=1)))
        rec['rock_xy_rover_m']=np.median(P[:,:2],0).round(2).tolist()
        rec['relief_above_local_ground_m_p95_max']=[float(np.percentile(h,95)),float(h.max())]
        for step in [0.01,0.02,0.05]:
            u,med,cnt=grid_cells(np.c_[P[:,:2],h],step); ok=cnt>=2
            rec[f'relief_grid_{int(step*100)}cm_max_m']=float(med[ok].max()) if ok.any() else None
            rec[f'cells_{int(step*100)}cm']=int(ok.sum())
        # production fused grid: cells under rock footprint
        xy=G['xy_m']; lab=G['labels']; fh=G['filled_height_m']; oh=G['observed_height_m']
        lo=P[:,:2].min(0); hi=P[:,:2].max(0)
        sel=(xy[...,0]>=lo[0]-.025)&(xy[...,0]<=hi[0]+.025)&(xy[...,1]>=lo[1]-.025)&(xy[...,1]<=hi[1]+.025)
        rec['fused_grid_cells_under_rock']=int(sel.sum()); rec['fused_grid_observed_cells']=int((sel&(lab==1)).sum()); rec['fused_grid_interpolated_cells']=int((sel&(lab==2)).sum())
        if sel.any():
            hh=fh[sel]-(np.c_[xy[sel],np.ones(sel.sum())]@cpl)
            rec['fused_grid_relief_max_m']=float(np.nanmax(hh)); rec['fused_grid_relief_median_m']=float(np.nanmedian(hh))
        rec['_P']=P.tolist() if o=='044' else None; rec['_h']=h.tolist() if o=='044' else None; rec['_plane']=cpl.tolist()
    out[o]=rec
    print(json.dumps({k:v for k,v in rec.items() if not k.startswith('_')}))
json.dump(out,open(OUT_DIR+'trace.json','w'))
