"""Run conservative SGBM stereo and export auditable depth, cloud and local mesh."""
import argparse
import csv
import hashlib
import json
import platform
import time
from pathlib import Path
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .geometry import ROOT, camera, rectification, transform_pixels, warp, write_ply
from .investigate import DATA, matches


class ReconstructionRejected(ValueError):
    """The available image evidence does not support fixed-rig triangulation."""


def disparity(left, right, cfg, reverse=False):
    n, block = cfg['num_disparities'], cfg['block_size']
    low = -cfg['min_disparity']-n+1 if reverse else cfg['min_disparity']
    sgbm = cv2.StereoSGBM_create(minDisparity=low, numDisparities=n,
        blockSize=block, P1=8*block*block, P2=32*block*block,
        disp12MaxDiff=1, preFilterCap=31, uniquenessRatio=cfg['uniqueness_ratio'],
        speckleWindowSize=cfg['speckle_window_size'], speckleRange=cfg['speckle_range'],
        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
    if cfg.get('pad_search',False):
        # SGBM discards a fixed n-column strip even where a smaller disparity is
        # valid. Pad both inputs equally; crop back, then reject out-of-image
        # correspondences explicitly. Padding never creates accepted source rays.
        left=np.pad(left,((0,0),(n,n)),mode='constant')
        right=np.pad(right,((0,0),(n,n)),mode='constant')
        return sgbm.compute(left,right)[:,n:-n].astype(np.float32)/16.
    return sgbm.compute(left,right).astype(np.float32)/16.


def local_mesh(xyz, valid, color, cfg):
    """Only connect observed neighbours; holes and discontinuities stay open."""
    s=cfg['mesh_stride']; p=xyz[::s,::s]; v=valid[::s,::s]; c=color[::s,::s]
    indices=np.full(v.shape,-1,np.int32); indices[v]=np.arange(v.sum())
    a,b,cidx,d=indices[:-1,:-1],indices[:-1,1:],indices[1:,:-1],indices[1:,1:]
    faces=np.concatenate([np.stack([a,cidx,b],-1).reshape(-1,3),np.stack([b,cidx,d],-1).reshape(-1,3)])
    faces=faces[(faces>=0).all(axis=1)]
    vertices=p[v]
    if len(faces):
        tri=vertices[faces]
        dz=np.ptp(tri[:,:,2],axis=1)/np.min(tri[:,:,2],axis=1)
        edges=np.stack([np.linalg.norm(tri[:,i]-tri[:,j],axis=1) for i,j in [(0,1),(1,2),(2,0)]],axis=1)
        faces=faces[(dz<cfg['mesh_max_relative_depth_jump']) & (edges.max(axis=1)<cfg['mesh_max_edge_baselines']*cfg['baseline'])]
    return vertices,c[v],faces


def run(row, cfg, out):
    """Depth is axial Z in a shared rectified left camera, in CAHV center units."""
    out.mkdir(parents=True,exist_ok=False)
    started=time.time(); cv2.setRNGSeed(cfg['random_seed']); cv2.setNumThreads(4)
    keys=['nrl_left_path','nrr_right_path'] if cfg['family']=='NR' else ['ncl_left_path','ncr_right_path']
    paths=[DATA/row[k] for k in keys]
    imgs=[cv2.imread(str(p),cv2.IMREAD_GRAYSCALE) for p in paths]
    if any(im is None or im.shape!=(1024,1024) for im in imgs): raise ValueError('Unexpected source image')
    K,R,B,H=rectification(interpretation=cfg['interpretation'])
    # A plausible-looking cloud is not sufficient when the fixed rig model fails.
    check_imgs=imgs if cfg['family']=='NR' else [cv2.imread(str(DATA/row[k]),0) for k in ['nrl_left_path','nrr_right_path']]
    check_a,check_b=matches(*check_imgs)
    check_aa,check_bb=transform_pixels(check_a,H[0]),transform_pixels(check_b,H[1])
    residual=abs(check_aa[:,1]-check_bb[:,1])
    if len(residual)<40 or np.median(residual)>1 or np.percentile(residual,90)>2:
        rejection=dict(observation=row['observation_id'],status='rejected',matches=len(residual),
            reason='Fixed-rig geometry not supported by sufficient subpixel matches')
        (out/'rejected.json').write_text(json.dumps(rejection,indent=2))
        raise ReconstructionRejected(rejection)
    rect=[warp(im,h) for im,h in zip(imgs,H)]
    masks=[warp(np.full(im.shape,255,np.uint8),h)==255 for im,h in zip(imgs,H)]
    for name,im in zip(['left','right'],rect): cv2.imwrite(str(out/f'rectified_{name}.png'),im)
    processed=rect
    if cfg['preprocessing']=='clahe':
        clahe=cv2.createCLAHE(cfg['clahe_clip_limit'],(cfg['clahe_grid'],)*2)
        processed=[clahe.apply(im) for im in rect]
    elif cfg['preprocessing']!='none': raise ValueError('Unknown preprocessing')
    for name,im in zip(['left','right'],processed): cv2.imwrite(str(out/f'matching_{name}.png'),im)
    dl=disparity(*processed,cfg); dr=disparity(processed[1],processed[0],cfg,True)
    yy,xx=np.indices(dl.shape,dtype=np.float32); xr=xx-dl
    sampled=cv2.remap(dr,xr,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=-10000)
    lr=np.abs(dl+sampled)
    right_valid=cv2.remap(masks[1].astype(np.uint8),xr,yy,cv2.INTER_NEAREST)>0
    right_intensity=cv2.remap(rect[1],xr,yy,cv2.INTER_LINEAR)
    im=rect[0].astype(np.float32); w=(cfg['texture_window'],)*2
    std=np.sqrt(np.maximum(cv2.boxFilter(im*im,-1,w)-cv2.boxFilter(im,-1,w)**2,0))
    filters=dict(inside_rectification=masks[0]&right_valid&(xr>=0)&(xr<dl.shape[1]-1),
        disparity_range=(dl>=cfg['min_valid_disparity_px'])&(dl<cfg['min_disparity']+cfg['num_disparities']-1),
        left_right_consistent=(lr<=cfg['lr_threshold_px']) & (sampled<=-cfg['min_valid_disparity_px']),
        illuminated=(rect[0]>cfg['dark_threshold'])&(rect[0]<cfg['saturated_threshold'])&(right_intensity>cfg['dark_threshold'])&(right_intensity<cfg['saturated_threshold']),
        textured=std>=cfg['texture_std_threshold'])
    if cfg.get('raw_quality_mask',False):
        # Radiometric correction can turn clipped raw values into ordinary gray.
        # Assess information loss in original raw pixels, before interpolation.
        raw=[cv2.imread(str(DATA/row[k]),cv2.IMREAD_GRAYSCALE) for k in ['nrl_left_path','nrr_right_path']]
        good=[]
        for src,h in zip(raw,H):
            bad=((src<=cfg['dark_threshold'])|(src>=cfg['saturated_threshold'])).astype(np.uint8)
            bad=cv2.dilate(bad,np.ones((3,3),np.uint8))
            good.append(warp((1-bad)*255,h)==255)
        filters['raw_information_present']=good[0] & (cv2.remap(good[1].astype(np.uint8),xr,yy,cv2.INTER_NEAREST)>0)
    valid=np.logical_and.reduce(list(filters.values()))
    depth=np.full(dl.shape,np.nan,np.float32); depth[valid]=K[0,0]*B/dl[valid]
    xyz=np.stack([(xx-K[0,2])*depth/K[0,0],(yy-K[1,2])*depth/K[1,1],depth],axis=-1)
    np.save(out/'disparity_left_px.npy',dl); np.save(out/'disparity_right_px.npy',dr)
    np.save(out/'depth_calibration_units.npy',depth); np.save(out/'xyz_rectified_calibration_units.npy',xyz)
    np.save(out/'left_right_error_px.npy',lr)
    cv2.imwrite(str(out/'validity_mask.png'),valid.astype(np.uint8)*255)
    for name,mask in filters.items(): cv2.imwrite(str(out/f'mask_{name}.png'),mask.astype(np.uint8)*255)
    write_ply(out/'points_calibration_units.ply',xyz[valid],rect[0][valid])
    vertices,colors,faces=local_mesh(xyz,valid,rect[0],{**cfg,'baseline':B})
    write_ply(out/'local_mesh_calibration_units.ply',vertices,colors,faces)
    # A readable OBJ companion is widely supported by simulators, but is not metric-certified.
    with (out/'local_mesh_calibration_units.obj').open('w') as f:
        f.write('# Source CAHV units; frame x right, y down, z forward. Not metre certified.\n')
        for p in vertices: f.write('v %.6f %.6f %.6f\n'%tuple(p))
        for face in faces: f.write('f %d %d %d\n'%tuple(face+1))
    a,b=matches(*imgs); aa,bb=transform_pixels(a,H[0]),transform_pixels(b,H[1])
    ix=np.rint(aa[:,0]).astype(int); iy=np.rint(aa[:,1]).astype(int)
    inside=(ix>=0)&(ix<1024)&(iy>=0)&(iy<1024)
    ix,iy,aa,bb=ix[inside],iy[inside],aa[inside],bb[inside]
    evaluated=valid[iy,ix] & (abs(aa[:,1]-bb[:,1])<1)
    error=abs(dl[iy[evaluated],ix[evaluated]]-(aa[evaluated,0]-bb[evaluated,0]))
    metrics=dict(observation=row['observation_id'],valid_points=int(valid.sum()),valid_fraction=float(valid.mean()),
        filter_pass_fractions={k:float(v.mean()) for k,v in filters.items()},
        depth_percentiles_calibration_units=np.percentile(depth[valid],[5,50,95]).tolist() if valid.any() else [],
        lr_error_median_px=float(np.median(lr[valid])) if valid.any() else None,
        feature_matches=len(a),feature_vertical_median_px=float(np.median(abs(aa[:,1]-bb[:,1]))) if len(aa) else None,
        feature_disparity_comparisons=int(len(error)),feature_disparity_error_median_px=float(np.median(error)) if len(error) else None,
        feature_disparity_error_p90_px=float(np.percentile(error,90)) if len(error) else None,
        mesh_vertices=len(vertices),mesh_faces=len(faces),runtime_seconds=time.time()-started)
    provenance=dict(config=cfg,observation=row,inputs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
        K=K.tolist(),R_rectified_from_source=R.tolist(),baseline_calibration_units=B,homographies=[h.tolist() for h in H],
        units='source CAHV center units, physical unit unavailable',frame='origin left camera center; x toward right center; y down; z forward',
        metric_certified=False,assumptions=['stationary rig between left/right acquisition','linear CAHV applicable to imagery; residual distortion unmodelled'],
        python=platform.python_version(),opencv=cv2.__version__,numpy=np.__version__)
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2)); (out/'metrics.json').write_text(json.dumps(metrics,indent=2))
    fig,axes=plt.subplots(2,3,figsize=(15,10))
    for ax,im,title in zip(axes[0,:2],rect,['Rectified left','Rectified right']):
        ax.imshow(im,cmap='gray',vmin=0,vmax=255)
        for y in range(64,1024,128): ax.axhline(y,color='lime',lw=.4)
        ax.set_title(title)
    axes[0,2].imshow(valid,cmap='gray'); axes[0,2].set_title(f'Validity: {valid.mean():.1%}')
    for ax,data,title in [(axes[1,0],np.where(valid,dl,np.nan),'Disparity (pixels)'),(axes[1,1],depth,'Axial depth (calibration units)')]:
        vmin,vmax=np.nanpercentile(data,[2,98]) if valid.any() else (0,1)
        plotted=ax.imshow(data,cmap='viridis',vmin=vmin,vmax=vmax); fig.colorbar(plotted,ax=ax,shrink=.7); ax.set_title(title)
    axes[1,2].scatter(aa[:,0],aa[:,1],c=aa[:,1]-bb[:,1],cmap='coolwarm',vmin=-2,vmax=2,s=3)
    axes[1,2].set_xlim(0,1024);axes[1,2].set_ylim(1024,0);axes[1,2].set_title('Feature vertical residual (-2 to +2 px)')
    fig.suptitle(f"{out.name}: {row['observation_id']} | {cfg['family']} | {cfg['preprocessing']} | source units, not metres")
    fig.tight_layout();fig.savefig(out/'diagnostics.png',dpi=120);plt.close(fig)
    if valid.any():
        pts=xyz[valid][::max(1,int(valid.sum()/25000))]; col=rect[0][valid][::max(1,int(valid.sum()/25000))]
        fig=plt.figure(figsize=(12,5)); ax=fig.add_subplot(121,projection='3d')
        ax.scatter(pts[:,0],pts[:,2],-pts[:,1],c=col,cmap='gray',s=.2,vmin=0,vmax=255)
        ax.set(xlabel='X (calibration units)',ylabel='Z forward',zlabel='-Y up'); ax.view_init(25,-65)
        ax=fig.add_subplot(122);ax.scatter(pts[:,0],pts[:,2],c=-pts[:,1],cmap='terrain',s=.3)
        ax.set(xlabel='X (calibration units)',ylabel='Z (calibration units)',title='Top projection; color is -Y, not gravity height');ax.set_aspect('equal')
        fig.tight_layout();fig.savefig(out/'point_cloud_views.png',dpi=150);plt.close(fig)
    print(json.dumps(metrics),flush=True)
    return metrics


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='configs/baseline.json')
    parser.add_argument('--observation',default='obs_003');parser.add_argument('--run',required=True)
    parser.add_argument('--family',choices=['NR','NC']);parser.add_argument('--preprocessing',choices=['none','clahe'])
    args=parser.parse_args();cfg=json.loads((ROOT/args.config).read_text())
    for k in ['family','preprocessing']:
        if getattr(args,k):cfg[k]=getattr(args,k)
    rows=list(csv.DictReader((DATA/'stereo_pairs.csv').open()))
    row=next(r for r in rows if r['observation_id']==args.observation)
    run(row,cfg,ROOT/'artifacts/runs'/args.run)


if __name__=='__main__':main()
