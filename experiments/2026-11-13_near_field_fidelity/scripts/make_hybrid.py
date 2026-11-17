"""Hybrid: experimental matcher (slant + left-only mask) where the ground prior says <= ~4 m (prior >= 85 px), production elsewhere."""
import os, sys, io, contextlib; _HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,_HERE)
with contextlib.redirect_stdout(io.StringIO()):
    from variants import *
OUT_DIR=os.environ.get('NF_OUT',os.path.join(_HERE,'..','results'))+'/'
for o in OBS:
    r=load(o); c,_,_=ground_prior(o,r,'pass1'); yy,xx=np.indices((1024,1024)); near=(c[0]*xx+c[1]*yy+c[2])>=85
    a=np.load(OUT_DIR+f'dl_{o}_slant+rawleft.npy'); va=np.load(OUT_DIR+f'v11_{o}_slant+rawleft.npy')
    b=np.load(OUT_DIR+f'dl_{o}_r08.npy'); vb=np.load(OUT_DIR+f'v11_{o}_r08.npy')
    np.save(OUT_DIR+f'dl_{o}_hybrid.npy',np.where(near,a,b).astype(np.float32)); np.save(OUT_DIR+f'v11_{o}_hybrid.npy',np.where(near,va,vb))
