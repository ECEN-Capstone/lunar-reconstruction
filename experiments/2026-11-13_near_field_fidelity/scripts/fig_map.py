import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, io, contextlib, json; sys.path.insert(0,_HERE)
with contextlib.redirect_stdout(io.StringIO()):
    from trace import load, C, G, TR, np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; from matplotlib.colors import ListedColormap
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
lab=G['labels']; xy=G['xy_m']; hyb=np.load(OUT_DIR+'grid_obs_hybrid.npy'); prod=lab==1
R=np.array(load('044')['prov']['R_rectified_from_source'])
cams={k[4:]:(np.array(v)[:3,3]@R+C)*0.001 for k,v in TR.items()}
ext=[xy[0,0,1]-.025,xy[0,-1,1]+.025,xy[0,0,0]-.025,xy[-1,0,0]+.025]
fig,axs=plt.subplots(1,2,figsize=(13,6.4),layout='constrained')
for ax,(title,obs) in zip(axs,[('Production fused grid (Nov 11)',prod),('Proposed pairs, same poses and fusion',hyb)]):
    m=np.zeros(lab.shape,int); m[lab>0]=1; m[obs]=2
    if obs is hyb: m[obs&~prod]=3
    ax.imshow(m,origin='lower',extent=ext,cmap=ListedColormap(['white','#edb04b','#267b4d','#2a78d6']),vmin=0,vmax=3,interpolation='nearest')
    for o,p in cams.items(): ax.plot(p[1],p[0],'k^',ms=7,mec='white')
    ax.text(cams['044'][1]-.35,cams['044'][0]-.15,'044, 045',fontsize=8.5); ax.text(cams['047'][1]-.6,cams['047'][0]+.05,'046–048 (5.5 h later)',fontsize=8.5)
    a=(obs&(lab>0)).sum()/(lab>0).sum()
    ax.set(xlabel='Y left (m)',ylabel='X forward (m)'); ax.set_title(f'{title}\nobserved {100*a:.0f}% of footprint',loc='left',fontsize=10.5)
    ax.invert_xaxis()
import matplotlib.patches as mp
fig.legend(handles=[mp.Patch(color='#267b4d',label='Observed (≥2 points in 5 cm cell)'),mp.Patch(color='#2a78d6',label='Newly observed with proposed matcher'),mp.Patch(color='#edb04b',label='Interpolated (Delaunay fill)'),plt.Line2D([],[],marker='^',color='k',ls='',label='Camera position')],loc='outside lower center',ncol=4,frameon=False)
fig.savefig(OUT_DIR+'fig3_fused_grid.png',dpi=120)
