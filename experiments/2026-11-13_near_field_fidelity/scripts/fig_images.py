import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR=_os.environ.get('LR_ROOT',_os.path.abspath(_os.path.join(_HERE,'..','..','..')))+'/'
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
POLAR_DIR=_os.environ.get('POLAR_DIR',_os.path.expanduser('~/Downloads/polar_eval'))+'/'
import sys, io, contextlib; sys.path.insert(0,_HERE)
with contextlib.redirect_stdout(io.StringIO()):
    from variants import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
f=1400.9789644404393
rows=[('044',[(255,692,390,752,'rock ~6.7 cm tall, 1.4 m')]),('047',[(565,840,615,885,'rock ~2.1 cm, 1.9 m')])]
fig,axs=plt.subplots(2,3,figsize=(14,9.6),layout='constrained')
for i,(o,rocks) in enumerate(rows):
    r=load(o); Bm=r['prov']['baseline_calibration_units']; c,_,_=ground_prior(o,r,'pass1')
    H=np.array(r['prov']['homographies'][1]); mr=cv2.warpPerspective(np.full((1024,1024),255,np.uint8),H,(1024,1024))
    xedge=np.argmax(mr[800]>0)
    for j,(title,v,dl) in enumerate([('Rectified left image',None,None),('Production depth (r08 → r11)',r['v11'],r['dl']),('Proposed: slanted windows + left-only shadow mask',np.load(OUT_DIR+f'v11_{o}_hybrid.npy'),np.load(OUT_DIR+f'dl_{o}_hybrid.npy'))]):
        ax=axs[i,j]; ax.imshow(r['L'],cmap='gray',vmin=0,vmax=255)
        if v is not None:
            Z=np.where(v,f*Bm/np.where(v,dl,1)/1000,np.nan); im=ax.imshow(Z,cmap='viridis',vmin=0.8,vmax=8,alpha=.9)
            nf=v[NEAR][r['m_inside_rectification'][NEAR]].mean()
            ax.text(10,1010,f'near field with depth: {100*nf:.1f}%',color='white',fontsize=10,va='bottom',bbox=dict(fc='black',alpha=.6,ec='none'))
        yy=np.arange(560,1024); xl=(xedge+c[1]*yy+c[2])/(1-c[0])
        ax.plot(xl,yy,'--',color='#eb6834',lw=1.6)
        if j==0: ax.text(xl[-1]+8,1000,'← right camera\ncannot see',color='#ffb48f',fontsize=9,va='bottom',bbox=dict(fc='black',alpha=.6,ec='none'))
        for (x0,y0,x1,y1,lab) in rocks:
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='white',lw=1.4))
            if j==0: ax.text(x0,y0-8,lab,color='white',fontsize=9,bbox=dict(fc='black',alpha=.5,ec='none'))
        ax.axhline(683,color='white',lw=.6,ls=':'); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f'obs_{o}: {title}' if j==0 else title,fontsize=10.5,loc='left')
cb=fig.colorbar(im,ax=axs[:,2],shrink=.6,label='Depth (m)')
fig.suptitle('Near field below the dotted line. Dashed orange: left of it the right camera has no view, so no stereo method can measure it.',fontsize=10.5,x=0.01,ha='left',color='#52514e')
fig.savefig(OUT_DIR+'fig1_near_field_depth.png',dpi=110)
