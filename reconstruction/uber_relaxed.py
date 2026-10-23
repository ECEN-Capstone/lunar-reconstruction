"""Deliberately relaxed generated-stereo sweep, isolated from production defaults."""
import argparse
import json
import zipfile
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from .geometry import ROOT, rectification, warp, transform_pixels
from .stereo import local_mesh
from .generated_stereo_trial import stats, digest
from .close_terrain import read_obj


def matcher(left,right,profile,reverse=False):
    n=512;block=profile['block_size']
    sgbm=cv2.StereoSGBM_create(minDisparity=-n+1 if reverse else 0,numDisparities=n,
        blockSize=block,P1=8*block*block,P2=32*block*block,disp12MaxDiff=profile['internal_lr_px'],
        preFilterCap=31,uniquenessRatio=profile['uniqueness_ratio'],speckleWindowSize=profile.get('speckle_window',0),
        speckleRange=2,mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
    left=np.pad(left,((0,0),(n,n)),mode='constant');right=np.pad(right,((0,0),(n,n)),mode='constant')
    return sgbm.compute(left,right)[:,n:-n].astype(np.float32)/16


def row_adjustment(aa,bb):
    """Fit right-row correction on 80% of matches; evaluate untouched 20%."""
    order=np.random.default_rng(42).permutation(len(aa));held=order[::5];train=np.setdiff1d(order,held)
    design=np.column_stack([(bb[:,0]-511.5)/1024,(bb[:,1]-511.5)/1024,np.ones(len(bb))])
    target=aa[:,1]-bb[:,1]
    initial=np.array([0,0,np.median(target[train])])
    fit=least_squares(lambda p:design[train]@p-target[train],initial,loss='soft_l1',f_scale=1.)
    a,b,c=fit.x
    h=np.array([[1.,0,0],[a/1024,1+b/1024,c-(a+b)*511.5/1024],[0,0,1.]])
    moved=transform_pixels(bb,h)
    report=dict(training_matches=len(train),heldout_matches=len(held),matrix=h.tolist(),
                before_heldout_error_px=stats(abs(aa[held,1]-bb[held,1])),
                after_heldout_error_px=stats(abs(aa[held,1]-moved[held,1])),
                note='Empirical right-row warp; changes camera model and does not establish metric depth')
    return h,report,held


def topology(v,f):
    if not len(f):
        return dict(components=0,largest_component_face_fraction=0,used_vertices=0)
    used,inv=np.unique(f,return_inverse=True);mapped=inv.reshape(-1,3)
    edges=np.concatenate([mapped[:,[0,1]],mapped[:,[1,2]],mapped[:,[2,0]]])
    graph=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(used),len(used)))
    count,labels=connected_components(graph,directed=False)
    face_counts=np.bincount(labels[mapped[:,0]])
    return dict(components=int(count),largest_component_face_fraction=float(face_counts.max()/len(f)),used_vertices=len(used))


def export_obj(path,v,f,uv,texture):
    used=np.unique(f);lookup=np.full(len(v),-1,dtype=int);lookup[used]=np.arange(len(used))
    v,uv,f=v[used],uv[used],lookup[f]
    cv2.imwrite(str(path.parent/'texture.png'),texture)
    (path.parent/'terrain.mtl').write_text('newmtl terrain\nKa 0.2 0.2 0.2\nKd 1 1 1\nKs 0 0 0\nd 1\nillum 1\nmap_Kd texture.png\n')
    with path.open('w') as file:
        file.write('# Uber relaxed experiment. Arbitrary baseline units, NOT metres.\n')
        file.write('mtllib terrain.mtl\no uber_relaxed\n')
        for p in v:
            file.write('v %.9f %.9f %.9f\n'%tuple(p))
        for p in uv:
            file.write('vt %.9f %.9f\n'%tuple(p))
        file.write('usemtl terrain\n')
        for face in f+1:
            file.write('f '+' '.join(f'{i}/{i}' for i in face)+'\n')
    rv,rf=read_obj(path)
    assert np.allclose(rv,v,rtol=0,atol=6e-10) and np.array_equal(rf,f)
    if len(f):
        tri=rv[rf]
        assert (np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)>0).all()
    return v,f


def run_profile(rect,masks,profile,k,aa,bb,held,out):
    out.mkdir()
    left,right=rect
    dl=matcher(left,right,profile);dr=matcher(right,left,profile,True)
    yy,xx=np.indices(dl.shape,dtype=np.float32);xr=xx-dl
    inside=masks[0]&(xr>=0)&(xr<1023)&(cv2.remap(masks[1].astype(np.uint8),xr,yy,cv2.INTER_NEAREST)>0)
    sampled=cv2.remap(dr,xr,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=-10000)
    lr=abs(dl+sampled)
    im=left.astype(np.float32);std=np.sqrt(np.maximum(cv2.boxFilter(im*im,-1,(7,7))-cv2.boxFilter(im,-1,(7,7))**2,0))
    ri=cv2.remap(right,xr,yy,cv2.INTER_LINEAR)
    valid=inside&(dl>=profile['min_disparity_px'])&(dl<511)
    if profile['external_lr_px'] is not None:
        valid&=(lr<=profile['external_lr_px'])&(sampled<=-profile['min_disparity_px'])
    valid&=(left>profile['light_min'])&(ri>profile['light_min'])&(std>=profile['texture_std'])
    z=np.full(dl.shape,np.nan,np.float32);z[valid]=k[0,0]/dl[valid]
    xyz=np.stack([(xx-k[0,2])*z/k[0,0],(yy-k[1,2])*z/k[1,1],z],axis=-1)
    cfg=dict(mesh_stride=3,mesh_max_relative_depth_jump=profile['relative_depth_jump'],
             mesh_max_edge_baselines=profile['edge_baselines'],baseline=1.)
    v,colors,f=local_mesh(xyz,valid,left,cfg)
    uv=np.stack([xx[::3,::3]/1023,1-yy[::3,::3]/1023],axis=-1)[valid[::3,::3]]
    mesh_stats=topology(v,f)
    v,f=export_obj(out/'uber_relaxed.obj',v,f,uv,left)
    # Measure agreement on held-out image correspondences, not ground truth.
    feat=aa[held];partner=bb[held];ix=np.rint(feat[:,0]).astype(int);iy=np.rint(feat[:,1]).astype(int)
    ok=(ix>=0)&(ix<1024)&(iy>=0)&(iy<1024)
    ix,iy,feat,partner=ix[ok],iy[ok],feat[ok],partner[ok]
    accepted=valid[iy,ix]
    reference_disparity=feat[:,0]-partner[:,0]
    error=abs(dl[iy[accepted],ix[accepted]]-reference_disparity[accepted])
    # Spatial texture difference after horizontal warp, only descriptive.
    difference=abs(left.astype(np.float32)-ri)
    tri=v[f]
    rel=np.ptp(tri[:,:,2],axis=1)/np.maximum(np.min(tri[:,:,2],axis=1),1e-8)
    np.savez_compressed(out/'arrays.npz',disparity_left_px=dl,disparity_right_px=dr,lr_error_px=lr,
                        validity=valid,xyz_baseline_units=xyz)
    cv2.imwrite(str(out/'validity.png'),valid.astype(np.uint8)*255)
    record=dict(profile=profile,accepted_pixels=int(valid.sum()),whole_image_fraction=float(valid.mean()),
        fraction_also_passing_2px_lr=float(np.mean((lr[valid]<=2)&(sampled[valid]<0))),
        lr_error_px=stats(lr[valid]),disparity_px=stats(dl[valid]),
        heldout_feature_count=int(len(held)),heldout_features_accepted=int(accepted.sum()),
        heldout_disparity_error_px=stats(error),photometric_difference_dn=stats(difference[valid]),
        mesh_vertices=len(v),mesh_triangles=len(f),mesh_topology=mesh_stats,
        triangle_fraction_over_10pct_depth_jump=float(np.mean(rel>.1)),
        units='arbitrary baseline=1; no physical scale',obj_readback_verified=True)
    (out/'metrics.json').write_text(json.dumps(record,indent=2))
    return record,valid,dl,v,f


def render_meshes(out,models):
    fig=plt.figure(figsize=(16,6),layout='constrained')
    for i,(title,v,f) in enumerate(models):
        ax=fig.add_subplot(1,len(models),i+1,projection='3d')
        # Show the complete exported mesh; no outlier cropping or hidden smoothing.
        display=v[:,[0,2,1]].copy();display[:,2]*=-1
        tri=display[f]
        depth=v[f,2].mean(axis=1)
        color=plt.get_cmap('viridis')((depth-depth.min())/max(float(np.ptp(depth)),1e-6))
        ax.add_collection3d(Poly3DCollection(tri,facecolors=color,edgecolors='none',rasterized=True))
        lo=display.min(axis=0);hi=display.max(axis=0)
        ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),zlim=(lo[2],hi[2]),
               xlabel='X',ylabel='Forward',zlabel='Up',title=title)
        ax.set_box_aspect(np.maximum(hi-lo,.01));ax.view_init(25,-65)
    fig.suptitle(out.name+' | Uber relaxed: entire exported meshes, arbitrary baseline units')
    fig.savefig(out/'mesh_comparison.png',dpi=150);plt.close(fig)


def report(root,results,config):
    lines=['# Uber relaxed','',
        '## Findings','',
        'Simply relaxing thresholds produces more triangles but no convincing full terrain reconstruction. '
        'Removing almost all rejection creates long spikes, including geometry from the sky. '
        'Trial 1 improves materially after an empirical row correction; trial 2 has too few reliable correspondences '
        'to support a similarly strong conclusion. The meshes are open experimental surfaces, not closed simulator collision assets.','',
        'Coverage below is accepted disparity pixels divided by the entire 1024 x 1024 image, including sky; '
        'it is not terrain area, mesh area, or a claim that all those pixels survive triangle construction.','',
        'Experimental generated-stereo rule sweep. Existing production defaults and prior outputs are unchanged. '
        'The named admission gate is 16 matches, median row error <=30 px, and p90 <=60 px; both generated pairs are admitted. '
        'This affects acceptance only; it cannot make horizontal SGBM search different image rows.','',
        '## Sweep','',
        '| Pair | Profile | Whole-image coverage | Pass 2 px LR among accepted | Triangles | Largest connected component |',
        '|---|---|---:|---:|---:|---:|']
    for pair in results:
        for p in pair['profiles']:
            lines.append(f"| {pair['name']} | {p['profile']['name']} | {p['whole_image_fraction']:.1%} | {p['fraction_also_passing_2px_lr']:.1%} | {p['mesh_triangles']:,} | {p['mesh_topology']['largest_component_face_fraction']:.1%} |")
    lines += ['', 'Previous diagnostic whole-image coverage: trial 1 strict 0.55%, relaxed 4.12%; '
              'trial 2 strict 0.61%, relaxed 4.00%. These runs already ignored the failed camera gate.', '',
              '## What was relaxed','',
              '- Matching uniqueness: 15 originally, 5 relaxed, now 2 or 0. Speckle rejection is disabled in the five original sweep variants.',
              '- Internal and external LR tolerance: originally 1 px, up to 16 px in uber relaxed. '
              'No-checks requests 512 px internally (the entire disparity search width) and removes the external check.',
              '- Minimum disparity: 16 originally, 8 / 4 / 1 px. Near-zero positive disparity allows extremely distant geometry.',
              '- Texture and brightness gates are progressively removed. Rectification overlap, valid correspondence image bounds, '
              'positive disparity and the SGBM search bound are retained.',
              '- Mesh discontinuity limit: original 2%, now 10%, 50%, or effectively unlimited. '
              'Triangle edge limits increase from 0.25 baselines to 1, 10, or effectively unlimited.',
              '- Wide-window variant uses 21 x 21 matching blocks. Larger blocks sacrifice local detail.',
              '- Row-adjusted variant additionally fits a vertical affine correction to the right image using 80% of feature matches. '
              'The held-out 20% evaluates alignment and disparity independently of that fit. '
              'This is an empirical camera-model change, not merely a relaxed threshold.','',
              'The two additional row-adjusted follow-ups restore 1 px internal LR rejection, 1–2 px external LR rejection, '
              'uniqueness 5 or 15, speckle rejection, and mesh depth-jump limits of 5% or 2%. '
              'Both retain the lower 4 px minimum disparity and brightness >4, and do not restore saturation masking. '
              'The strict-matching name therefore does not mean every original production gate is restored.','',
              '## Geometry gate and held-out evidence','',
              'Original admission requires >=40 matches, median row error <=1 px and p90 <=2 px. '
              'The following measured thresholds are the minimum needed to admit each pair under the original camera model:', '',
              '| Pair | Available gate matches | Required median allowance | Required p90 allowance |',
              '|---|---:|---:|---:|']
    for pair in results:
        g=pair['original_gate_measurements']
        lines.append(f"| {pair['name']} | {g['count']} | {g['median']:.2f} px | {g['p90']:.2f} px |")
    for pair in results:
        a=pair['row_adjustment']
        lines += ['',f"### {pair['name']}",'',
            f"Row correction used {a['training_matches']} training matches and {a['heldout_matches']} held-out matches. "
            f"Held-out median vertical error changed from {a['before_heldout_error_px']['median']:.2f} to "
            f"{a['after_heldout_error_px']['median']:.2f} px; corrected p90 is {a['after_heldout_error_px']['p90']:.2f} px.", '',
            '| Profile | Accepted held-out matches | Median disparity disagreement | p90 disagreement |',
            '|---|---:|---:|---:|']
        for p in pair['profiles']:
            e=p['heldout_disparity_error_px']
            med=f"{e['median']:.2f}" if e['count'] else 'N/A'
            p90=f"{e['p90']:.2f}" if e['count'] else 'N/A'
            lines.append(f"| {p['profile']['name']} | {e['count']}/{p['heldout_feature_count']} | {med} px | {p90} px |")
    lines += ['', 'The held-out split applies to fitting the row warp, not unseen images. '
              'Disparity disagreement is evaluated only where each profile accepts a held-out feature, '
              'so low error with few retained features cannot establish accuracy across the full scene. '
              'These features are image correspondences, not measured 3D ground truth.','',
              '## Files and interpretation','',
              'Each profile contains `uber_relaxed.obj`, `terrain.mtl`, `texture.png`, arrays, validity and metrics. '
              'Keep the OBJ, MTL and PNG together for texture. Geometry uses arbitrary baseline units, NOT metres. '
              'No hole filling, manual geometry edits, outlier cropping or smoothing was used to make these mesh previews. '
              'A large connected component means a more connected mesh, not correct stereo depth. '
              'The consistency and feature checks use image agreement; no ground truth exists for these generated images.', '',
              'See `comparison.png` for masks/disparities and `mesh_comparison.png` for full mesh geometry in each trial. '
              'The viewer ZIP contains all seven profiles for each trial (14 textured OBJ meshes).','',
              'Run: `python -m reconstruction.uber_relaxed --output output/uber_relaxed_new`. '
              'The input split images and reference features come from the existing generated-stereo experiment.']
    (root/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='output/uber_relaxed')
    parser.add_argument('--resume',action='store_true',help='Reuse verified profile outputs and run newly added profiles')
    args=parser.parse_args();root=ROOT/args.output;root.mkdir(parents=True,exist_ok=args.resume)
    config=json.loads((ROOT/'configs/uber_relaxed.json').read_text())
    (root/'config.json').write_text(json.dumps(config,indent=2))
    source=ROOT/'output/generated_stereo_trial'
    prior=json.loads((source/'results.json').read_text())
    cv2.setNumThreads(4);cv2.setRNGSeed(42)
    k,_,_,hs=rectification();results=[]
    for name in ['stereo_trial_1','stereo_trial_2']:
        out=root/name;out.mkdir(exist_ok=args.resume)
        inputs=[source/name/f'{eye}_1024.png' for eye in ['left','right']]
        hashes=[digest(p) for p in inputs]
        if args.resume and (out/'results.json').exists():
            assert json.loads((out/'results.json').read_text())['input_sha256']==hashes, 'Cached inputs changed'
        images=[cv2.imread(str(p),0) for p in inputs]
        rect=[warp(im,h) for im,h in zip(images,hs)]
        masks=[warp(np.full(im.shape,255,np.uint8),h)==255 for im,h in zip(images,hs)]
        features=np.load(source/name/'feature_geometry.npz');aa=features['rectified_left_xy'];bb=features['rectified_right_xy']
        adjustment,adj_report,held=row_adjustment(aa,bb)
        pair_prior=next(p for p in prior['pairs'] if p['name']==name)
        gate=pair_prior['geometry']['analysis_image_gate'];g=config['geometry_gate']
        admitted=gate['count']>=g['minimum_matches'] and gate['median']<=g['median_row_error_px'] and gate['p90']<=g['p90_row_error_px']
        pair=dict(name=name,row_adjustment=adj_report,original_gate_measurements=gate,
                  uber_relaxed_gate_passed=bool(admitted),profiles=[],input_sha256=hashes)
        displays=[];models=[]
        for profile in config['profiles']:
            use_rect=rect;use_masks=masks;use_bb=bb
            if profile.get('row_adjustment'):
                use_rect=[rect[0],warp(rect[1],adjustment)]
                use_masks=[masks[0],warp(masks[1].astype(np.uint8)*255,adjustment)==255]
                use_bb=transform_pixels(bb,adjustment)
                cv2.imwrite(str(out/'right_row_adjusted.png'),use_rect[1])
            profile_out=out/profile['name']
            if args.resume and (profile_out/'metrics.json').exists():
                record=json.loads((profile_out/'metrics.json').read_text())
                assert record['profile']==profile, 'Cached profile settings differ'
                saved=np.load(profile_out/'arrays.npz')
                valid=saved['validity'];dl=saved['disparity_left_px']
                v,f=read_obj(profile_out/'uber_relaxed.obj')
            else:
                record,valid,dl,v,f=run_profile(use_rect,use_masks,profile,k,aa,use_bb,held,profile_out)
            pair['profiles'].append(record);displays.append((profile['name'],valid,dl))
            if profile['name'] in ['uber_relaxed','uber_relaxed_no_checks','uber_relaxed_row_adjusted']:
                models.append((profile['name'],v,f))
            (out/'results.json').write_text(json.dumps(pair,indent=2))
            print(json.dumps(dict(pair=name,**record)),flush=True)
        fig,axes=plt.subplots(2,len(displays),figsize=(4*len(displays),8),layout='constrained')
        for i,(title,valid,dl) in enumerate(displays):
            axes[0,i].imshow(valid,cmap='gray');axes[0,i].set_title(title.replace('uber_relaxed','uber')+f'\n{valid.mean():.1%} of image')
            axes[1,i].imshow(np.where(valid,dl,np.nan),cmap='viridis',vmin=0,vmax=512)
            for ax in axes[:,i]:
                ax.axis('off')
        fig.suptitle(name+' | acceptance masks (top) and disparity 0–512 px (bottom)')
        fig.savefig(out/'comparison.png',dpi=140);plt.close(fig)
        render_meshes(out,models)
        assert hashes==[digest(p) for p in inputs]
        results.append(pair);(root/'results.json').write_text(json.dumps(results,indent=2))
    report(root,results,config)
    with zipfile.ZipFile(root/'uber_relaxed_meshes.zip','w' if args.resume else 'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in root.glob('stereo_trial_*/*/*'):
            if path.suffix in ['.obj','.mtl'] or path.name=='texture.png':
                archive.write(path,path.relative_to(root))
        archive.write(root/'REPORT.md','REPORT.md')
        archive.write(root/'config.json','config.json')
        archive.write(root/'results.json','results.json')


if __name__=='__main__':
    main()
