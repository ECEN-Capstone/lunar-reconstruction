import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys; sys.path.insert(0,_HERE)
import trace as T
from variants import *
boxes={'044':(255,692,390,752),'047':(565,840,615,885),'048':(545,832,580,868),'048b':(688,622,722,650)}
for key,(x0,y0,x1,y1) in boxes.items():
    o=key[:3]; r=load(o); rawg=raw_good(r)
    box=np.zeros((1024,1024),bool); box[y0:y1,x0:x1]=True
    for nm in ['r08','slant_pass1']:
        dl,lr,sampled,ex=run_variant(r,nm,o); f,v08,v11,ml=downstream(r,dl,lr,sampled,rawg)
        cons=(lr<=1)&(lr<99)&(dl>=0)&box; n=box.sum()
        fails={k:round(float((cons&~f[k]).sum()/max(cons.sum(),1)),2) for k in f}
        # r11-specific losses among v08 in box
        med=cv2.medianBlur(dl,5); nb=cv2.boxFilter(v08.astype(np.float32),-1,(5,5),normalize=False)
        a=v08&box
        r11f=dict(mindisp32=float((a&(dl<32)).sum()/max(a.sum(),1)),median2px=float((a&(np.abs(dl-med)>2)).sum()/max(a.sum(),1)),neighbors8=float((a&(nb<8)).sum()/max(a.sum(),1)))
        print(key,nm,'LRcons %.2f'%(cons.sum()/n),'r08 %.2f'%((v08&box).sum()/n),'r11 %.2f'%((v11&box).sum()/n),'| r08-filter fail among LRcons',fails,'| r11 fail among r08',{k:round(v,2) for k,v in r11f.items()})
