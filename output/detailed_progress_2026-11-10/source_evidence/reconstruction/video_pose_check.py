"""Check video camera motion against real endpoint stereo, never a withheld image.

This provides anchor-conditioned PnP evidence, not independently surveyed poses.
No generated depth is used and failed frames receive no interpolated pose.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from .video_bridge import read, transform
from .video_triangulate import decode
from .learned_video import digest


def match(a, b):
    ka, da = a
    kb, db = b
    if da is None or db is None or min(len(da), len(db)) < 2:
        return np.empty((0, 2)), np.empty((0, 2))
    bf = cv2.BFMatcher()
    forward = [(x.queryIdx, x.trainIdx) for x, y in bf.knnMatch(da, db, k=2) if x.distance < .75*y.distance]
    backward = {(x.trainIdx, x.queryIdx) for x, y in bf.knnMatch(db, da, k=2) if x.distance < .75*y.distance}
    pairs = [p for p in forward if p in backward]
    return (np.array([ka[i].pt for i, j in pairs], 'float32').reshape(-1, 2),
            np.array([kb[j].pt for i, j in pairs], 'float32').reshape(-1, 2))


def estimate(x, uv, K, shape):
    scale = max(shape) / 1024
    result = dict(depth_correspondences=len(x), accepted=False)
    if len(x) < 30:
        return result, None
    idx = np.random.default_rng(42).permutation(len(x))
    hold, train = idx[::5], np.delete(idx, np.arange(0, len(idx), 5))
    cv2.setRNGSeed(42)
    ok, rv, tv, inliers = cv2.solvePnPRansac(x[train], uv[train], K, None,
        iterationsCount=2000, reprojectionError=2*scale, confidence=.999, flags=cv2.SOLVEPNP_EPNP)
    if not ok or inliers is None or len(inliers) < 20:
        return result, None
    chosen = train[inliers.ravel()]
    rv, tv = cv2.solvePnPRefineLM(x[chosen], uv[chosen], K, None, rv, tv)
    projected = cv2.projectPoints(x[hold], rv, tv, K, None)[0][:, 0]
    error = np.linalg.norm(projected-uv[hold], axis=1)
    R = cv2.Rodrigues(rv)[0]
    front = (x[hold] @ R.T + tv.ravel())[:, 2] > 0
    span = np.ptp(uv[chosen], axis=0)
    passed = len(chosen)/len(train) >= .5 and np.median(error) <= 2*scale
    passed &= np.percentile(error, 90) <= 4*scale and min(span) >= 120*scale and front.all()
    result.update(accepted=bool(passed), inliers=len(chosen), heldout_features=len(hold),
                  heldout_median_px=float(np.median(error)), heldout_p90_px=float(np.percentile(error, 90)),
                  feature_span_px=span.tolist())
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = tv.ravel()
    return result, np.linalg.inv(T) if passed else None


def delta(a, b):
    return (float(np.linalg.norm(a[:3, 3]-b[:3, 3])),
            float(np.linalg.norm(cv2.Rodrigues(a[:3, :3].T @ b[:3, :3])[0])*180/np.pi))


def run(args):
    cv2.setNumThreads(4)
    manifest = json.loads((args.bundle / 'manifest.json').read_text())
    camera = np.load(args.bundle / 'commanded_trajectory.npz')
    frames = decode(args.movie)
    if len(frames) != manifest['frames'] or any(f.shape != tuple(camera['frame_shape']) for f in frames):
        raise ValueError('Video resolution/frame count differs from the bundle')
    sift = cv2.SIFT_create(nfeatures=8000, contrastThreshold=.02)
    height, width = frames[0].shape
    anchors = []
    for name, T in zip(manifest['endpoints'], camera['T_world_from_camera'][[0, -1]]):
        anchor = read(name)
        resized = cv2.resize(anchor['image'], (width, height), interpolation=cv2.INTER_AREA)
        anchors.append((name, anchor, T, sift.detectAndCompute(resized, None)))
    output, poses = [], np.full_like(camera['T_world_from_camera'], np.nan)
    for index, frame in enumerate(frames):
        feature = sift.detectAndCompute(frame, None)
        trials, accepted = [], []
        for name, anchor, T, descriptors in anchors:
            src, dst = match(descriptors, feature)
            factor = np.array([anchor['image'].shape[1]/width, anchor['image'].shape[0]/height])
            ij = np.rint((src+.5)*factor-.5).astype(int)
            ij = np.clip(ij, 0, np.array(anchor['image'].shape[::-1])-1)
            xyz = anchor['xyz'][ij[:, 1], ij[:, 0]]
            valid = np.isfinite(xyz).all(1)
            result, pose = estimate(transform(xyz[valid], T).astype('float64'), dst[valid].astype('float64'), camera['K'], frame.shape)
            result.update(anchor=name, mutual_matches=len(src)); trials.append(result)
            if pose is not None:
                accepted.append((result['heldout_median_px'], pose))
        row = dict(frame=index, conditioned=index in manifest['conditioned_frame_indices'], anchors=trials, accepted=False)
        if len(accepted) == 2:
            shift, angle = delta(accepted[0][1], accepted[1][1])
            row['cross_anchor_translation_m'], row['cross_anchor_rotation_deg'] = shift, angle
            if shift > .10 or angle > 2:
                accepted = []
                row['rejection'] = 'Endpoint anchors disagree by >10 cm or >2 degrees'
        if accepted:
            chosen = min(accepted, key=lambda pair: pair[0])[1]
            poses[index] = chosen
            shift, angle = delta(chosen, camera['T_world_from_camera'][index])
            row.update(accepted=True, command_translation_difference_m=shift, command_rotation_difference_deg=angle)
        output.append(row)
    valid = np.isfinite(poses).all((1, 2))
    unconditioned = [r for r in output if not r['conditioned']]
    summary = dict(frames=len(frames), accepted_frames=int(valid.sum()),
                   movie_sha256=digest(args.movie), bundle_sha256=digest(args.bundle / 'manifest.json'),
                   unconditioned_frames=len(unconditioned), accepted_unconditioned_frames=sum(r['accepted'] for r in unconditioned),
                   status='anchor-conditioned pose diagnostic; not surveyed validation',
                   limitations=['Single-anchor PnP lacks independent target depth checks.',
                                'Endpoint relative placement and camera intrinsics are assumed.',
                                'Conditioned frame matches do not show learned geometric recovery.',
                                'Rejected frames have NaN poses; no trajectory is silently interpolated.'], frames_detail=output)
    args.out.mkdir(parents=True, exist_ok=False)
    np.savez(args.out / 'anchor_poses.npz', T_world_from_camera=poses, valid=valid, K=camera['K'], frame_shape=frames[0].shape)
    (args.out / 'metrics.json').write_text(json.dumps(summary, indent=2, allow_nan=False))
    print(json.dumps({k: v for k, v in summary.items() if k != 'frames_detail'}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', required=True, type=Path)
    p.add_argument('--movie', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    run(p.parse_args())
