"""Estimate and validate local multi-frame poses without inventing a global pose.

PnP uses prior-frame stereo depth and temporal SIFT observations. Held-out
reprojection and independent target depth gate each link. Disconnected pose
components remain separate. No commanded mobility is treated as measured pose.
"""
import argparse
import json
import csv
from collections import defaultdict, deque
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .geometry import ROOT, write_ply
from .investigate import matches


def estimate(a,b,cfg):
    ua,ub=matches(a['image'],b['image'])
    rec=dict(source=a['id'],target=b['id'],feature_matches=len(ua),accepted=False)
    if len(ua)<cfg['minimum_correspondences']:return rec,None
    ia=np.rint(ua).astype(int);ib=np.rint(ub).astype(int)
    x=a['xyz'][ia[:,1],ia[:,0]];xb=b['xyz'][ib[:,1],ib[:,0]]
    valid=np.isfinite(x).all(axis=1)
    x,xb,ua,ub=x[valid],xb[valid],ua[valid],ub[valid]
    rec['depth_correspondences']=len(x)
    if len(x)<cfg['minimum_correspondences']:return rec,None
    rng=np.random.default_rng(cfg['random_seed']);idx=rng.permutation(len(x));hold=idx[::5];train=np.setdiff1d(idx,hold)
    cv2.setRNGSeed(cfg['random_seed'])
    ok,rv,tv,inliers=cv2.solvePnPRansac(x[train].astype(np.float64),ub[train].astype(np.float64),a['K'],None,
        iterationsCount=2000,reprojectionError=cfg['ransac_reprojection_px'],confidence=.999,flags=cv2.SOLVEPNP_EPNP)
    if not ok or inliers is None or len(inliers)<cfg['minimum_pnp_inliers']:return rec,None
    ii=train[inliers.ravel()]
    rv,tv=cv2.solvePnPRefineLM(x[ii].astype(np.float64),ub[ii].astype(np.float64),a['K'],None,rv,tv)
    proj,_=cv2.projectPoints(x[hold],rv,tv,a['K'],None)
    error=np.linalg.norm(proj[:,0]-ub[hold],axis=1)
    R,_=cv2.Rodrigues(rv);trans=x@R.T+tv.ravel()
    both=np.isfinite(xb).all(axis=1)
    relative=np.linalg.norm(trans[both]-xb[both],axis=1)/np.linalg.norm(xb[both],axis=1)
    rec.update(pnp_inliers=len(ii),inlier_fraction=len(ii)/len(train),heldout_count=len(hold),
        heldout_median_px=float(np.median(error)),heldout_p90_px=float(np.percentile(error,90)),
        target_depth_checks=int(both.sum()),median_relative_3d_error=float(np.median(relative)) if len(relative) else None,
        feature_span_px=np.ptp(ua[ii],axis=0).tolist(),rotation_degrees=float(np.linalg.norm(rv)*180/np.pi),translation_calibration_units=tv.ravel().tolist())
    passed=(rec['inlier_fraction']>=cfg['minimum_inlier_fraction'] and rec['heldout_median_px']<=cfg['heldout_median_px']
        and rec['heldout_p90_px']<=cfg['heldout_p90_px'] and both.sum()>=cfg['minimum_depth_checks']
        and np.median(relative)<=cfg['median_relative_3d_error'] and min(rec['feature_span_px'])>=cfg['minimum_feature_span_px']
        and (trans[hold,2]>0).all())
    rec['accepted']=bool(passed)
    T=np.eye(4);T[:3,:3]=R;T[:3,3]=tv.ravel();rec['T_target_from_source']=T.tolist()
    return rec,T if passed else None


def fuse(frames,poses,out,cfg):
    """Voxel aggregation retains per-voxel counts of distinct observing frames."""
    pts=[];cols=[];frame_ids=[];raw_counts={}
    for i,key in enumerate(poses):
        frame=frames[key];s=cfg['point_stride'];ar=frame['xyz'][::s,::s];color=frame['image'][::s,::s]
        v=np.isfinite(ar).all(axis=2);p=ar[v];T=poses[key];p=p@T[:3,:3].T+T[:3,3]
        pts.append(p);cols.append(color[v]);frame_ids.append(np.full(len(p),i));raw_counts[key]=len(p)
    points=np.concatenate(pts);colors=np.concatenate(cols);ids=np.concatenate(frame_ids)
    voxel=next(iter(frames.values()))['baseline']*cfg['voxel_size_baselines']
    cells=np.floor(points/voxel).astype(np.int64);unique,inverse=np.unique(cells,axis=0,return_inverse=True)
    count=np.bincount(inverse);mean=np.column_stack([np.bincount(inverse,weights=points[:,j])/count for j in range(3)])
    gray=np.bincount(inverse,weights=colors)/count
    pairs=np.unique(np.column_stack([inverse,ids]),axis=0);support=np.bincount(pairs[:,0],minlength=len(unique))
    write_ply(out/'cloud_all_observed_calibration_units.ply',mean,gray)
    write_ply(out/'cloud_multiview_supported_calibration_units.ply',mean[support>=2],gray[support>=2])
    np.savez_compressed(out/'fusion.npz',points=mean,gray=gray,view_support=support)
    poses_json={k:v.tolist() for k,v in poses.items()};(out/'camera_trajectory.json').write_text(json.dumps(dict(frame='first component camera',units='CAHV source units',T_component_from_camera=poses_json),indent=2))
    with (out/'camera_trajectory.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['observation','x_cal_units','y_cal_units','z_cal_units']);[w.writerow([k,*v[:3,3]]) for k,v in poses.items()]
    summary=dict(frames=list(poses),input_points=sum(raw_counts.values()),voxel_size_calibration_units=voxel,
        fused_voxels=len(mean),multiview_supported_voxels=int((support>=2).sum()),metric_certified=False)
    (out/'metrics.json').write_text(json.dumps(summary,indent=2))
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    sub=mean[::max(1,len(mean)//40000)];axes[0].scatter(sub[:,0],sub[:,2],s=.2,c=sub[:,1],cmap='terrain')
    mp=mean[support>=2];axes[1].scatter(mp[:,0],mp[:,2],s=.3,c=gray[support>=2],cmap='gray',vmin=0,vmax=255)
    for ax,title in zip(axes,['All observed voxels','Supported by at least two frames']):
        ax.set(title=title,xlabel='X (calibration units)',ylabel='Z (calibration units)');ax.set_aspect('equal')
        for key,T in poses.items():ax.plot(T[0,3],T[2,3],'r.');ax.text(T[0,3],T[2,3],key,fontsize=6)
    fig.suptitle('Local component; source units, unknown gravity and global location');fig.tight_layout();fig.savefig(out/'fusion_views.png',dpi=150);plt.close(fig)
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',default='r08_quality_batch');p.add_argument('--run',required=True);p.add_argument('--max-observation',type=int,default=56);args=p.parse_args()
    cfg=json.loads((ROOT/'configs/registration.json').read_text());base=ROOT/'artifacts/runs'/args.batch
    out=ROOT/'artifacts/runs'/args.run;out.mkdir(parents=True,exist_ok=False)
    cv2.setNumThreads(4);frames={}
    for d in sorted(base.glob('obs_*')):
        if not (d/'metrics.json').exists() or int(d.name[-3:])>args.max_observation:continue
        prov=json.loads((d/'provenance.json').read_text())
        frames[d.name]=dict(id=d.name,image=cv2.imread(str(d/'rectified_left.png'),0),xyz=np.load(d/'xyz_rectified_calibration_units.npy'),K=np.array(prov['K']),baseline=prov['baseline_calibration_units'])
    keys=list(frames);edges=[];graph=defaultdict(list)
    candidates=set()
    for i,key in enumerate(keys):
        for other in keys[i+1:]:
            if int(other[-3:])-int(key[-3:])<=cfg['temporal_window']:candidates.add((key,other))
    # Appearance retrieval adds non-local revisits without forcing an odometry
    # chain across changes of viewpoint. ORB proposes links; it never sets poses.
    orb=cv2.ORB_create(nfeatures=1500);bf=cv2.BFMatcher(cv2.NORM_HAMMING)
    descriptors={key:orb.detectAndCompute(frames[key]['image'],None)[1] for key in keys}
    scores=defaultdict(list)
    for i,key in enumerate(keys):
        da=descriptors[key]
        if da is None:continue
        for other in keys[i+1:]:
            db=descriptors[other]
            if db is None or len(db)<2:continue
            nn=bf.knnMatch(da,db,k=2);score=sum(a.distance<.75*b.distance for a,b in nn)
            if score>=cfg['retrieval_minimum_orb_matches']:
                scores[key].append((score,other));scores[other].append((score,key))
    for key,ranked in scores.items():
        for score,other in sorted(ranked,reverse=True)[:cfg['retrieval_top_k']]:candidates.add(tuple(sorted([key,other])))
    (out/'retrieval.json').write_text(json.dumps(dict(scores=scores,candidates=sorted(candidates)),indent=2))
    print(f'Validating {len(candidates)} temporal/retrieval links among {len(frames)} frames',flush=True)
    for key,other in sorted(candidates):
        rec,T=estimate(frames[key],frames[other],cfg);edges.append(rec)
        if T is not None:
            graph[key].append((other,T,rec['heldout_median_px']));graph[other].append((key,np.linalg.inv(T),rec['heldout_median_px']))
        print(json.dumps(rec),flush=True);(out/'registration_edges.json').write_text(json.dumps(edges,indent=2))
    remaining=set(keys);components=[]
    while remaining:
        root=min(remaining);poses={root:np.eye(4)};queue=deque([root]);remaining.remove(root)
        while queue:
            key=queue.popleft()
            for other,T,err in sorted(graph[key],key=lambda e:e[2]):
                if other not in remaining:continue
                poses[other]=poses[key]@np.linalg.inv(T);remaining.remove(other);queue.append(other)
        if len(poses)<2:
            components.append(dict(frames=list(poses),status='unregistered_single_frame'));continue
        d=out/('component_'+root);d.mkdir();summary=fuse(frames,poses,d,cfg)
        # Evaluate non-tree links as a drift diagnostic, without silently merging
        # contradictory geometry or pretending this is optimized global SLAM.
        cycles=[]
        for edge in edges:
            a,b=edge['source'],edge['target']
            if not edge['accepted'] or a not in poses or b not in poses:continue
            expected=np.linalg.inv(poses[b])@poses[a];res=np.linalg.inv(np.array(edge['T_target_from_source']))@expected
            rv,_=cv2.Rodrigues(res[:3,:3]);cycles.append(dict(source=a,target=b,rotation_degrees=float(np.linalg.norm(rv)*180/np.pi),translation_calibration_units=float(np.linalg.norm(res[:3,3]))))
        (d/'cycle_consistency.json').write_text(json.dumps(cycles,indent=2));components.append(summary)
    (out/'components.json').write_text(json.dumps(components,indent=2));(out/'config.json').write_text(json.dumps(cfg,indent=2))


if __name__=='__main__':main()
