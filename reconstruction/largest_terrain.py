"""Audit local terrain footprints and export the largest as a closed block."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull, Delaunay
from scipy.stats import binned_statistic_2d
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from .geometry import ROOT, camera
from .inspect_outputs import read_ply
from .complete_terrain import interpolate
from .close_terrain import export, read_obj, write_obj


def cloud_in_rover_frame(path, observation):
    xyz,_,_=read_ply(path)
    provenance=json.loads((ROOT/'artifacts/runs/r11_filtered_batch'/observation/'provenance.json').read_text())
    rotation=np.asarray(provenance['R_rectified_from_source'])
    center,_=camera('left')
    return (xyz@rotation+center)*.001


def footprint(points):
    xy=points[:,:2]
    occupied,counts=np.unique(np.floor(xy/.05).astype(np.int64),axis=0,return_counts=True)
    supported=(occupied[counts>=2]+.5)*.05
    return dict(point_count=len(points),dimensions_xy_m=np.ptp(xy,axis=0).tolist(),
                raw_convex_hull_m2=float(ConvexHull(xy).volume),
                occupied_5cm_cells=int(len(supported)),occupied_5cm_cell_area_m2=len(supported)*.05**2,
                supported_cell_hull_m2=float(ConvexHull(supported).volume))


def audit():
    records=[]
    for p in sorted((ROOT/'artifacts/runs/r11_filtered_batch').glob('obs_*/points_calibration_units.ply')):
        records.append(dict(name=p.parent.name,kind='single_frame',path=p.relative_to(ROOT).as_posix(),
                            reference_observation=p.parent.name,**footprint(cloud_in_rover_frame(p,p.parent.name))))
    for p in sorted((ROOT/'artifacts/runs/r12_registration').glob('component_*/cloud_all_observed_calibration_units.ply')):
        obs=p.parent.name.removeprefix('component_')
        trajectory=json.loads((p.parent/'camera_trajectory.json').read_text())
        records.append(dict(name=p.parent.name,kind='registered_component',path=p.relative_to(ROOT).as_posix(),
                            reference_observation=obs,observations=list(trajectory['T_component_from_camera']),
                            **footprint(cloud_in_rover_frame(p,obs))))
    return sorted(records,key=lambda r:r['supported_cell_hull_m2'],reverse=True)


def build(record,out):
    source=ROOT/record['path']
    points=cloud_in_rover_frame(source,record['reference_observation'])
    step=.05
    lo=np.floor(points[:,:2].min(axis=0)/step)*step
    hi=np.ceil(points[:,:2].max(axis=0)/step)*step
    edges=[np.linspace(lo[i],hi[i],int(round((hi[i]-lo[i])/step))+1) for i in range(2)]
    height=binned_statistic_2d(points[:,0],points[:,1],points[:,2],'median',bins=edges).statistic
    count=binned_statistic_2d(points[:,0],points[:,1],points[:,2],'count',bins=edges).statistic
    height[count<2]=np.nan
    x,y=np.meshgrid(*[(e[1:]+e[:-1])/2 for e in edges],indexing='ij')
    xy=np.stack([x,y],axis=-1)
    supported=np.isfinite(height)
    filled,distance,inside=interpolate(xy[supported],height[supported],xy.reshape(-1,2))
    filled=filled.reshape(height.shape);distance=distance.reshape(height.shape);inside=inside.reshape(height.shape)
    filled[supported]=height[supported]
    valid=np.isfinite(filled)
    v=np.column_stack([xy[valid],filled[valid]])
    # Planar triangulation gives one height per XY and one simple convex boundary.
    # It also closes small staircase-boundary gaps without overlapping faces.
    faces=Delaunay(v[:,:2]).simplices.copy()
    top=v[faces];sign=np.cross(top[:,1]-top[:,0],top[:,2]-top[:,0])[:,2]
    faces[sign<0]=faces[sign<0,::-1]
    assert np.all(abs(sign)>1e-12)
    out.mkdir(parents=True,exist_ok=False)
    top_path=out/'terrain_top_m.obj';write_obj(top_path,v,faces)
    labels=np.zeros(height.shape,np.uint8);labels[valid]=2;labels[supported]=1
    np.savez_compressed(out/'terrain_grids.npz',xy_m=xy,observed_height_m=height,filled_height_m=filled,
                        distance_to_support_m=distance,labels=labels)
    closure=export(top_path,out/'closed',.25)
    projected_area=float(abs(sign).sum()/2)
    tri=v[faces]
    normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    slopes=np.degrees(np.arctan2(np.linalg.norm(normals[:,:2],axis=1),normals[:,2]))
    metrics=dict(source=record,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                 units='metres',frame='nominal rover-local frame of reference observation; gravity unverified',
                 grid_spacing_m=step,support_minimum_points_per_cell=2,
                 top_projected_area_m2=projected_area,top_dimensions_m=np.ptp(v,axis=0).tolist(),
                 observed_cells=int(supported.sum()),filled_cells=int((valid&~supported).sum()),
                 observed_cell_fraction=float(supported.sum()/valid.sum()),
                 fill_distance_p95_m=float(np.percentile(distance[valid&~supported],95)),
                 maximum_fill_distance_m=float(distance[valid&~supported].max()),
                 slope_p95_deg=float(np.percentile(slopes,95)),slope_max_deg=float(slopes.max()),
                 closure=closure,
                 limitations=['Convex footprint includes interpolated gaps; area is not wholly measured',
                   'Resampled median height surface replaces overlapping observed triangles',
                   'Single-height terrain cannot represent overhangs or hidden obstacles',
                   'Prior 6 m pilot error estimates do not validate this larger footprint',
                   'No flight, Gazebo collision, or absolute physical accuracy certification'])
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2))
    render(out,v,faces,xy,height,filled,labels)
    (out/'README.md').write_text(
        f"# Largest terrain: {record['name']}\n\n"
        f"Completed projected footprint: {projected_area:.2f} m². "
        f"Bounds: {np.ptp(v[:,0]):.2f} × {np.ptp(v[:,1]):.2f} m (not a full rectangle).\n\n"
        "Use `closed/terrain_closed_m.obj` or `closed/terrain_closed_m.stl`, at metre scale 1. "
        "The export is a single closed solid with no open edges, nonmanifold vertices, or inconsistent winding. "
        "Both formats were read back and checked. Side walls and a flat base 0.25 m below the lowest top point are artificial.\n\n"
        f"{supported.sum()/valid.sum():.1%} of interior grid cells have observed-point support; the rest are interpolated. "
        f"Maximum distance from an inferred grid cell to support: {distance[valid&~supported].max():.2f} m. "
        "The labels and distance array in `terrain_grids.npz` preserve that distinction.\n\n"
        "This is a local terrain patch, not a global lunar map. Grid spacing is 5 cm, not a statement of accuracy. "
        "Per-frame gravity, acquisition motion, unseen obstacles, and absolute accuracy remain uncertain. "
        "Geometry is prepared for import; flight readiness and simulator collision behavior have not been demonstrated.\n")
    return metrics


def render(out,vertices,faces,xy,observed,filled,labels):
    fig=plt.figure(figsize=(14,6),layout='constrained')
    ax=fig.add_subplot(1,2,1,projection='3d')
    v,f=read_obj(out/'closed/terrain_closed_m.obj')
    tri=v[f];colors=np.tile([.38,.38,.4,1.],(len(f),1))
    z=tri[:len(faces),:,2].mean(axis=1)
    colors[:len(faces)]=plt.get_cmap('terrain')((z-z.min())/max(np.ptp(z),1e-6))
    ax.add_collection3d(Poly3DCollection(tri,facecolors=colors,edgecolors='none',rasterized=True))
    ax.set(xlim=(v[:,0].min(),v[:,0].max()),ylim=(v[:,1].min(),v[:,1].max()),
           zlim=(v[:,2].min(),v[:,2].max()),xlabel='X forward (m)',ylabel='Y left (m)',zlabel='Nominal Z (m)',
           title='Closed terrain: actual exported triangles')
    ax.set_box_aspect(np.ptp(v,axis=0));ax.view_init(30,135)
    from matplotlib.ticker import MaxNLocator
    ax.zaxis.set_major_locator(MaxNLocator(3))
    ax=fig.add_subplot(1,2,2)
    im=ax.imshow(labels,origin='lower',extent=[xy[0,0,1]-.025,xy[0,-1,1]+.025,xy[0,0,0]-.025,xy[-1,0,0]+.025],
                 cmap=ListedColormap(['white','#267b4d','#edb04b']),vmin=0,vmax=2,interpolation='nearest')
    ax.set(xlabel='Y left (m)',ylabel='X forward (m)',title='Green: observed cells | gold: interpolated')
    fig.suptitle(out.name+' | metre-scale local terrain; walls/base are artificial')
    fig.savefig(out/'preview.png',dpi=150);plt.close(fig)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='output/largest_terrain')
    parser.add_argument('--build',action='store_true')
    args=parser.parse_args()
    out=ROOT/args.output
    if args.build and (out/'footprint_audit.json').exists():
        records=json.loads((out/'footprint_audit.json').read_text())
    else:
        out.mkdir(parents=True,exist_ok=False)
        records=audit()
        (out/'footprint_audit.json').write_text(json.dumps(records,indent=2))
    print(json.dumps(records[:12],indent=2),flush=True)
    if args.build:
        result=build(records[0],out/records[0]['name'])
        print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    main()
