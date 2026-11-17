import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, json, io, contextlib; sys.path.insert(0,_HERE)
with contextlib.redirect_stdout(io.StringIO()):
    from trace import load, C, G, TR, np
from fuse_grid import xyz_from
R=np.array(load('044')['prov']['R_rectified_from_source'])
xy=G['xy_m']; x0=xy[0,0,0]-.025; y0=xy[0,0,1]-.025; dmin=np.load(OUT_DIR+'dmin.npy')
def pair_grid(o,variant):
    r=load(o); Bm=r['prov']['baseline_calibration_units']
    if variant=='production': dl,v=r['dl'],r['v11']
    else: dl=np.load(OUT_DIR+f'dl_{o}_{variant}.npy'); v=np.load(OUT_DIR+f'v11_{o}_{variant}.npy')
    ar=xyz_from(dl,v,Bm)[::2,::2]; ok=np.isfinite(ar).all(2); p=ar[ok]; T=np.array(TR['obs_'+o]); p=p@T[:3,:3].T+T[:3,3]; P=(p@R+C)*0.001
    k=np.floor((P[:,:2]-[x0,y0])/.05).astype(int); okk=(k>=0).all(1)&(k[:,0]<xy.shape[0])&(k[:,1]<xy.shape[1])
    lin=k[okk,0]*xy.shape[1]+k[okk,1]; z=P[okk,2]
    order=np.argsort(lin); lin=lin[order]; z=z[order]; u,st,cnt=np.unique(lin,return_index=True,return_counts=True)
    med=np.array([np.median(z[s:s+c]) for s,c in zip(st,cnt)])
    g=np.full(xy.shape[0]*xy.shape[1],np.nan); g[u[cnt>=2]]=med[cnt>=2]; return g.reshape(xy.shape[:2])
for variant in ['production','slant+rawleft','hybrid']:
    grids={o:pair_grid(o,variant) for o in ['044','045','046','047','048']}
    diffs=[];near=[]
    keys=list(grids)
    for i in range(5):
        for j in range(i+1,5):
            a,b=grids[keys[i]],grids[keys[j]]; m=np.isfinite(a)&np.isfinite(b)
            if m.sum(): diffs+=list(np.abs(a-b)[m]); near+=list(dmin[m]<2)
    d=np.array(diffs); n=np.array(near)
    print(variant,'cells seen by 2 pairs (pairwise):',len(d),'median |dz| mm %.1f p90 %.1f'%(1000*np.median(d),1000*np.percentile(d,90)),
          '| near(<2m) n=%d median %.1f p90 %.1f'%(n.sum(),1000*np.median(d[n]) if n.sum() else np.nan,1000*np.percentile(d[n],90) if n.sum() else np.nan))
print('--- by distance band')
for variant in ['production','slant+rawleft','hybrid']:
    grids={o:pair_grid(o,variant) for o in ['044','045','046','047','048']}; keys=list(grids); D=[];N=[]
    for i in range(5):
        for j in range(i+1,5):
            a,b=grids[keys[i]],grids[keys[j]]; m=np.isfinite(a)&np.isfinite(b); D+=list(np.abs(a-b)[m]); N+=list(dmin[m])
    D=np.array(D);N=np.array(N)
    print(variant,' | '.join('%g-%gm n=%d med %.0f p90 %.0f'%(lo,hi,((N>=lo)&(N<hi)).sum(),1000*np.median(D[(N>=lo)&(N<hi)]) if ((N>=lo)&(N<hi)).sum() else -1,1000*np.percentile(D[(N>=lo)&(N<hi)],90) if ((N>=lo)&(N<hi)).sum() else -1) for lo,hi in [(0,2),(2,4),(4,6),(6,9),(9,20)]))
