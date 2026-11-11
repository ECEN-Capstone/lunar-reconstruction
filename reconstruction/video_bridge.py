"""Pose-conditioned lunar video, video-only triangulation and stereo integration.
Run python -m reconstruction.video_bridge --help. Coordinates are metres.
"""
import argparse
import csv
import heapq
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree, Delaunay
from scipy.spatial.transform import Rotation, Slerp

from .geometry import ROOT, camera
from .complete_terrain import export_mesh, summary

RUNS = ROOT / 'artifacts/runs'
DX = .05
SIZE = 512
NFRAMES = 33
MAX_RANGE = 11.
CENTRE = camera('left')[0] * .001


def read(name):
    folder = RUNS / 'r11_filtered_batch' / name
    meta = json.loads((folder / 'provenance.json').read_text())
    image = cv2.imread(str(folder / 'rectified_left.png'), 0)
    if image is None:
        raise ValueError(f'No stereo anchor for {name}')
    depth = np.load(folder / 'xyz_rectified_calibration_units.npy') * .001
    return dict(name=name, image=image, xyz=depth, K=np.array(meta['K']),
                R=np.array(meta['R_rectified_from_source']),
                time=meta['observation']['left_timestamp'])


def transform(p, T):
    return p @ T[:3, :3].T + T[:3, 3]


def local_camera(frame):
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = frame['R'].T, CENTRE
    return T


def relative(a, b, exclude=()):
    """Lowest summed held-out pixel residual path in the accepted real pose graph."""
    edges = json.loads((RUNS/'r12_registration/registration_edges.json').read_text())
    graph = {}
    for e in edges:
        i, j = e['source'], e['target']
        if not e['accepted'] or i in exclude or j in exclude:
            continue
        T = np.array(e['T_target_from_source'])
        T[:3, 3] *= .001
        for f, t, m in [(i,j,np.linalg.inv(T)), (j,i,T)]:
            graph.setdefault(f, []).append((t,m,e['heldout_median_px']))
    queue = [(0., (a,), np.eye(4))]
    seen = set()
    while queue:
        cost, path, T = heapq.heappop(queue)
        n = path[-1]
        if n in seen:
            continue
        if n == b:
            return T, list(path)
        seen.add(n)
        for j,m,w in graph.get(n, []):
            if j not in seen:
                heapq.heappush(queue, (cost+w,path+(j,),T@m))
    return None, []


def pose_pair(a, b, withheld, distance_scale, yaw_offset):
    A = local_camera(a)
    rel, path = relative(a['name'], b['name'], [withheld])
    if rel is not None:
        return A, A@rel, dict(source='stereo registration', path=path)
    # Only use a documented movement with verified bounding image times.
    catalog=json.loads((ROOT/'configs/video_mobility_priors.json').read_text())
    prior=catalog.get(a['name']+':'+b['name'])
    if prior is None or not a['time']<prior['event_utc']<b['time'] or prior['ordering']!='turn_then_drive':
        raise ValueError('No accepted pose or documented mobility scenario for this pair')
    yaw=prior['turn_deg_ccw']+yaw_offset
    distance=prior['distance_m']*distance_scale
    angle = np.deg2rad(yaw)
    rot = Rotation.from_rotvec([0,0,angle]).as_matrix()
    rover = np.eye(4)
    rover[:3,:3] = rot
    rover[:3,3] = rot @ [distance,0,0]
    from .video_pose import refine_height
    B=rover@local_camera(b)
    B,tilt=refine_height(points(a,A),points(b,B),B)
    return A, B, dict(source='conditional mobility prior', height_refinement=tilt,
        reference=prior['reference'],
        distance_m=distance, turn_deg=yaw, achieved_pose_verified=False,
        assumptions='images bracket complete maneuver; planar initial pose; optional footprint-based tilt/elevation; achieved XY and yaw unverified')


def trajectory(A, B, mobility, yaw_deg=0):
    f = np.linspace(0,1,NFRAMES)
    # Model a turn followed by a drive for MID 036. Registered endpoints only
    # constrain the ends; their interpolated intermediate poses are hypothetical.
    r = np.minimum(f/.2,1) if mobility else f
    d = np.maximum(0,(f-.2)/.8) if mobility else f
    transforms = np.repeat(np.eye(4)[None],len(f),axis=0)
    transforms[:,:3,:3] = Slerp([0,1],Rotation.from_matrix([A[:3,:3],B[:3,:3]]))(r).as_matrix()
    transforms[:,:3,3] = (1-d[:,None])*A[:3,3] + d[:,None]*B[:3,3]
    if mobility:
        # Rotate offset optical centre about the rover body during the turn.
        turned=Rotation.from_rotvec([0,0,np.deg2rad(yaw_deg)]).as_matrix()@A[:3,:3]
        transforms[:,:3,:3]=Slerp([0,.2,1],Rotation.from_matrix([A[:3,:3],turned,B[:3,:3]]))(f).as_matrix()
        ra=transforms[:,:3,:3] @ A[:3,:3].T
        end_origin=B[:3,3]-ra[-1]@CENTRE
        transforms[:,:3,3] = (ra@CENTRE) + d[:,None]*end_origin
    return transforms


def points(frame, T):
    p=frame['xyz']
    p=p[np.isfinite(p).all(2)&(p[:,:,2]<MAX_RANGE)]
    return transform(p,T)


def bins(p, xy):
    """Cell medians. Reject points beyond grid, never clamp them to its rim."""
    from scipy.stats import binned_statistic_2d
    axes=[xy[:,0,0],xy[0,:,1]]
    e=[np.r_[x-DX/2,x[-1]+DX/2] for x in axes]
    if len(p)==0:
        return np.full(xy.shape[:2],np.nan),np.zeros(xy.shape[:2],int)
    h=binned_statistic_2d(*p.T,'median',bins=e).statistic
    count=np.histogram2d(*p[:,:2].T,bins=e)[0].astype(int)
    return h,count


def surface(a,b,A,B,seed):
    pa,pb=points(a,A),points(b,B)
    p=np.vstack([pa,pb])
    lo=np.floor(p[:,:2].min(0)/DX)*DX
    hi=np.ceil(p[:,:2].max(0)/DX)*DX
    xy=np.stack(np.meshgrid(*[np.arange(l,h+DX/2,DX) for l,h in zip(lo,hi)],indexing='ij'),-1)
    h,n=bins(p,xy)
    measured=(n>=2)
    flat=xy.reshape(-1,2)
    anchors=xy[measured]
    dist,idx=cKDTree(anchors).query(flat,k=12)
    w=1/np.maximum(dist,.005)**2
    base=((h[measured][idx]*w).sum(1)/w.sum(1)).reshape(h.shape)
    base[measured]=h[measured]
    inside=(Delaunay(anchors).find_simplex(flat)>=0).reshape(h.shape)
    # Independent seeded relief, tapered to zero at stereo anchors. Scale it
    # using observed local relief rather than copying a withheld observation.
    rng=np.random.default_rng(seed)
    scale=np.clip(np.nanmedian(abs(h[measured]-gaussian_filter(base,2)[measured]))*1.4826,.003,.04)
    noise=np.zeros_like(base)
    for sigma,amp in [(1,.4),(3,.65),(9,.6)]:
        component=gaussian_filter(rng.normal(size=base.shape),sigma)
        noise+=amp*component/max(component.std(),1e-8)
    predicted=base+scale*noise*np.minimum(dist[:,0].reshape(h.shape)/.3,1)
    return xy, measured, inside, base, predicted, scale


def scaled_K(frame):
    K=frame['K'].copy()
    s=SIZE/frame['image'].shape[1]
    K[:2]*=s
    K[:2,2]+=(s-1)/2
    return K


def project(p,T,K):
    q=(p-T[:3,3])@T[:3,:3]
    uv=q@K.T
    return uv[:,:2]/np.maximum(uv[:,2:],1e-8),q[:,2]


def sample(im, coord, mode=cv2.INTER_LINEAR):
    return cv2.remap(im, coord[:,:,0].astype('f'),coord[:,:,1].astype('f'),mode,
                     borderMode=cv2.BORDER_CONSTANT)


def ray_hits(rays, origin, xy0, height, support):
    """First surface crossing along each ray, including uphill terrain.

    March at half resolution, then refine the bracket at the original pixel.
    Only consecutive samples within the supported footprint define a crossing.
    """
    def residual(ray,t):
        uv=(origin[:2]+ray[:,:,:2]*np.asarray(t)[...,None]-xy0)/DX
        uv=uv.astype('f')
        h=cv2.remap(height,uv,None,cv2.INTER_LINEAR)
        mask=cv2.remap(support,uv,None,cv2.INTER_NEAREST)>0
        return origin[2]+ray[:,:,2]*t-h,mask
    ray=rays[::2,::2].astype('f')
    origin=origin.astype('f')
    hit=np.zeros(ray.shape[:2],'f')
    prev,valid=residual(ray,.28)
    t0=.28
    for t in np.linspace(.36,MAX_RANGE,111):
        cur,ok=residual(ray,t)
        cross=ok&valid&(prev*cur<=0)&(hit==0)
        f=abs(prev)/(abs(prev)+abs(cur)+1e-7)
        hit[cross]=(t0+f*(t-t0))[cross]
        prev,valid,t0=cur,ok,t
    t=cv2.resize(hit,(rays.shape[1],rays.shape[0]),interpolation=cv2.INTER_NEAREST)
    lo=np.maximum(.25,t-.14); hi=t+.14
    dlo,mlo=residual(rays,lo); dhi,mhi=residual(rays,hi)
    valid=(t>0)&mlo&mhi&(dlo*dhi<=0)
    for _ in range(7):
        mid=(lo+hi)/2
        diff,_=residual(rays,mid)
        left=dlo*diff<=0
        hi=np.where(left,mid,hi)
        lo=np.where(left,lo,mid)
        dlo=np.where(left,dlo,diff)
    return (lo+hi)/2,valid

def synthesize(out,a,b,A,B,poses,xy,inside,h,seed):
    # Fixed texture in world coordinates, with real projections where visible.
    # Ray/surface intersection uses the generated height field, never held-out data.
    rng=np.random.default_rng(seed)
    texstep=.009
    extent=xy[-1,-1]-xy[0,0]
    shape=np.ceil(extent[::-1]/texstep).astype(int)+2
    noise=rng.normal(0,1,shape).astype('f')
    texture=105+14*noise+30*gaussian_filter(noise,1)+55*gaussian_filter(noise,4)
    K=scaled_K(a)
    u,v=np.meshgrid(np.arange(SIZE),np.arange(SIZE))
    rays=np.stack([u,v,np.ones_like(u)],-1)@np.linalg.inv(K).T
    height=h.T.astype('f')
    masks=[]
    mask_height=inside.T.astype('f')
    sources=[]
    for frame,T in [(a,A),(b,B)]:
        sources.append((frame['image'],frame['xyz'][:,:,2],T,frame['K']))
    movie=out/'transition.mp4'
    writer=cv2.VideoWriter(str(movie),cv2.VideoWriter_fourcc(*'mp4v'),12,(SIZE,SIZE))
    if not writer.isOpened():
        raise RuntimeError('MP4 writer unavailable')
    try:
        for i,T in enumerate(poses):
            if i in (0,len(poses)-1):
                view=cv2.resize(sources[int(i>0)][0],(SIZE,SIZE),interpolation=cv2.INTER_AREA)
            else:
                ray=rays@T[:3,:3].T
                origin=T[:3,3]
                t,valid=ray_hits(ray.astype('f'),origin,xy[0,0].astype('f'),height,mask_height)
                xyz=origin+ray*t[:,:,None]
                uv=(xyz[:,:,:2]-xy[0,0])/DX
                terrain=sample(texture.astype('f'),uv*DX/texstep)
                val=terrain*.08
                weight=np.full(t.shape,.08)
                for j,(im,depth,S,k) in enumerate(sources):
                    pix,z=project(xyz.reshape(-1,3),S,k)
                    pix=pix.reshape(SIZE,SIZE,2)
                    z=z.reshape(t.shape)
                    intensity=sample(im,pix)
                    original=sample(depth,pix,cv2.INTER_NEAREST)
                    seen=(z>.1)&(intensity>5)&(intensity<250)&(pix.min(2)>1)&(pix.max(2)<im.shape[0]-2)
                    # Weak influence for unsupported depth; occlusion rejects
                    # projections behind an observed foreground stereo surface.
                    support=np.where(np.isfinite(original),np.exp(-np.minimum(abs(original-z),10)/.12),.25)
                    # Pick weights by world point and source depth only. With the
                    # same world point, every generated frame sees the same
                    # texture (no time-dependent dissolve of terrain details).
                    w=seen*support/np.maximum(z,1)**2*9
                    val+=intensity*w
                    weight+=w
                # The two distant panoramas supply appearance only where no terrain
                # is visible. Mask those pixels OUT of every reconstruction.
                far=origin+ray*80
                bgval=np.zeros(t.shape); bgweight=np.zeros(t.shape)
                for j,(im,depth,S,k) in enumerate(sources):
                    pix,z=project(far.reshape(-1,3),S,k)
                    col=sample(im,pix.reshape(SIZE,SIZE,2))
                    w=(col>0)*((i/(len(poses)-1)) if j else 1-i/(len(poses)-1))
                    bgval+=w*col; bgweight+=w
                view=np.clip(np.where(valid,val/weight,bgval/np.maximum(bgweight,.001)),0,255).astype('B')
            masks.append(np.ones(view.shape,bool) if i in (0,len(poses)-1) else valid)
            writer.write(cv2.cvtColor(view,cv2.COLOR_GRAY2BGR))
    finally:
        writer.release()
    np.savez_compressed(out/'support.npz',valid=np.stack(masks))
    return movie


def depth_holdout(a,b,A,B,radius):
    """Entire disks withheld from both endpoint depth maps after pose estimation.
    This tests missing-depth completion at fixed poses. Both photos remain inputs.
    """
    if radius<=0 or radius>.8:raise ValueError('Use a disk radius in (0, 0.8] metres')
    originals=np.vstack([points(a,A),points(b,B)])
    # Fixed physical lattice, independent of heights, coverage, or test errors.
    spacing=2*radius+.45
    def removed(xy):
        delta=np.remainder(xy+spacing/2,spacing)-spacing/2
        return np.sum(delta**2,axis=1)<=radius**2
    held=originals[removed(originals[:,:2])]
    for frame,T in [(a,A),(b,B)]:
        xyz=frame['xyz'].copy()
        ok=np.isfinite(xyz).all(2)
        idx=np.flatnonzero(ok)
        world=transform(xyz[ok],T)
        # Extra half cell diagonal buffer prevents adjacent, retained points
        # landing in an evaluated cell. Evaluation also excludes measured cells.
        delta=np.remainder(world[:,:2]+spacing/2,spacing)-spacing/2
        cut=(delta**2).sum(1)<=(radius+DX/np.sqrt(2))**2
        xyz.reshape(-1,3)[idx[cut]]=np.nan
        frame['xyz']=xyz
    return held

def run(args):
    from .video_triangulate import reconstruct, sweep, decode
    cv2.setNumThreads(4)
    a,b=read(args.start),read(args.end)
    if a['time']>=b['time']: raise ValueError('Endpoints must have strictly increasing camera timestamps')
    if args.holdout in (args.start,args.end): raise ValueError('An endpoint cannot be withheld')
    A,B,info=pose_pair(a,b,args.holdout,args.distance_scale,args.yaw_offset)
    if np.linalg.norm(B[:3,3]-A[:3,3])<.05: raise ValueError('Insufficient translation for video triangulation')
    out=args.out
    out.mkdir(parents=True,exist_ok=False)
    poses=trajectory(A,B,'conditional' in info['source'],info.get('turn_deg',0))
    hidden=depth_holdout(a,b,A,B,args.holdout_radius) if args.holdout_radius else None
    xy,measured,inside,base,h,scale=surface(a,b,A,B,args.seed)
    movie=synthesize(out,a,b,A,B,poses,xy,inside,h,args.seed)
    np.savez(out/'trajectory.npz',K=scaled_K(a),T_world_from_camera=poses,frame_shape=[SIZE,SIZE])
    p,err,windows=reconstruct(movie,out/'trajectory.npz',out/'triangulated.npz',out/'support.npz')
    raw,counts=bins(p,xy)
    # Filter the height envelope relative to nearby measured terrain before merging.
    # Report unfiltered error as well; this gate alone cannot validate a new bridge.
    raw[(counts<2)|~inside]=np.nan
        # Use endpoint stereo only to define a generous search volume. The matching
    # stage gets no endpoint elevations, no rendered depths and no holdout image.
    heights=base[measured]
    bounds=np.percentile(heights,[.1,99.9])+[-.4,.4]
    dense=sweep(decode(movie,out/'support.npz'),poses,scaled_K(a),xy,bounds)
    dense[~inside]=np.nan
    disagreement=np.isfinite(dense)&np.isfinite(raw)&(np.abs(dense-raw)>.10)
    raw=np.where(np.isfinite(dense),dense,raw)
    raw[disagreement]=np.nan
    video=np.where(np.abs(raw-base)<=.20,raw,np.nan)
    add=(~measured)&np.isfinite(video)
    merged=np.where(measured,base,np.where(add,video,np.nan))
    labels=np.where(measured,1,np.where(add,3,0)).astype('B')
    if not np.array_equal(base[measured],merged[measured]):
        raise RuntimeError('Stereo geometry was modified')
    axes=dict(x=xy[:,0,0],y=xy[0,:,1])
    np.savez_compressed(out/'surfaces.npz',**axes,stereo_m=np.where(measured,base,np.nan),
        baseline_idw_m=np.where(inside,base,np.nan),video_m=raw,merged_m=merged,labels=labels)
    mesh=export_mesh(out/'candidate_stereo_plus_video_m.obj',merged,xy,labels)
    record=dict(endpoints=[a['name'],b['name']],utc=[a['time'],b['time']],pose=info,
                endpoint_displacement_m=float(np.linalg.norm(A[:3,3]-B[:3,3])),
                seed=args.seed,generator='pose-conditioned textured stochastic elevation field',
                camera_frame='T_world_from_rectified_left; nominal rover axes at A; metres',
                grid_m=DX,relief_scale_m=float(scale),frames=len(poses),
                plane_sweep_cells=int(np.isfinite(dense).sum()),triangulation_windows=windows,video_tracks=len(p),reprojection_px=summary(err),
                stereo_cells=int(measured.sum()),new_video_cells=int(add.sum()),new_cell_area_m2=float(add.sum()*DX**2),
                mesh=mesh,labels={'0':'unsupported','1':'endpoint stereo','3':'synthetic video'},
                status='conditional candidate; unverified spatial placement' if 'conditional' in info['source'] else 'candidate; no held-out test')
    if args.holdout:
        # First access to holdout data; it must never affect synthesis, reconstruction or filtering.
        hold=read(args.holdout)
        if not a['time']<hold['time']<b['time']:raise ValueError('Holdout must be chronologically interior')
        rel,path=relative(a['name'],hold['name'])
        if rel is None: raise ValueError('Cannot register evaluation-only holdout')
        ref,n=bins(points(hold,A@rel),xy)
        ref[n<2]=np.nan
        region=np.isfinite(ref)&inside&~measured
        common=region&add
        def error(z,mask):
            return summary(np.abs(z[mask]-ref[mask]))
        baseline=error(base,common)
        candidate=error(video,common)
        acceptable=(candidate.get('count',0)>=100 and candidate['median']<=.05 and candidate['p90']<=.15)
        record['validation']=dict(holdout=args.holdout,eval_pose_path=path,reference='independent stereo cell median; not survey truth',
            measurable_gap_cells=int(region.sum()),tested_added_cells=int(common.sum()),reference_coverage=float(common.sum()/max(1,region.sum())),
            video_abs_height_error_m=candidate,matched_idw_abs_height_error_m=baseline,
            raw_before_envelope_m=error(raw,region&np.isfinite(raw)),
            measured_overlap_abs_height_error_m=error(base,measured&np.isfinite(ref)),
            passes_experimental_tolerance=acceptable,better_than_matched_idw_rmse=bool(candidate and candidate.get('rmse',np.inf)<baseline.get('rmse',np.inf)))
        record['status']='holdout passes exploratory height tolerances' if acceptable else 'holdout fails exploratory height tolerances'
        np.savez_compressed(out/'validation.npz',heldout_m=ref,scored_cells=common)
    if hidden is not None:
        z,count=bins(hidden,xy)
        eligible=np.isfinite(z)&(count>=2)&~measured&inside
        scored=eligible&add
        record['spatial_holdout']=dict(radius_m=args.holdout_radius,reference='withheld real stereo depth; endpoint poses fixed and photos available',
            eligible_cells=int(eligible.sum()),scored_cells=int(scored.sum()),
            coverage=float(scored.sum()/max(1,eligible.sum())),video_abs_height_error_m=summary(abs(video[scored]-z[scored])),
            matched_idw_abs_height_error_m=summary(abs(base[scored]-z[scored])))
        np.savez_compressed(out/'spatial_validation.npz',heldout_m=z,eligible=eligible,scored=scored)
    (out/'metrics.json').write_text(json.dumps(record,indent=2,allow_nan=False))
    print(json.dumps(record,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start',default='obs_044')
    p.add_argument('--end',default='obs_047')
    p.add_argument('--holdout')
    p.add_argument('--holdout-radius',type=float,default=0,help='Hide depth in physical disks at fixed poses, metres')
    p.add_argument('--seed',type=int,default=7)
    p.add_argument('--distance-scale',type=float,default=1)
    p.add_argument('--yaw-offset',type=float,default=0)
    p.add_argument('--out',type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
