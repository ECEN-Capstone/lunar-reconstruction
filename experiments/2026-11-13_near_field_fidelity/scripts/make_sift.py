"""Step 0: SIFT matches on the r08 rectified pairs (used for ground prior hold-out split and accuracy checks)."""
import os, sys, pickle
_HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,_HERE)
from common import *
OUT_DIR=os.environ.get('NF_OUT',os.path.join(_HERE,'..','results'))+'/'
res={}
for o in OBS:
    r=load(o); pa,pb=sift_matches(r['L'],r['R']); res[o]=dict(pa=pa,pb=pb); print(o,len(pa))
pickle.dump(res,open(OUT_DIR+'sift.pkl','wb'))
