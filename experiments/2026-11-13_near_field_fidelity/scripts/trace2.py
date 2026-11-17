import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, json; sys.path.insert(0,_HERE)
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from trace import load, pts, C, G, np, cv2, TR
ROCKS={'044':('044',(255,692,390,752),'obs_044 near rock (lower left)'),'047':('047',(565,840,615,885),'obs_047 rock (lower right)'),'048b':('048',(688,622,722,650),'obs_048 rock (mid field)')}
def relief(o,d,mask_box,mask_ring,r):
    P,_,_=pts(o,d,mask_box,r); Pg,_,_=pts(o,d,mask_ring,r)
    if len(P)<3 or len(Pg)<20: return None,None,None
    A=np.c_[Pg[:,:2],np.ones(len(Pg))]; w=np.ones(len(Pg),bool)
    for _ in range(5):
        cpl,*_=np.linalg.lstsq(A[w],Pg[w,2],rcond=None); res=Pg[:,2]-A@cpl; w=np.abs(res)<3*max(1.4826*np.median(np.abs(res)),1e-3)
    return P,P[:,2]-np.c_[P[:,:2],np.ones(len(P))]@cpl,cpl
def gridmax(P,h,step,minpts=2):
    k=np.floor(P[:,:2]/step).astype(int); u,inv=np.unique(k,axis=0,return_inverse=True); cnt=np.bincount(inv)
    med=np.array([np.median(h[inv==i]) for i in range(len(u))]); ok=cnt>=minpts
    return (float(med[ok].max()) if ok.any() else None), int(ok.sum())
out={}
for key,(o,(x0,y0,x1,y1),name) in ROCKS.items():
    r=load(o); box=np.zeros((1024,1024),bool); box[y0:y1,x0:x1]=True
    ring=np.zeros_like(box); ring[max(0,y0-40):y1+40,max(0,x0-60):x1+60]=True; ring&=~box
    rec=dict(rock=name,box=[x0,y0,x1,y1])
    # matched (LR-consistent, before filters) relief = what stereo actually measured
    ds=np.load(OUT_DIR+f'd_{o}_slant_pass1.npy')
    P,h,cpl=relief(o,ds,box,ring,r)
    rec['range_m']=float(np.median(np.linalg.norm(P-C*0.001,axis=1)))
    rec['footprint_m']=np.ptp(P[:,:2],0).round(3).tolist()
    rec['measured_relief_mm_p95']=float(1000*np.percentile(h,95)); rec['measured_relief_mm_max']=float(1000*h.max())
    rec['pixel_size_mm_at_range']=float(1000*rec['range_m']/1400.98)
    for nm in ['r08','slant','slant+rawleft']:
        v11=np.load(OUT_DIR+f'v11_{o}_{nm}.npy'); dl=np.load(OUT_DIR+f'dl_{o}_{nm}.npy')
        d=np.where(v11,dl,np.nan); n=(v11&box).sum()
        Pk,hk,_=relief(o,d,box,ring,r)
        mesh=np.zeros_like(box); mesh[::3,::3]=v11[::3,::3]
        e=dict(r11_pixels_on_rock=int(n),pair_mesh_vertices_on_rock=int((mesh&box).sum()))
        if Pk is not None and len(Pk)>=3:
            # use the matched-relief plane (cpl) for a common reference
            hk=Pk[:,2]-np.c_[Pk[:,:2],np.ones(len(Pk))]@cpl
            e['relief_mm_max_points']=float(1000*hk.max())
            for st in [0.01,0.02,0.05]:
                m,c=gridmax(Pk,hk,st); e[f'relief_mm_{int(st*100)}cm_grid']=None if m is None else float(1000*m); e[f'cells_{int(st*100)}cm']=c
        rec[nm]=e
    # production fused grid
    xy=G['xy_m']; lab=G['labels']; fh=G['filled_height_m']
    lo=P[:,:2].min(0); hi=P[:,:2].max(0)
    sel=(xy[...,0]>=lo[0]-.025)&(xy[...,0]<=hi[0]+.025)&(xy[...,1]>=lo[1]-.025)&(xy[...,1]<=hi[1]+.025)
    hh=fh[sel]-(np.c_[xy[sel],np.ones(sel.sum())]@cpl)
    rec['fused_5cm_grid']=dict(cells=int(sel.sum()),observed=int((sel&(lab==1)).sum()),interpolated=int((sel&(lab==2)).sum()),relief_mm_max=float(1000*np.nanmax(hh)) if sel.any() else None, relief_mm_median=float(1000*np.nanmedian(hh)) if sel.any() else None)
    out[key]=rec; print(json.dumps(rec))
json.dump(out,open(OUT_DIR+'trace2.json','w'),indent=1)
