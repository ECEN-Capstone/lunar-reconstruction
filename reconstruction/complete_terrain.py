"""Compare relaxed stereo and explicitly labelled terrain completion experiments.

Legacy evidence is never overwritten. Heights are cell medians in the CAHV rover
frame (nominal Z up), with millimetres converted to metres. The regular grid is
a 2.5D surface: it cannot represent overhangs. Inferred surfaces are not measured
terrain, and spatial holdouts measure internal consistency, not absolute error.
"""
import argparse
import csv
import hashlib
import json

import cv2
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import cKDTree, Delaunay
from scipy.stats import binned_statistic_2d
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.ticker import MaxNLocator

from .geometry import ROOT, camera, transform_pixels
from .investigate import DATA, matches
from .stereo import run
from .filter_clouds import filter_frame


def summary(values):
    v = np.asarray(values)
    v = v[np.isfinite(v)]
    if not len(v):
        return {'count': 0}
    return dict(count=int(len(v)), median=float(np.median(v)),
                p90=float(np.percentile(v, 90)), p95=float(np.percentile(v, 95)),
                maximum=float(v.max()), rmse=float(np.sqrt(np.mean(v*v))))


def grid_cloud(xyz, provenance, cfg):
    """Invert the documented rectification, including the calibrated camera C."""
    good = np.isfinite(xyz).all(axis=2)
    cl, _ = camera('left')
    p = (xyz[good] @ np.asarray(provenance['R_rectified_from_source']) + cl) * .001
    step = cfg['grid_m']
    xb, yb = cfg['forward_bounds_m'], cfg['lateral_bounds_m']
    nx, ny = int(round((xb[1]-xb[0])/step)), int(round((yb[1]-yb[0])/step))
    xe, ye = np.linspace(*xb, nx+1), np.linspace(*yb, ny+1)
    h = binned_statistic_2d(p[:,0], p[:,1], p[:,2], 'median', bins=[xe,ye]).statistic
    n = binned_statistic_2d(p[:,0], p[:,1], p[:,2], 'count', bins=[xe,ye]).statistic
    h[n < cfg['minimum_points_per_cell']] = np.nan
    x, y = np.meshgrid((xe[:-1]+xe[1:])/2, (ye[:-1]+ye[1:])/2, indexing='ij')
    return h, n, np.stack([x,y], axis=-1)


def interpolate(xy, heights, queries, method='linear'):
    hull = Delaunay(xy)
    inside = hull.find_simplex(queries) >= 0
    distance, ids = cKDTree(xy).query(queries, k=min(12,len(xy)))
    if method == 'linear':
        pred = np.asarray(LinearNDInterpolator(hull, heights)(queries))
    else:
        weights = 1/np.maximum(distance,1e-9)**2
        pred = (heights[ids]*weights).sum(axis=1)/weights.sum(axis=1)
        pred[~inside] = np.nan
    return pred, distance[:,0], inside


def holdout(h, xy, cfg, sampling='random'):
    """Remove entire physical disks; never retain relaxed observations in holes."""
    valid = np.isfinite(h)
    p, z = xy[valid], h[valid]
    rng = np.random.default_rng(cfg['seed'])
    count=min(len(p),cfg['holdout_patches_per_radius'])
    if sampling == 'random':
        centers = p[rng.choice(len(p),count,replace=False)]
    else:
        # Target local relief/outliers, with separated centres, to stress rocks
        # and edges that a random test may rarely sample.
        _,ids=cKDTree(p).query(p,k=min(20,len(p)))
        relief=np.abs(z-np.median(z[ids],axis=1))
        chosen=[]
        for i in np.argsort(relief)[::-1]:
            if not chosen or np.linalg.norm(p[chosen]-p[i],axis=1).min()>.3:
                chosen.append(i)
            if len(chosen)==count:
                break
        centers=p[chosen]
    results = []
    for radius in cfg['holdout_radii_m']:
        errors = {m: [] for m in ['linear','idw']}
        attempted, recovered, used_patches = 0, 0, 0
        per_patch = []
        for center in centers:
            removed = np.linalg.norm(p-center,axis=1) <= radius+1e-8
            if removed.sum() < 3 or (~removed).sum() < 20:
                continue
            used_patches += 1
            attempted += int(removed.sum())
            for method in errors:
                pred, distance, inside = interpolate(p[~removed], z[~removed], p[removed], method)
                ok = np.isfinite(pred)
                err = np.abs(pred[ok]-z[removed][ok])
                errors[method].extend(err.tolist())
                if method == 'linear':
                    recovered += int(ok.sum())
                    per_patch.append(dict(center_m=center.tolist(), removed=int(removed.sum()),
                                          recovered=int(ok.sum()), error_m=summary(err)))
        results.append(dict(sampling=sampling,radius_m=radius,diameter_m=2*radius,patches=used_patches,
                            removed_cell_evaluations=attempted,recovered_cell_evaluations=recovered,
                            methods={m:summary(e) for m,e in errors.items()}, linear_patches=per_patch))
    return results


def mesh_from_grid(h, xy):
    valid = np.isfinite(h)
    ids = np.full(h.shape,-1,dtype=np.int32)
    ids[valid] = np.arange(valid.sum())
    a,b,c,d = ids[:-1,:-1],ids[1:,:-1],ids[:-1,1:],ids[1:,1:]
    faces = np.concatenate([np.stack([a,b,c],-1).reshape(-1,3),
                            np.stack([b,d,c],-1).reshape(-1,3)])
    faces = faces[(faces>=0).all(axis=1)]
    vertices = np.column_stack([xy[valid],h[valid]])
    return vertices, faces


def export_mesh(path, h, xy, labels):
    v,f = mesh_from_grid(h,xy)
    with path.open('w') as out:
        out.write('# Metres. CAHV rover-local axes; nominal Z up, attitude unverified.\n')
        out.write('# Includes inferred terrain; see provenance and surface_labels.npy.\n')
        for point in v:
            out.write('v %.7f %.7f %.7f\n' % tuple(point))
        for face in f:
            out.write('f %d %d %d\n' % tuple(face+1))
    tri = v[f]
    normal = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    area_xy = normal[:,2]/2
    assert np.isfinite(v).all() and (area_xy > 0).all()
    slopes = np.degrees(np.arctan2(np.linalg.norm(normal[:,:2],axis=1),normal[:,2]))
    # Parse the actual serialized OBJ and verify face indices and winding.
    lines = path.read_text().splitlines()
    rv = np.array([[float(x) for x in s.split()[1:]] for s in lines if s.startswith('v ')])
    rf = np.array([[int(x)-1 for x in s.split()[1:]] for s in lines if s.startswith('f ')])
    assert rv.shape == v.shape and np.array_equal(rf,f) and np.allclose(rv,v,atol=6e-8)
    assert f.min() >= 0 and f.max() < len(v)
    face_labels = labels[np.isfinite(h)][f].max(axis=1)
    return dict(vertices=len(v),triangles=len(f),projected_surface_area_m2=float(area_xy.sum()),
                slopes_deg=summary(slopes),
                area_with_inferred_vertices_m2=float(area_xy[face_labels>=3].sum()),
                obj_readback_verified=True)


def feature_checks(row, relaxed_dir, strict_xyz):
    imgs = [cv2.imread(str(DATA/row[k]),0) for k in ['ncl_left_path','ncr_right_path']]
    a,b = matches(*imgs)
    prov = json.loads((relaxed_dir/'provenance.json').read_text())
    a,b = [transform_pixels(p,np.array(H)) for p,H in zip([a,b],prov['homographies'])]
    idx = np.rint(a).astype(int)
    inside = ((idx>=0)&(idx<1024)).all(axis=1) & (np.abs(a[:,1]-b[:,1])<1)
    a,b,idx = a[inside],b[inside],idx[inside]
    x,y = idx.T
    relaxed = np.load(relaxed_dir/'xyz_rectified_calibration_units.npy')
    dl = np.load(relaxed_dir/'disparity_left_px.npy')
    valid = np.isfinite(relaxed[y,x,2])
    added = valid & ~np.isfinite(strict_xyz[y,x,2])
    err = np.abs(dl[y,x]-(a[:,0]-b[:,0]))
    common = np.isfinite(relaxed[:,:,2]) & np.isfinite(strict_xyz[:,:,2])
    relative = np.abs(relaxed[:,:,2][common]/strict_xyz[:,:,2][common]-1)
    return dict(all_relaxed_feature_error_px=summary(err[valid]),
                added_feature_error_px=summary(err[added]),
                common_depth_relative_change=summary(relative),
                common_depth_change_over_10_percent_fraction=float(np.mean(relative>.1)))


def plot_results(out, old, combined, completed, xy, labels, metrics):
    step=float(xy[1,0,0]-xy[0,0,0])
    extent = [xy[0,0,1]-step/2,xy[0,-1,1]+step/2,xy[0,0,0]-step/2,xy[-1,0,0]+step/2]
    lo,hi = np.nanpercentile(combined,[2,98])
    fig,axes = plt.subplots(1,4,figsize=(16,6),layout='constrained')
    for ax,h,title in zip(axes[:3],[old,combined,completed],
                          ['Original stereo cells','Additional stereo support','Completed simulation surface']):
        im=ax.imshow(h,origin='lower',extent=extent,cmap='terrain',vmin=lo,vmax=hi)
        ax.set(title=title,xlabel='Y left (m)',ylabel='X forward (m)')
    fig.colorbar(im,ax=list(axes[:3]),shrink=.6,label='Nominal rover-frame height (m)')
    cmap=ListedColormap(['white','#19733c','#41b6c4','#f5bc42','#da572b'])
    im=axes[3].imshow(labels,origin='lower',extent=extent,cmap=cmap,norm=BoundaryNorm(np.arange(-.5,5),5))
    axes[3].set(title='Source of each surface cell',xlabel='Y left (m)',ylabel='X forward (m)')
    cb=fig.colorbar(im,ax=axes[3],ticks=range(5),shrink=.6)
    cb.ax.set_yticklabels(['Outside','Original','Relaxed','Balanced fill','Larger fill'])
    fig.suptitle(out.name+f' | {step*100:g} cm cells; shaded gaps are inferred, not observed')
    fig.savefig(out/'coverage_comparison.png',dpi=160);plt.close(fig)
    fig=plt.figure(figsize=(15,6),layout='constrained')
    for i,(h,title) in enumerate([(old,'Original gridded observations'),(completed,'Completed simulation surface')]):
        ax=fig.add_subplot(1,2,i+1,projection='3d')
        v,f=mesh_from_grid(h,xy)
        ax.plot_trisurf(v[:,0],v[:,1],v[:,2],triangles=f,cmap='terrain',vmin=lo,vmax=hi,
                        linewidth=0,antialiased=True)
        ax.set(xlabel='X forward (m)',ylabel='Y left (m)',zlabel='Z nominal up (m)',title=title)
        ax.set(xlim=(xy[:,:,0].min(),xy[:,:,0].max()),ylim=(xy[:,:,1].min(),xy[:,:,1].max()),
               zlim=(np.nanmin(completed)-.05,np.nanmax(completed)+.05))
        ax.set_box_aspect([np.ptp(xy[:,:,0]),np.ptp(xy[:,:,1]),max(.1,np.nanmax(completed)-np.nanmin(completed)+.1)])
        ax.zaxis.set_major_locator(MaxNLocator(3))
        ax.view_init(28,135)
    fig.suptitle(out.name+' | actual exported grid triangles; heights in metres')
    fig.savefig(out/'mesh_comparison.png',dpi=170);plt.close(fig)


def complete(obs, out, cfg):
    original=ROOT/'artifacts/runs/r11_filtered_batch'/obs
    old_xyz=np.load(original/'xyz_rectified_calibration_units.npy')
    prov=json.loads((original/'provenance.json').read_text())
    old,n,xy=grid_cloud(old_xyz,prov,cfg)
    new_xyz=np.load(out/'relaxed_filtered/xyz_rectified_calibration_units.npy')
    new,nn,_=grid_cloud(new_xyz,prov,cfg)
    observed=np.isfinite(old)
    dist,nearest=cKDTree(xy[observed]).query(xy.reshape(-1,2))
    dist,nearest=dist.reshape(old.shape),nearest.reshape(old.shape)
    delta=np.abs(new-old[observed][nearest])
    added=(~observed)&np.isfinite(new)&(dist<=cfg['relaxed_anchor_distance_m'])
    added &= delta <= cfg['relaxed_height_tolerance_m'] + np.tan(np.radians(cfg['relaxed_slope_envelope_deg']))*dist
    combined=old.copy();combined[added]=new[added]
    supported=np.isfinite(combined)
    pred,distance,inside=interpolate(xy[supported],combined[supported],xy.reshape(-1,2))
    pred,distance,inside=[a.reshape(old.shape) for a in [pred,distance,inside]]
    labels=np.zeros(old.shape,np.uint8);labels[observed]=1;labels[added]=2
    fill=inside & ~supported
    labels[fill & (distance<=cfg['balanced_fill_distance_m'])]=3
    labels[fill & (distance>cfg['balanced_fill_distance_m'])]=4
    full=combined.copy();full[fill]=pred[fill]
    np.save(out/'surface_labels.npy',labels)
    np.savez_compressed(out/'terrain_grids.npz',xy_m=xy,original_m=old,relaxed_gated_m=combined,
                        simulation_m=full,nearest_support_m=distance,labels=labels)
    validations=holdout(old,xy,cfg)+holdout(old,xy,cfg,'local_relief')
    (out/'spatial_holdout.json').write_text(json.dumps(validations,indent=2))
    meshes={}
    for name,limit in [('balanced',cfg['balanced_fill_distance_m']),
                       ('extended',cfg['extended_fill_distance_m']),('simulation',np.inf)]:
        surface=full.copy();surface[(distance>limit)&~supported]=np.nan
        meshes[name]=export_mesh(out/f'terrain_{name}_m.obj',surface,xy,labels)
        meshes[name]['filled_cells']=int((np.isfinite(surface)&~supported).sum())
        meshes[name]['covered_cells']=int(np.isfinite(surface).sum())
        meshes[name]['convex_hull_cell_coverage']=float(np.isfinite(surface).sum()/inside.sum())
    # Count projected area of the original image-grid mesh in the same crop.
    from .inspect_outputs import read_ply
    ov,_,of=read_ply(original/'local_mesh_calibration_units.ply')
    cl,_=camera('left');ov=(ov@np.array(prov['R_rectified_from_source'])+cl)*.001
    ot=ov[of];xb,yb=cfg['forward_bounds_m'],cfg['lateral_bounds_m']
    in_crop=((ot[:,:,0]>=xb[0])&(ot[:,:,0]<=xb[1])&(ot[:,:,1]>=yb[0])&(ot[:,:,1]<=yb[1])).all(axis=1)
    ot=ot[in_crop]
    original_area=np.abs(np.cross(ot[:,1]-ot[:,0],ot[:,2]-ot[:,0])[:,2]).sum()/2
    metrics=dict(observation=obs,strict_pixel_count=int(np.isfinite(old_xyz[:,:,2]).sum()),
                 relaxed_filtered_pixel_count=int(np.isfinite(new_xyz[:,:,2]).sum()),
                 original_grid_cells=int(observed.sum()),added_gated_stereo_cells=int(added.sum()),
                 rejected_new_stereo_cells=int(((~observed)&np.isfinite(new)&~added).sum()),
                 hull_cells=int(inside.sum()),original_mesh_projected_area_in_crop_m2=float(original_area),
                 original_grid_coverage=float(observed.sum()/inside.sum()),meshes=meshes,
                 max_fill_support_distance_m=float(distance[fill].max()),
                 strict_height_preservation_max_m=float(np.max(abs(full[observed]-old[observed]))))
    (out/'completion_metrics.json').write_text(json.dumps(metrics,indent=2))
    provenance=dict(units='metres; input CAHV positions interpreted as mm',
        unit_evidence='Iyer et al., LPSC 2024 abstract 1180, nominal Navcam baseline 240 mm; calibrated baseline 242.0594 mm',
        frame='CAHV rover-local frame, inverse rectification plus left C; nominal Z up; actual gravity unverified',
        interpolation='Linear Delaunay interpolation of median occupied grid cells; no extrapolation outside support convex hull',
        labels={'0':'outside footprint','1':'original stereo median','2':'relaxed stereo median, spatially gated',
                '3':'interpolated <= balanced radius from support','4':'larger interpolation / simulation assumption'},
        config=cfg,inputs=[dict(path=str(original.relative_to(ROOT)),
          xyz_sha256=hashlib.sha256((original/'xyz_rectified_calibration_units.npy').read_bytes()).hexdigest())],
        limitations=['spatial holdouts are not independent lunar ground truth',
          'interpolation can erase unseen rocks and craters; smooth does not mean safe',
          'grid spacing is not an accuracy claim',
          'single-valued height surface cannot represent overhangs',
          'convex hull can bridge disconnected patches and occlusions in simulation mode',
          'surface is open at perimeter; not a watertight solid; simulator collision untested',
          'stereo acquisition motion and per-frame attitude remain unresolved'])
    (out/'completion_provenance.json').write_text(json.dumps(provenance,indent=2))
    plot_results(out,old,combined,full,xy,labels,metrics)
    return metrics


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True)
    p.add_argument('--config',default='configs/completion.json');args=p.parse_args()
    cfg=json.loads((ROOT/args.config).read_text())
    out=ROOT/'artifacts/runs'/args.run;out.mkdir(parents=True,exist_ok=False)
    (out/'config.json').write_text(json.dumps(cfg,indent=2))
    rows={r['observation_id']:r for r in csv.DictReader((DATA/'stereo_pairs.csv').open())}
    stereo_cfg={**json.loads((ROOT/'configs/terrain.json').read_text()),**cfg['stereo_overrides']}
    filter_cfg={**json.loads((ROOT/'configs/filtering.json').read_text()),**cfg['support_overrides']}
    results=[]
    for obs in cfg['observations']:
        dest=out/obs;dest.mkdir()
        stereo_metrics=run(rows[obs],stereo_cfg,dest/'relaxed_stereo')
        filtered=filter_frame(dest/'relaxed_stereo',dest/'relaxed_filtered',filter_cfg)
        metrics=complete(obs,dest,cfg)
        strict=np.load(ROOT/'artifacts/runs/r11_filtered_batch'/obs/'xyz_rectified_calibration_units.npy')
        checks=feature_checks(rows[obs],dest/'relaxed_stereo',strict)
        metrics.update(stereo=stereo_metrics,filtered=filtered,stereo_consistency=checks)
        (dest/'completion_metrics.json').write_text(json.dumps(metrics,indent=2))
        results.append(metrics);(out/'summary.json').write_text(json.dumps(results,indent=2))
        print(json.dumps(metrics),flush=True)


if __name__=='__main__':
    main()
