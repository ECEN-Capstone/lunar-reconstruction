import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__))
OUT_DIR=_os.environ.get('NF_OUT',_os.path.join(_HERE,'..','results'))+'/'
import sys, io, contextlib; sys.path.insert(0,_HERE)
with contextlib.redirect_stdout(io.StringIO()):
    from variants import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
o='047'; r=load(o); L,R=r['L'],r['R']; c,_,_=ground_prior(o,r,'pass1'); a,b,c0=c
yy,xx=np.indices(L.shape,dtype=np.float32); dg=np.clip(a*xx+b*yy+c0,0,None).astype(np.float32)
Rw=cv2.remap(R,xx-dg,yy,cv2.INTER_LINEAR)
x0,x1,y0,y1=470,770,740,960
xc,yc=(x0+x1)//2,(y0+y1)//2; off=int(round(dg[yc,xc]))   # shift raw-right crop so centre lines up
fig=plt.figure(figsize=(15,10.2),layout='constrained')
gs=fig.add_gridspec(2,3,height_ratios=[1.05,1])
cols=['#ffd400','#ff7a1a','#2fd0ff']
def grid(ax,mode):
    xs=np.arange(x0+30,x1,60); ys=np.arange(y0+20,y1,50)
    for i,x in enumerate(xs):
        yv=np.arange(y0,y1)
        if mode=='raw': xv=x-dg[yv,x]+off
        else: xv=np.full_like(yv,x,dtype=float)
        ax.plot(xv-x0,yv-y0,color=cols[0],lw=1.3)
    for y in ys: ax.axhline(y-y0,color=cols[0],lw=.8,alpha=.7)
titles=['Left image (the reference)','Right image, as captured\n(shifted so the centre lines up)','Right image after pre-skew\n(shifted row by row by the fitted ground plane)']
crops=[L[y0:y1,x0:x1],R[y0:y1,x0-off:x1-off],Rw[y0:y1,x0:x1]]
for j,(t,im,mode) in enumerate(zip(titles,crops,['left','raw','warp'])):
    ax=fig.add_subplot(gs[0,j]); ax.imshow(im,cmap='gray',vmin=0,vmax=255); grid(ax,mode); ax.set_xlim(-.5,x1-x0-.5); ax.set_ylim(y1-y0-.5,-.5); ax.set_title(t,loc='left',fontsize=10.5); ax.set_xticks([]); ax.set_yticks([])
    if j==1: ax.text(5,y1-y0-8,'Same ground lines lean: near rows need more shift',color='white',fontsize=9,bbox=dict(fc='black',alpha=.6,ec='none'))
    if j==2: ax.text(5,y1-y0-8,'Ground lines upright again: patches line up',color='white',fontsize=9,bbox=dict(fc='black',alpha=.6,ec='none'))
# zoom: 25x25 around a textured point, with a 5x5 block and a 15-row block
h=12
D=np.load(OUT_DIR+'d_047_slant_pass1.npy'); Lf=L.astype(np.float32)
sd=np.sqrt(np.maximum(cv2.boxFilter(Lf*Lf,-1,(15,15))-cv2.boxFilter(Lf,-1,(15,15))**2,0))
cand=np.zeros_like(sd); cand[860:935,520:740]=1; cand*=np.isfinite(D)*(L>30)
py,px=np.unravel_index(np.argmax(sd*cand),sd.shape)
dc=dg[py,px]; offz=int(round(dc))
zl=L[py-h:py+h+1,px-h:px+h+1]; zr=R[py-h:py+h+1,px-h-offz:px+h+1-offz]; zw=Rw[py-h:py+h+1,px-h:px+h+1]
zt=['Left: 25×25 px zoom, 5×5 matching block','Right as captured: the block that truly matches\nis slanted (≈%.1f px shift per row)'%b,'Right after pre-skew: matching block is square']
for j,(t,z) in enumerate(zip(zt,[zl,zr,zw])):
    ax=fig.add_subplot(gs[1,j]); ax.imshow(z,cmap='gray',vmin=0,vmax=255,interpolation='nearest'); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(t,loc='left',fontsize=10.5)
    # 5x5 block outline (and a taller 11-row strip to make the lean visible)
    for (hh,col,lw) in [(2,cols[1],2.2),(8,cols[2],1.4)]:
        ys_=np.array([h-hh-.5,h+hh+.5]); 
        if j==1:
            sh=lambda y: -(b*(y-h))  # true match position relative to centre-aligned crop
            xs_=[h-2.5,h+2.5]
            pts=[(xs_[0]+sh(ys_[0]),ys_[0]),(xs_[1]+sh(ys_[0]),ys_[0]),(xs_[1]+sh(ys_[1]),ys_[1]),(xs_[0]+sh(ys_[1]),ys_[1]),(xs_[0]+sh(ys_[0]),ys_[0])]
        else:
            pts=[(h-2.5,ys_[0]),(h+2.5,ys_[0]),(h+2.5,ys_[1]),(h-2.5,ys_[1]),(h-2.5,ys_[0])]
        ax.plot(*zip(*pts),color=col,lw=lw)
fig.text(0.01,-0.04,f"obs_047, near field (~1.5–2.5 m). Fitted ground plane: shift = {a:.3f}·column + {b:.3f}·row + {c0:.0f} px. Orange = 5×5 matching block; blue = same block stretched to 17 rows to make the lean easy to see.\n"
         f"Across a 5-row block the bottom needs ~{4*b:.1f} px more shift than the top, enough to scramble fine regolith texture. At the correct match, 5×5 block similarity (NCC) rises from 0.68 to 0.80 median after pre-skew.",fontsize=9,color='#52514e',wrap=True)
fig.suptitle('Pre-skewing: undo the ground slant before matching',x=0.01,ha='left',fontsize=13)
fig.savefig(_os.path.join(_HERE,'..','figures','fig5_preskew_explained.png'),dpi=120,bbox_inches='tight')
print(a,b,c0,off)
