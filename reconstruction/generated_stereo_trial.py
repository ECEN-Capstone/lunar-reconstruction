"""Split generated side-by-side pairs and test the existing stereo pipeline.

Production rejection is never bypassed. A separate diagnostic reuses the same
SGBM matcher and mesh builder after explicitly ignoring geometry rejection.
Diagnostic XYZ/OBJ coordinates use an arbitrary baseline of 1, not metres.
"""
import argparse
import csv
import hashlib
import json
import platform
import shutil
import zipfile
from pathlib import Path

import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .geometry import ROOT, camera, rectification, transform_pixels, warp
from .investigate import DATA, matches
from .stereo import ReconstructionRejected, disparity, local_mesh, run


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(values):
    v=np.asarray(values);v=v[np.isfinite(v)]
    if not len(v):
        return dict(count=0,median=None,p90=None,p95=None)
    return dict(count=len(v),median=float(np.median(v)),p90=float(np.percentile(v,90)),
                p95=float(np.percentile(v,95)))


def split_canvas(path,out):
    original=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
    if original is None:
        raise ValueError(f'Cannot read {path}')
    h,w=original.shape[:2]
    if w!=2*h:
        raise ValueError(f'Expected two square panels without gutter: got {w}x{h}')
    out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(path,out/'original_canvas.png')
    arrays=[]
    for eye,crop in [('left',original[:,:w//2]),('right',original[:,w//2:])]:
        native=out/f'{eye}_native.png'
        assert cv2.imwrite(str(native),crop)
        readback=cv2.imread(str(native),cv2.IMREAD_UNCHANGED)
        assert np.array_equal(readback,crop)
        arrays.append(readback)
        gray=cv2.imread(str(native),cv2.IMREAD_GRAYSCALE)
        normalized=cv2.resize(gray,(1024,1024),interpolation=cv2.INTER_AREA)
        assert cv2.imwrite(str(out/f'{eye}_1024.png'),normalized)
    assert np.array_equal(np.concatenate(arrays,axis=1),original)
    return dict(source=str(path),source_sha256=digest(path),canvas_wh=[w,h],native_panel_wh=[w//2,h],
                split_x=w//2,split_pixels_lossless=True,analysis_wh=[1024,1024],
                normalization='OpenCV grayscale then INTER_AREA resize; assumed same framing, not verified camera intrinsics')


def reciprocal(left,right):
    sift=cv2.SIFT_create(nfeatures=10000)
    kl,dl=sift.detectAndCompute(left,None);kr,dr=sift.detectAndCompute(right,None)
    if dl is None or dr is None or min(len(dl),len(dr))<2:
        return np.empty((0,2)),np.empty((0,2))
    bf=cv2.BFMatcher(cv2.NORM_L2)
    forward={a.queryIdx:a.trainIdx for a,b in bf.knnMatch(dl,dr,k=2) if a.distance<.75*b.distance}
    reverse={a.queryIdx:a.trainIdx for a,b in bf.knnMatch(dr,dl,k=2) if a.distance<.75*b.distance}
    pairs=[(a,b) for a,b in forward.items() if reverse.get(b)==a]
    return (np.asarray([kl[a].pt for a,b in pairs]).reshape(-1,2),
            np.asarray([kr[b].pt for a,b in pairs]).reshape(-1,2))


def fixed_geometry(left,right,out):
    a,b=reciprocal(left,right)
    cl,ml=camera('left');cr,mr=camera('right')
    pl=np.column_stack([ml,-ml@cl]);pr=np.column_stack([mr,-mr@cr])
    e=pr@np.r_[cl,1.]
    skew=np.array([[0,-e[2],e[1]],[e[2],0,-e[0]],[-e[1],e[0],0]])
    f=skew@pr@np.linalg.pinv(pl);f/=np.linalg.norm(f)
    ah=np.column_stack([a,np.ones(len(a))]);bh=np.column_stack([b,np.ones(len(b))])
    lines_r=ah@f.T;lines_l=bh@f
    residual=np.abs((bh*lines_r).sum(axis=1))
    error=.5*residual*(1/np.maximum(np.linalg.norm(lines_r[:,:2],axis=1),1e-12)
                       +1/np.maximum(np.linalg.norm(lines_l[:,:2],axis=1),1e-12))
    _,_,_,homographies=rectification()
    aa,bb=[transform_pixels(p,h) for p,h in zip([a,b],homographies)]
    cv2.setRNGSeed(42)
    pa,pb=matches(left,right)
    paa,pbb=[transform_pixels(p,h) for p,h in zip([pa,pb],homographies)]
    gate=stats(np.abs(paa[:,1]-pbb[:,1]))
    gate['passed']=bool(gate['count']>=40 and gate['median']<=1 and gate['p90']<=2)
    report=dict(reciprocal_sift_matches=len(a),symmetric_fixed_cahv_error_px=stats(error),
                fraction_within_2_px=float(np.mean(error<=2)) if len(error) else None,
                rectified_vertical_error_px=stats(abs(aa[:,1]-bb[:,1])),analysis_image_gate=gate,
                gate_input_note='Gate criterion on these analysis images; real production control runs check their original raw counterparts')
    np.savez_compressed(out/'feature_geometry.npz',left_xy=a,right_xy=b,
                        fixed_cahv_error_px=error,rectified_left_xy=aa,rectified_right_xy=bb)
    # Alternate geometry is only a feasibility diagnostic; do not replace calibration.
    report['alternate_geometry']=alternate_geometry(a,b)
    fig,axes=plt.subplots(1,3,figsize=(16,5),layout='constrained')
    canvas=np.hstack([left,right]);axes[0].imshow(canvas,cmap='gray',vmin=0,vmax=255)
    for i in np.linspace(0,len(a)-1,min(60,len(a)),dtype=int):
        color=plt.get_cmap('turbo')(min(error[i]/30,1))
        axes[0].plot([a[i,0],b[i,0]+1024],[a[i,1],b[i,1]],color=color,lw=.6)
    axes[0].set_title(f'{len(a)} reciprocal feature matches');axes[0].axis('off')
    axes[1].hist(error,bins=40,color='#407eac');axes[1].axvline(2,color='red',label='2 px reference')
    axes[1].set(xlabel='Fixed-calibration epipolar error (px)',ylabel='Matches',title='Original Navcam geometry')
    axes[1].legend()
    axes[2].scatter(aa[:,1],aa[:,1]-bb[:,1],s=3)
    axes[2].axhspan(-2,2,color='green',alpha=.15)
    axes[2].set(xlabel='Rectified left row',ylabel='Left minus right row (px)',title='Expected: same image row')
    fig.suptitle(out.name+' | generated stereo geometry check')
    fig.savefig(out/'geometry_check.png',dpi=140);plt.close(fig)
    return report


def alternate_geometry(a,b):
    if len(a)<40:
        return dict(status='insufficient_matches',matches=len(a),minimum=40)
    rng=np.random.default_rng(42);order=rng.permutation(len(a));held=order[::5];train=np.setdiff1d(order,held)
    cv2.setRNGSeed(42)
    f,mask=cv2.findFundamentalMat(a[train],b[train],cv2.FM_RANSAC,1.,.999)
    if f is None or f.shape!=(3,3) or mask is None:
        return dict(status='fundamental_fit_failed')
    inlier=mask.ravel().astype(bool)
    ok,h1,h2=cv2.stereoRectifyUncalibrated(a[train][inlier],b[train][inlier],f,(1024,1024))
    report=dict(training_matches=len(train),heldout_matches=len(held),training_f_inliers=int(inlier.sum()),
                calibration_reused=False,metric_scale_available=False)
    h,hmask=cv2.findHomography(a[train],b[train],cv2.RANSAC,2.)
    if h is not None:
        report['heldout_homography_transfer_error_px']=stats(np.linalg.norm(transform_pixels(a[held],h)-b[held],axis=1))
        report['training_homography_inlier_fraction']=float(hmask.mean())
    if not ok:
        report['status']='uncalibrated_rectification_failed';return report
    ra,rb=transform_pixels(a[held],h1),transform_pixels(b[held],h2)
    report.update(status='exploratory_fit_only',heldout_rectified_vertical_error_px=stats(abs(ra[:,1]-rb[:,1])),
                  homographies=[h1.tolist(),h2.tolist()],
                  caveat='A fitted projective geometry does not validate the intended cameras, parallax, or depth')
    return report


def dense_diagnostic(left,right,cfg,out,mode):
    """Execute matcher/filters/mesher with failed camera geometry clearly labelled."""
    out.mkdir()
    k,r,baseline,hs=rectification()
    rect=[warp(im,h) for im,h in zip([left,right],hs)]
    masks=[warp(np.full(im.shape,255,np.uint8),h)==255 for im,h in zip([left,right],hs)]
    dl=disparity(*rect,cfg);dr=disparity(rect[1],rect[0],cfg,True)
    yy,xx=np.indices(dl.shape,dtype=np.float32);xr=xx-dl
    sampled=cv2.remap(dr,xr,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=-10000)
    lr=abs(dl+sampled)
    right_valid=cv2.remap(masks[1].astype(np.uint8),xr,yy,cv2.INTER_NEAREST)>0
    right_intensity=cv2.remap(rect[1],xr,yy,cv2.INTER_LINEAR)
    im=rect[0].astype(np.float32);w=(cfg['texture_window'],)*2
    std=np.sqrt(np.maximum(cv2.boxFilter(im*im,-1,w)-cv2.boxFilter(im,-1,w)**2,0))
    filters=dict(inside_rectification=masks[0]&right_valid&(xr>=0)&(xr<1023),
        disparity_range=(dl>=cfg['min_valid_disparity_px'])&(dl<cfg['num_disparities']-1),
        left_right_consistent=(lr<=cfg['lr_threshold_px'])&(sampled<=-cfg['min_valid_disparity_px']),
        illuminated=(rect[0]>cfg['dark_threshold'])&(rect[0]<cfg['saturated_threshold'])
                   &(right_intensity>cfg['dark_threshold'])&(right_intensity<cfg['saturated_threshold']),
        textured=std>=cfg['texture_std_threshold'])
    valid=np.logical_and.reduce(list(filters.values()))
    # Unit baseline solely for visualizing the numerical output. No metric claim.
    z=np.full(dl.shape,np.nan,np.float32);z[valid]=k[0,0]/dl[valid]
    xyz=np.stack([(xx-k[0,2])*z/k[0,0],(yy-k[1,2])*z/k[1,1],z],axis=-1)
    vertices,colors,faces=local_mesh(xyz,valid,rect[0],{**cfg,'baseline':1.})
    np.save(out/'disparity_left_px.npy',dl);np.save(out/'disparity_right_px.npy',dr)
    np.save(out/'left_right_error_px.npy',lr);np.save(out/'INVALID_GEOMETRY_xyz_baseline_units.npy',xyz)
    for name,image in [('rectified_left',rect[0]),('rectified_right',rect[1]),('validity_mask',valid.astype(np.uint8)*255)]:
        cv2.imwrite(str(out/f'{name}.png'),image)
    for name,mask in filters.items():
        cv2.imwrite(str(out/f'mask_{name}.png'),mask.astype(np.uint8)*255)
    obj=out/'INVALID_GEOMETRY_mesh_baseline_units.obj'
    with obj.open('w') as file:
        file.write('# DIAGNOSTIC ONLY: original calibrated geometry FAILED. Not a valid reconstruction.\n')
        file.write('# Arbitrary baseline = 1; NOT metres or millimetres. No hole filling.\n')
        for p in vertices:
            file.write('v %.8f %.8f %.8f\n'%tuple(p))
        for f in faces:
            file.write('f %d %d %d\n'%tuple(f+1))
    if len(vertices):
        assert np.isfinite(vertices).all()
    if len(faces):
        assert faces.min()>=0 and faces.max()<len(vertices)
    result=dict(profile=mode,status='diagnostic_only_geometry_gate_failed',config=cfg,
        valid_pixels=int(valid.sum()),whole_image_valid_fraction=float(valid.mean()),
        pass_fractions={name:float(mask.mean()) for name,mask in filters.items()},
        left_right_error_px=stats(lr[valid]),disparity_px=stats(dl[valid]),
        vertices=len(vertices),triangles=len(faces),unit_baseline=1,physical_scale_available=False,
        raw_sensor_data_available=False,raw_quality_mask_applied=False,
        note='Valid mask means numerical matching/filter acceptance only; cannot override failed scene geometry')
    (out/'metrics.json').write_text(json.dumps(result,indent=2))
    fig,axes=plt.subplots(2,3,figsize=(15,9),layout='constrained')
    for ax,im,title in zip(axes[0,:2],rect,['Rectified left','Rectified right']):
        ax.imshow(im,cmap='gray');ax.set_title(title);ax.axis('off')
        for row in range(64,1024,128):
            ax.axhline(row,color='lime',lw=.35)
    axes[0,2].imshow(valid,cmap='gray');axes[0,2].set_title(f'Filter-accepted pixels: {valid.mean():.2%}');axes[0,2].axis('off')
    for ax,data,title in [(axes[1,0],np.where(valid,dl,np.nan),'Accepted disparity (px)'),
                          (axes[1,1],np.where(valid,lr,np.nan),'Left/right discrepancy (px)')]:
        plotted=ax.imshow(data,cmap='viridis');fig.colorbar(plotted,ax=ax,shrink=.7);ax.set_title(title);ax.axis('off')
    if len(vertices):
        axes[1,2].scatter(vertices[:,0],vertices[:,2],s=.4,c=colors,cmap='gray',vmin=0,vmax=255)
    axes[1,2].set(xlabel='X (arbitrary baseline units)',ylabel='Z (arbitrary baseline units)',
                  title=f'Diagnostic cloud: {len(faces):,} triangles')
    axes[1,2].set_aspect('equal')
    fig.suptitle(f'{out.parent.name} / {mode}: CAMERA GEOMETRY FAILED — not physical terrain',color='darkred')
    fig.savefig(out/'dense_diagnostic.png',dpi=140);plt.close(fig)
    return result


def pipeline_attempt(row,cfg,out):
    try:
        result=run(row,cfg,out)
        return dict(status='accepted',metrics=result)
    except ReconstructionRejected:
        return json.loads((out/'rejected.json').read_text())


def write_report(out,result):
    lines=['# Generated stereo pipeline experiment','',
           'Both supplied canvases were split losslessly; separate 1024 x 1024 grayscale analysis copies were prepared. '
           'Resize assumes the requested field of view and does not establish actual generated camera intrinsics.','',
           '## Results','',
           '| Pair | Reciprocal matches | Median fixed CAHV error (px) | p90 (px) | Within 2 px | Pipeline |',
           '|---|---:|---:|---:|---:|---|']
    for r in result['pairs']:
        g=r['geometry'];e=g['symmetric_fixed_cahv_error_px']
        lines.append(f"| {r['name']} | {g['reciprocal_sift_matches']} | {e['median']:.2f} | {e['p90']:.2f} | {g['fraction_within_2_px']:.1%} | {r['pipeline']['status']} |")
    lines += ['', 'The table uses all reciprocal SIFT matches without fitted-camera prefiltering. '
              'The production gate uses its existing 8,000-feature lower-contrast SIFT + fitted-F outlier rejection, '
              'then requires at least 40 matches, median rectified row error <=1 px and p90 <=2 px. '
              'The real production controls check original raw counterparts, while the independent analysis uses calibrated imagery. '
              'Their counts therefore differ. Real C has reasonable median/p90 independent calibration residuals, '
              'but the actual pipeline rejects it with only 24 usable matches, below the 40-match minimum.','',
              '## Dense matching despite failed geometry','',
              'These separate diagnostic runs deliberately ignore the failed camera check, while reusing '
              'the production SGBM matcher and mesh builder. They do NOT change the production gate. '
              'Intensity and texture masks operate on generated pixels; no real raw sensor data exists for these outputs.','',
              '| Generated pair | Profile | Filter-accepted pixels | Fraction of whole image | Mesh triangles |',
              '|---|---|---:|---:|---:|']
    for r in result['pairs']:
        for d in r.get('dense_diagnostics',[]):
            lines.append(f"| {r['name']} | {d['profile']} | {d['valid_pixels']:,} | {d['whole_image_valid_fraction']:.2%} | {d['triangles']:,} |")
    lines += ['', 'Any OBJ under `diagnostic_*` is named `INVALID_GEOMETRY_mesh_baseline_units.obj`: '
              'arbitrary baseline = 1, not metres or millimetres. These are numerical failure-case artifacts, '
              'not usable reconstructed lunar terrain. They are intentionally not hole-filled, fused, or made into collision assets.','',
              '## Interpretation','',
              'These two saved outputs do not preserve the original Navcam camera relationship under the requested framing. '
              'More feature matches or a denser SGBM mask cannot fix that. A fitted alternate fundamental matrix is explored '
              'with held-out features in `results.json`, but does not establish intended camera pose, physical scale, or correct depth. '
              'A near-planar image warp can also fit many features without proving useful stereo parallax.','',
              'For a controlled synthetic stereo test, render both cameras from one shared 3D scene with known calibration '
              'and depth ground truth. Existing metre-scale terrain can provide that scene. Image generation may then be evaluated '
              'as appearance augmentation without silently replacing the camera geometry.','',
              '## Reproduction','',
              'Run `python -m reconstruction.generated_stereo_trial --package <original-package-directory> --output <new-workspace-output-directory>`. '
              'Run names must be new. Original images are hashed before/after and never modified. '
              'Native halves are byte-equivalent in decoded pixels to their original canvas regions. '
              'Calibration files are checked against the package copies. '
              'The output contains split images, actual pipeline acceptance/rejection results, geometry visualizations, '
              'dense disparity/masks/XYZ/OBJ diagnostics, and full JSON metrics.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def package_splits(out,result):
    with zipfile.ZipFile(out/'split_stereo_images.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
        for pair in result['pairs']:
            if 'split' not in pair:
                continue
            for eye in ['left','right']:
                for size in ['native','1024']:
                    path=out/pair['name']/f'{eye}_{size}.png'
                    archive.write(path,path.relative_to(out).as_posix())
        archive.writestr('README.txt',
            'Native files are lossless 887 x 887 crops. 1024 files are resized grayscale analysis copies.\n'
            'Both generated pairs failed the original Navcam geometry check. Splitting is valid; stereo geometry is not verified.\n')
        archive.writestr('split_provenance.json',json.dumps({p['name']:p['split'] for p in result['pairs'] if 'split' in p},indent=2))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--output',default='output/generated_stereo_trial')
    args=parser.parse_args();package=args.package.resolve()
    out=ROOT/args.output;out.mkdir(parents=True,exist_ok=False)
    cv2.setNumThreads(4);cv2.setRNGSeed(42)
    for side in ['left','right']:
        filename=f'ch3_nav_{side}_cahv.txt'
        assert digest(package/'calibration'/filename)==digest(ROOT/'chandrayaan-3-documentation/nav/calibration'/filename)
    for filename in ['stereo_config.json','generation_record.json','Stereo-Pilot-Notes.md']:
        shutil.copyfile(package/filename,out/filename)
    base_cfg=json.loads((ROOT/'configs/terrain.json').read_text())
    result=dict(pairs=[],versions=dict(python=platform.python_version(),opencv=cv2.__version__,numpy=np.__version__),
                calibration_matches_package=True,physical_scale_for_generated_images_verified=False)
    rows={r['observation_id']:r for r in csv.DictReader((DATA/'stereo_pairs.csv').open())}
    for name,obs in [('real_A','obs_049'),('real_C','obs_050')]:
        dest=out/name;dest.mkdir()
        row=rows[obs]
        left,right=[cv2.imread(str(DATA/row[key]),0) for key in ['ncl_left_path','ncr_right_path']]
        g=fixed_geometry(left,right,dest)
        pipeline=pipeline_attempt(row,base_cfg,dest/'pipeline')
        r=dict(name=name,observation=obs,geometry=g,pipeline=pipeline)
        result['pairs'].append(r)
        (out/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(r),flush=True)
    for i in [1,2]:
        name=f'stereo_trial_{i}';source=package/'generated'/f'{name}.png';dest=out/name
        split=split_canvas(source,dest)
        left,right=[cv2.imread(str(dest/f'{eye}_1024.png'),0) for eye in ['left','right']]
        g=fixed_geometry(left,right,dest)
        row=dict(observation_id=name,source_kind='image_generated_synthetic')
        for key,eye in [('ncl_left_path','left'),('ncr_right_path','right'),('nrl_left_path','left'),('nrr_right_path','right')]:
            row[key]=str((dest/f'{eye}_1024.png').resolve())
        cfg={**base_cfg,'raw_quality_mask':False,'source_kind':'image_generated_synthetic'}
        pipeline=pipeline_attempt(row,cfg,dest/'pipeline')
        diagnostics=[]
        # Only perform the explicit bypass experiment when production rejects.
        if pipeline['status']=='rejected':
            for mode,overrides in [('strict',{}),('relaxed',dict(block_size=7,uniqueness_ratio=5,
                    speckle_window_size=50,lr_threshold_px=2.,texture_std_threshold=1.,
                    mesh_max_relative_depth_jump=.05,mesh_max_edge_baselines=.5))]:
                diagnostics.append(dense_diagnostic(left,right,{**cfg,**overrides},dest/f'diagnostic_{mode}',mode))
        assert digest(source)==split['source_sha256']
        r=dict(name=name,split=split,geometry=g,pipeline=pipeline,dense_diagnostics=diagnostics,source_unchanged=True)
        result['pairs'].append(r)
        (out/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(r),flush=True)
    write_report(out,result)
    package_splits(out,result)


if __name__=='__main__':
    main()
