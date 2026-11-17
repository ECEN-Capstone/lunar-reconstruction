import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import json, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.edgecolor':'#bdbcb6','axes.labelcolor':'#52514e','xtick.color':'#52514e','ytick.color':'#52514e'})
L=[l.split(' ',2) for l in open(OUT_DIR+'variants2.log') if l[:3].isdigit()]
V={}
for o,n,j in L: V[(o,n)]=json.loads(j)
P=json.load(open(OUT_DIR+'proposed.json'))
obs=['044','045','046','047','048']; stages=['SGBM returns\na disparity','Left-right\nconsistent','After per-pixel\nfilters (r08)','After support\nfilter (r11)']
def series(n,raw='strict'):
    a=[]
    for o in obs:
        v=V[(o,n)]; r08=v['after_r08']; r11=v['after_r11']
        if raw=='left': r08=P[f'{o}/slant+rawleft']['after_r08']; r11=P[f'{o}/slant+rawleft']['after_r11']
        a.append([v['returned'],v['lr_consistent'],r08,r11])
    return 100*np.array(a)
S=[('Production (r08 → r11)',series('r08'),'#8c8b86','o'),('Half resolution',series('half'),'#eda100','s'),
   ('Ground-slanted windows',series('slant_pass1'),'#2a78d6','^'),('Slanted + left-only shadow mask',series('slant_pass1','left'),'#6250d6','D')]
fig,ax=plt.subplots(figsize=(9,5.2),layout='constrained'); x=np.arange(4)
ax.axhspan(67,72,color='#e9e8e4',zorder=0); ax.text(3.45,69.5,'Right camera can see\nonly 67–72%',ha='right',va='center',fontsize=9,color='#52514e')
off=np.linspace(-0.15,0.15,len(S))
for (lab,a,c,m),dx in zip(S,off):
    mean=a.mean(0); ax.vlines(x+dx,a.min(0),a.max(0),color=c,lw=2,alpha=.55)
    ax.plot(x+dx,mean,color=c,lw=2,marker=m,ms=8,mec='white',mew=1.5,label=lab)
    lo,hi=a[:,3].min(),a[:,3].max(); fmt=(lambda v:f'{v:.1f}' if v<1 else f'{v:.0f}')
    yoff={'Half resolution':12,'Production (r08 → r11)':-12}.get(lab,0)
    ax.annotate(f'{fmt(lo)}–{fmt(hi)}%',(x[3]+dx,mean[3]),xytext=(12,yoff),textcoords='offset points',va='center',fontsize=8.5,color='#0b0b0b')
ax.set_xticks(x,stages); ax.set_ylabel('Near-field pixels with depth (%)'); ax.set_ylim(0,80); ax.set_xlim(-.4,3.75)
ax.grid(axis='y',color='#ebeae6',lw=.8); ax.set_axisbelow(True); [ax.spines[s].set_visible(False) for s in ['top','right']]
ax.legend(frameon=False,loc='upper left',fontsize=9)
ax.set_title('Near field (bottom third, ~0.8–2 m), obs_044–048: line = mean, bar = range across the 5 pairs',loc='left',fontsize=10.5,color='#0b0b0b')
fig.savefig(OUT_DIR+'fig2_near_field_funnel.png',dpi=160)
