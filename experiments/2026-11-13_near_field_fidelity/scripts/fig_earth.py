import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import json, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, pickle
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.edgecolor':'#bdbcb6','axes.labelcolor':'#52514e','xtick.color':'#52514e','ytick.color':'#52514e'})
V={}
for l in open(OUT_DIR+'variants2.log'):
    if l[:3].isdigit(): o,n,j=l.split(' ',2); V[(o,n)]=json.loads(j)
shear={'044':0.858,'045':None,'046':0.733,'047':0.790,'048':0.893}
# use pass1-prior slope b (rows) for all five NavCam pairs
import sys,io,contextlib; sys.path.insert(0,_HERE)
with contextlib.redirect_stdout(io.StringIO()):
    from variants import ground_prior, load
for o in ['044','045','046','047','048']: shear[o]=ground_prior(o,load(o),'pass1')[0][1]
print({o:round(v,2) for o,v in shear.items()})
T=json.load(open(OUT_DIR+'polar_traverse.json')); P=json.load(open(OUT_DIR+'polar_stereo.json'))
pts={'prod':[], 'slant':[]}
def add(ds,x,yp,ys): pts['prod'].append((ds,x,yp)); pts['slant'].append((ds,x,ys))
for o in shear: add('NavCam obs_044–048 (camera ~0.33 m)',shear[o],V[(o,'r08')]['lr_consistent'],V[(o,'slant_pass1')]['lr_consistent'])
for k,v in T.items(): add('POLAR Traverse, camera 1.3 m' if v['height_m']>1 else 'POLAR Traverse, camera 0.65 m',v['near_shear_px_per_row'],v['production']['lr_consistent'],v['slanted']['lr_consistent'])
for k,v in P.items():
    if 'Sun_270_0128' in k or 'Sun_350_0512' in k: continue  # under-exposed (near-field median < 20 DN)
    add('POLAR Stereo, camera 1.35 m (lidar truth)',v['gt_near_shear_px_per_row'],v['production']['near']['lr_consistent'],v['slanted']['near']['lr_consistent'])
mk={'NavCam obs_044–048 (camera ~0.33 m)':'o','POLAR Traverse, camera 1.3 m':'s','POLAR Traverse, camera 0.65 m':'D','POLAR Stereo, camera 1.35 m (lidar truth)':'^'}
fig,ax=plt.subplots(figsize=(9,5.4),layout='constrained')
for (a,b) in zip(pts['prod'],pts['slant']):
    ax.annotate('',xy=(b[1],100*b[2]),xytext=(a[1],100*a[2]),arrowprops=dict(arrowstyle='-',color='#d6d5cf',lw=1))
for key,c,lab in [('prod','#8c8b86','Production SGBM (r08 settings)'),('slant','#2a78d6','Ground-slanted windows')]:
    for ds,m in mk.items():
        xs=[p[1] for p in pts[key] if p[0]==ds]; ys=[100*p[2] for p in pts[key] if p[0]==ds]
        ax.scatter(xs,ys,marker=m,s=60,c=c,edgecolors='white',linewidths=1.2,zorder=3)
from matplotlib.lines import Line2D
h=[Line2D([],[],marker='o',ls='',color='#8c8b86',ms=8,label='Production SGBM (r08 settings)'),Line2D([],[],marker='o',ls='',color='#2a78d6',ms=8,label='Ground-slanted windows')]
h+=[Line2D([],[],marker=m,ls='',color='#52514e',mfc='white',ms=8,label=ds) for ds,m in mk.items()]
ax.legend(handles=h,frameon=False,loc='upper right',fontsize=8.8)
ax.set_xlabel('Near-field disparity change per image row (px/row)  ← steeper view | grazing view →')
ax.set_ylabel('Near-field pixels with left-right-consistent depth (%)')
ax.set_ylim(0,100); ax.set_xlim(0.1,1.1); ax.grid(color='#ebeae6',lw=.8); ax.set_axisbelow(True); [ax.spines[s].set_visible(False) for s in ['top','right']]
ax.set_title('Same matcher settings on lunar-analog Earth data vs NavCam: depth coverage falls as the camera gets lower',loc='left',fontsize=10.5)
fig.savefig(OUT_DIR+'fig4_earth_vs_navcam.png',dpi=160)
