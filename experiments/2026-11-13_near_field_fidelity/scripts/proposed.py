import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, json; sys.path.insert(0,_HERE)
from variants import *
res={}
for o in OBS:
    r=load(o); rawg=raw_good(r)
    for nm,var,mode in [('r08','r08','strict'),('slant','slant_pass1','strict'),('slant+rawleft','slant_pass1','left'),('r08+rawleft','r08','left')]:
        dl,lr,sampled,ex=run_variant(r,var,o); f,v08,v11,ml=downstream(r,dl,lr,sampled,rawg,mode)
        den=ml[NEAR]
        rec=dict(after_r08=float(v08[NEAR][den].mean()),after_r11=float(v11[NEAR][den].mean()),mid_after_r11=float(v11[MID][ml[MID]].mean()),
                 whole_after_r11=float(v11[ml].mean()),sift=sift_agree(o,dl,v11))
        res[f'{o}/{nm}']=rec
        np.save(OUT_DIR+f'v11_{o}_{nm}.npy',v11); np.save(OUT_DIR+f'dl_{o}_{nm}.npy',dl)
        s=rec['sift']; print(o,nm.ljust(14),'near r08 %.3f r11 %.3f | mid r11 %.3f | whole r11 %.3f | SIFT(held-out, r11 px) n=%d med %.2f w1 %.2f'%(rec['after_r08'],rec['after_r11'],rec['mid_after_r11'],rec['whole_after_r11'],s['n_eval'],s.get('med_err',np.nan),s.get('within1',np.nan)),flush=True)
json.dump(res,open(OUT_DIR+'proposed.json','w'),indent=1)
