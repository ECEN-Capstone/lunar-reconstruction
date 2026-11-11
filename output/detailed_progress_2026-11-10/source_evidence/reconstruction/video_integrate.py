"""Fuse repeatable video estimates into the first terrain-completion method.

Stereo always wins. Output is a local simulation candidate, with per-vertex
provenance; a closed solid does not imply verified physical placement.
"""
import argparse
import json
import warnings
from pathlib import Path
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree
from .video_bridge import read,local_camera,points,bins,transform,DX,RUNS,summary
from .close_terrain import write_obj,export


def combine(runs,out):
    runs=list(map(Path,runs))
    records=[json.loads((r/'metrics.json').read_text()) for r in runs]
    if len(set(r['seed'] for r in records))<3:raise ValueError('Use three independent terrain seeds')
    if len(set(r['generator'] for r in records))!=1:
        raise ValueError('Do not combine different generation methods as seed replicates')
    ref=records[0]
    if any((r['endpoints'],r['pose'])!=(ref['endpoints'],ref['pose']) for r in records):
        raise ValueError('Pose sensitivity scenarios must be evaluated separately from seed variation')
    surfaces=[np.load(r/'surfaces.npz') for r in runs]
    s=surfaces[0]
    def anchor_poses(run):
        file=run/'anchor_trajectory.npz'
        if not file.exists():file=run/'trajectory.npz'
        return np.load(file)['T_world_from_camera'][[0,-1]]
    # Independently estimated video paths can differ; fusion requires the same
    # real endpoint coordinate anchors and grid, not identical interior poses.
    traj=anchor_poses(runs[0])
    for r,t in zip(runs[1:],surfaces[1:]):
        if not np.array_equal(t['stereo_m'],s['stereo_m'],equal_nan=True):
            raise ValueError('Seed replicates must preserve identical stereo anchors')
        if not np.array_equal(t['x'],s['x']) or not np.array_equal(t['y'],s['y']) or not np.allclose(traj,anchor_poses(r)):
            raise ValueError('Runs do not share the same grid and endpoint coordinate anchors')
    xy=np.stack(np.meshgrid(s['x'],s['y'],indexing='ij'),-1)
    h=s['stereo_m'].copy()
    strict=np.isfinite(h)
    labels=np.where(strict,1,0).astype('B')
    inside=np.isfinite(s['baseline_idw_m'])
    # Import actual first-pipeline gated relaxed terrain where available. The
    # held-out observation is never a source. Never average away strict cells.
    relaxed_sources=[]
    hulls=[]
    for name,T in zip(ref['endpoints'],traj[[0,-1]]):
        frame=read(name)
        p=points(frame,T)
        hulls.append(Delaunay(p[::4,:2]).find_simplex(xy.reshape(-1,2)).reshape(h.shape)>=0)
        f=RUNS/'r15_terrain_completion'/name/'terrain_grids.npz'
        if not f.exists():continue
        terrain=np.load(f); valid=terrain['labels']==2
        local=np.c_[terrain['xy_m'][valid],terrain['relaxed_gated_m'][valid]]
        sample=transform(local,T@np.linalg.inv(local_camera(frame)))
        z,n=bins(sample,xy)
        add=inside&(labels==0)&(n>0)
        h[add]=z[add];labels[add]=2
        relaxed_sources.append(dict(name=name,source=str(f.relative_to(RUNS)),added_cells=int(add.sum())))
    observed=labels>0
    baseline=LinearNDInterpolator(xy[observed],h[observed])(xy)
    # Use only actual reconstructed video cells (no interpolation between seed
    # results). Tolerance is the published first pipeline's 4 cm local envelope.
    samples=np.array([np.where(t['labels']==3,t['video_m'],np.nan) for t in surfaces])
    votes=np.isfinite(samples).sum(0)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning)
        med=np.nanmedian(samples,axis=0)
        spread=np.nanmax(samples,axis=0)-np.nanmin(samples,axis=0)
    add=(votes>=2)&(spread<=.04)&~observed&inside&np.isfinite(baseline)
    h[add]=med[add];labels[add]=3
    fallback=(labels==0)&inside&np.isfinite(baseline)
    h[fallback]=baseline[fallback];labels[fallback]=4
    valid=np.isfinite(h)
    np.testing.assert_array_equal(s['stereo_m'][strict],h[strict])
    out=out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(out/'integrated_grid.npz',xy_m=xy,height_m=h,labels=labels,
        seed_votes=votes,seed_height_range_m=spread,endpoint_A_footprint=hulls[0],endpoint_B_footprint=hulls[1])
    v=np.column_stack([xy[valid],h[valid]])
    # Triangulate exact integer grid indices; floating point XY accumulated
    # by arange can create nominally collinear slivers at the footprint rim.
    ij=np.argwhere(valid)
    faces=Delaunay(ij).simplices.copy()
    aij,bij,cij=ij[faces].transpose(1,0,2)
    cross=(bij[:,0]-aij[:,0])*(cij[:,1]-aij[:,1])-(bij[:,1]-aij[:,1])*(cij[:,0]-aij[:,0])
    faces=faces[cross!=0]
    tri=v[faces]
    sign=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])[:,2]
    faces[sign<0]=faces[sign<0,::-1]
    top=out/'terrain_top_m.obj'
    write_obj(top,v,faces)
    # Explicit vertex provenance also travels in an OBJ group/material
    # companion file; top CSV follows the actual on-disk OBJ vertex order.
    np.savetxt(out/'top_vertex_provenance.csv',
               np.column_stack([np.arange(1,len(v)+1),labels[valid],votes[valid]]),
               fmt='%d',delimiter=',',header='obj_vertex_id,source_label,video_seed_votes',comments='')
    closure=export(top,out/'closed',.25)
    gap=~hulls[0]&~hulls[1]&inside
    metrics=dict(endpoints=ref['endpoints'],pose=ref['pose'],seeds=[r['seed'] for r in records],
        grid_m=DX,top_area_m2=float(abs(sign).sum()/2),units='metres',frame='start rover local; nominal up',
        labels={'0':'unsupported','1':'strict endpoint stereo','2':'first-pipeline gated relaxed stereo',
                '3':'video consensus (synthetic)','4':'first-pipeline linear interpolation (synthetic)'},
        cell_counts={int(i):int((labels==i).sum()) for i in range(1,5)},relaxed_sources=relaxed_sources,
        new_video_cell_area_m2=float(add.sum()*DX**2),
        between_footprints_video_cells=int((gap&add).sum()),between_footprints_total_cells=int(gap.sum()),
        unchanged_strict_cells=int(strict.sum()),closure=closure,
        caveats=['Spatial footprint is a convex envelope, not a surveyed traverse.',
                 'Seed agreement is repeatability, not ground truth.',
                 'Interior cells without video support fall back to interpolation and are separately labelled.'])
    if (runs[0]/'validation.npz').exists():
        reference=np.load(runs[0]/'validation.npz')['heldout_m']
        test=np.isfinite(reference)&add
        metrics['holdout']=dict(name=ref['validation']['holdout'],consensus_video_m=summary(abs(h[test]-reference[test])),
            same_cell_linear_m=summary(abs(baseline[test]-reference[test])),
            same_cell_idw_m=summary(abs(s['baseline_idw_m'][test]-reference[test])),
            eligible_gap_cells=int((np.isfinite(reference)&inside&~observed).sum()))
    metrics['strict_to_video_max_change_m']=float(np.max(abs(h[strict]-s['stereo_m'][strict])))
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False))
    print(json.dumps({k:metrics[k] for k in ['endpoints','cell_counts','between_footprints_video_cells','top_area_m2','new_video_cell_area_m2']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();combine(a.runs,a.out)


