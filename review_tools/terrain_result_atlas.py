"""Scientific renders of saved OBJ results; never reconstructs or edits terrain."""
from pathlib import Path
import json, hashlib, csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.spatial import cKDTree
import cv2
from reconstruction.close_terrain import read_obj
from reconstruction.video_bridge import local_camera, transform, CENTRE

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/detailed_progress_2026-11-10'
ASSETS=OUT/'figures'
COLORS=np.array([[1,1,1,1],[.12,.46,.66,1],[.15,.68,.57,1],[.94,.47,.08,1],[.64,.66,.69,1]])

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def render(obj,dst,T=None,labels=None,xy=None,units='m',top=False,background='white'):
    v,f=read_obj(obj)
    if T is not None:v=transform(v*.001,T)
    tri=v[f]
    if labels is not None:
        _,idx=cKDTree(xy.reshape(-1,2)).query(v[:,:2])
        source=labels.ravel()[idx]
        # Face carries its most inferred vertex category, rather than implying
        # an entire face is observed when only one vertex is observed.
        color=COLORS[source[f].max(1)]
    else:
        z=tri[:,:,2].mean(1)
        color=plt.get_cmap('viridis')((z-z.min())/max(np.ptp(z),1e-8))
    if background!='white':color[:,:3]=.25+.75*color[:,:3]
    fig=plt.figure(figsize=(8,4.5),facecolor=background)
    ax=fig.add_axes([.03,.04,.94,.94],projection='3d')
    ax.set_facecolor(background)
    ax.add_collection3d(Poly3DCollection(tri,facecolors=color,edgecolors='none',rasterized=True))
    lo=v.min(0);hi=v.max(0);span=np.maximum(hi-lo,1e-4)
    for fn,a,b in zip((ax.set_xlim,ax.set_ylim,ax.set_zlim),lo,hi):fn(a-.025*max(b-a,.05),b+.025*max(b-a,.05))
    ax.set_box_aspect(span.copy())
    ax.view_init(elev=90 if top else 31,azim=-90 if top else -115)
    ax.set_xlabel('X ('+units+')',labelpad=2);ax.set_ylabel('Y ('+units+')',labelpad=2);ax.set_zlabel('Z ('+units+')',labelpad=2)
    ax.tick_params(labelsize=8,pad=0)
    ax.xaxis.set_major_locator(plt.MaxNLocator(3));ax.yaxis.set_major_locator(plt.MaxNLocator(3));ax.zaxis.set_major_locator(plt.MaxNLocator(3))
    ax.set_proj_type('ortho')
    # True aspect ratio; no smoothing, face decimation, outlier removal or clipping.
    ax.set_axis_off()
    fig.savefig(dst,dpi=150,facecolor=background);plt.close(fig)
    # Remove empty canvas margins only; retain every rendered geometry pixel.
    from PIL import Image
    im=Image.open(dst).convert('RGB');a=np.asarray(im)
    from matplotlib.colors import to_rgb
    bg=np.round(np.array(to_rgb(background))*255).astype(int)
    yy,xx=np.where(np.max(np.abs(a.astype(int)-bg),axis=2)>10)
    if len(xx):
        im.crop((max(0,int(xx.min())-24),max(0,int(yy.min())-24),min(im.width,int(xx.max())+25),min(im.height,int(yy.max())+25))).save(dst)
    return {'vertices':len(v),'triangles':len(f),'bbox_min':lo.tolist(),'bbox_max':hi.tolist(),'extent':span.tolist(),'obj':str(obj.relative_to(ROOT)),'obj_sha256':sha(obj),'render':str(dst.relative_to(ROOT)),'units':units,'render_policy':'all exported faces; orthographic; true XYZ aspect; independent full extent; no smoothing or cropping'}

def frame_strip(movie,dst):
    cap=cv2.VideoCapture(str(movie));count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));idx=[0,count//2,count-1]
    images=[]
    for i in idx:
        cap.set(cv2.CAP_PROP_POS_FRAMES,i);ok,im=cap.read()
        if not ok:raise ValueError((movie,i))
        images.append(cv2.resize(im,(220,220),interpolation=cv2.INTER_AREA))
    cap.release();cv2.imwrite(str(dst),np.concatenate(images,axis=1))
    return {'frame_indices':idx,'frame_count':count,'movie_sha256':sha(movie),'strip':str(dst.relative_to(ROOT))}

def plan_grid(s,dst):
    labels=s['labels'];x=s['x'] if 'x' in s else s['xy_m'][:,0,0];y=s['y'] if 'y' in s else s['xy_m'][0,:,1]
    fig,ax=plt.subplots(figsize=(6,4.5));ax.imshow(COLORS[labels].transpose(1,0,2),origin='lower',extent=[x[0]-.025,x[-1]+.025,y[0]-.025,y[-1]+.025],interpolation='nearest')
    ax.set(xlabel='X (m)',ylabel='Y (m)',aspect='equal');fig.tight_layout();fig.savefig(dst,dpi=150);plt.close(fig)

def main():
    ASSETS.mkdir(parents=True,exist_ok=True);plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
    result={'snapshot':'2026-11-10','local':[],'components':[],'completion':[],'generated':[],'video':[]}
    for folder in sorted((ROOT/'artifacts/runs/r11_filtered_batch').glob('obs_*')):
        obj=folder/'local_mesh_calibration_units.obj'
        if not obj.exists():continue
        name=folder.name;meta=read(folder/'provenance.json');T=np.eye(4);T[:3,:3]=np.asarray(meta['R_rectified_from_source']).T;T[:3,3]=CENTRE
        r=render(obj,ASSETS/(name+'_mesh.png'),T=T);r.update(name=name,metrics=read(folder/'metrics.json'),input=str((folder/'rectified_left.png').relative_to(ROOT)),metrics_source=str((folder/'metrics.json').relative_to(ROOT)))
        result['local'].append(r)
        if len(result['local'])%10==0:print('local renders',len(result['local']),flush=True)
    for folder in sorted((ROOT/'artifacts/runs/r12_registration').glob('component_*')):
        meta=read(folder/'metrics.json')
        if len(meta.get('frames',[]))<2:continue
        name=folder.name;obs=name.replace('component_','');pr=read(ROOT/'artifacts/runs/r11_filtered_batch'/obs/'provenance.json');T=np.eye(4);T[:3,:3]=np.asarray(pr['R_rectified_from_source']).T;T[:3,3]=CENTRE
        r=render(folder/'mesh_observed_union_calibration_units.obj',ASSETS/(name+'.png'),T=T);r.update(name=name,metrics=meta,metrics_source=str((folder/'metrics.json').relative_to(ROOT)));result['components'].append(r)
    for name in ['obs_003','obs_029','obs_034']:
        folder=ROOT/'artifacts/runs/r15_terrain_completion'/name
        rows={}
        for mode in ['balanced','extended','simulation']:
            rows[mode]=render(folder/f'terrain_{mode}_m.obj',ASSETS/f'{name}_{mode}.png')
        result['completion'].append({'name':name,'metrics':read(folder/'completion_metrics.json'),'renders':rows,'coverage':str((folder/'coverage_comparison.png').relative_to(ROOT)),'metrics_source':str((folder/'completion_metrics.json').relative_to(ROOT))})
    profiles=['more_relaxed','uber_relaxed','uber_relaxed_no_checks','uber_relaxed_wide_window','uber_relaxed_row_adjusted','row_adjusted_tighter','row_adjusted_strict_matching']
    for trial in ['stereo_trial_1','stereo_trial_2']:
        for profile in profiles:
            folder=ROOT/'output/uber_relaxed'/trial/profile
            # Camera coordinates: X right, Z forward, -Y up. This is a display
            # rotation only; no metric interpretation of generated geometry.
            v,f=read_obj(folder/'uber_relaxed.obj')
            R=np.array([[1,0,0],[0,0,1],[0,-1,0]])
            T=np.eye(4);T[:3,:3]=R*1000
            r=render(folder/'uber_relaxed.obj',ASSETS/f'{trial}_{profile}.png',T=T,units='baseline=1')
            r.update(trial=trial,name=profile,metrics=read(folder/'metrics.json'),metrics_source=str((folder/'metrics.json').relative_to(ROOT)));result['generated'].append(r)
        print('generated renders',trial,flush=True)
    folders=[p for p in sorted((ROOT/'output/chronological_video').iterdir()) if (p/'candidate_stereo_plus_video_m.obj').exists() or (p/'terrain_top_m.obj').exists()]
    for folder in folders:
        integrated=(folder/'integrated_grid.npz').exists();s=np.load(folder/('integrated_grid.npz' if integrated else 'surfaces.npz'))
        xy=s['xy_m'] if integrated else np.stack(np.meshgrid(s['x'],s['y'],indexing='ij'),-1)
        obj=folder/('terrain_top_m.obj' if integrated else 'candidate_stereo_plus_video_m.obj')
        r=render(obj,ASSETS/(folder.name+'_model.png'),labels=s['labels'],xy=xy)
        plan_grid(s,ASSETS/(folder.name+'_provenance.png'))
        r.update(name=folder.name,metrics=read(folder/'metrics.json'),metrics_source=str((folder/'metrics.json').relative_to(ROOT)),plan=str((ASSETS/(folder.name+'_provenance.png')).relative_to(ROOT)),integrated=integrated)
        if (folder/'transition.mp4').exists():r['video']=frame_strip(folder/'transition.mp4',ASSETS/(folder.name+'_frames.png'))
        result['video'].append(r);print('video render',folder.name,flush=True)
    result['local_totals']={key:sum(r['metrics'][key] for r in result['local']) for key in ['valid_points','mesh_faces']}
    result['render_count']=len(list(ASSETS.glob('*.png')))
    (OUT/'atlas_manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (OUT/'local_observation_results.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['observation','valid_points','whole_image_coverage','mesh_triangles','extent_x_m','extent_y_m','extent_z_m'])
        for r in result['local']:w.writerow([r['name'],r['metrics']['valid_points'],r['metrics']['valid_fraction'],r['triangles'],*r['extent']])
    print(json.dumps({k:len(result[k]) for k in ['local','components','completion','generated','video']}),flush=True)

if __name__=='__main__':main()
