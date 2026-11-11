"""Reconstruct unconditioned video frames using real-anchor PnP poses.

Runs after generation and pose checking. Uses no generator depth. Optional
withheld stereo is accessed only after reconstruction and filtering finish.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.interpolate import LinearNDInterpolator

from .video_bridge import bins, summary, DX
from .complete_terrain import export_mesh
from .learned_video import digest
from .video_triangulate import decode, tracks, sweep


def run(args):
    cv2.setNumThreads(4)
    source = json.loads((args.source / 'metrics.json').read_text())
    manifest = json.loads((args.bundle / 'manifest.json').read_text())
    if manifest['endpoints'] != source['endpoints'] or manifest['source_hashes']['metrics.json'] != digest(args.source / 'metrics.json'):
        raise ValueError('Bundle belongs to a different source experiment')
    check = np.load(args.pose_check / 'anchor_poses.npz')
    details = json.loads((args.pose_check / 'metrics.json').read_text())
    # Pose files must be bound to the exact movie to prevent accidentally using
    # a baseline trajectory check to certify an unrelated learned output.
    if details.get('movie_sha256') != digest(args.movie) or details.get('bundle_sha256') != digest(args.bundle / 'manifest.json'):
        raise ValueError('Pose check does not bind to this movie and bundle; rerun video_pose_check')
    frames = decode(args.movie)
    if len(frames) != manifest['frames'] or any(f.shape != tuple(check['frame_shape']) for f in frames):
        raise ValueError('Video dimensions differ from the pose check')
    selected = check['valid'].copy()
    selected[manifest['conditioned_frame_indices']] = False
    chosen = np.flatnonzero(selected)
    if len(chosen) < 8:
        raise ValueError(f'Only {len(chosen)} unconditioned frames have accepted anchor poses; at least eight needed')
    images = [frames[i] for i in chosen]
    poses, K = check['T_world_from_camera'][chosen], check['K']
    points, errors, windows = tracks(images, poses, K)
    s = np.load(args.source / 'surfaces.npz')
    xy = np.stack(np.meshgrid(s['x'], s['y'], indexing='ij'), -1)
    measured = np.isfinite(s['stereo_m'])
    inside = np.isfinite(s['baseline_idw_m'])
    raw, counts = bins(points, xy)
    raw[(counts < 2) | ~inside] = np.nan
    bounds = np.percentile(s['stereo_m'][measured], [.1, 99.9]) + [-.4, .4]
    dense = sweep(images, poses, K, xy, bounds)
    dense[~inside] = np.nan
    disagreement = np.isfinite(dense) & np.isfinite(raw) & (abs(dense-raw) > .10)
    raw = np.where(np.isfinite(dense), dense, raw)
    raw[disagreement] = np.nan
    gated = np.where(abs(raw-s['baseline_idw_m']) <= .20, raw, np.nan)
    add = ~measured & inside & np.isfinite(gated)
    merged = np.where(measured, s['stereo_m'], np.where(add, gated, np.nan))
    labels = np.where(measured, 1, np.where(add, 3, 0)).astype('uint8')
    np.testing.assert_array_equal(merged[measured], s['stereo_m'][measured])
    args.out.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(args.out / 'triangulated.npz', xyz_m=points, reprojection_px=errors)
    np.savez_compressed(args.out / 'reconstructed_trajectory.npz', T_world_from_camera=poses,
                        original_frame_indices=chosen, K=K, frame_shape=check['frame_shape'])
    anchors = np.load(args.bundle / 'commanded_trajectory.npz')['T_world_from_camera'][[0, -1]]
    np.savez(args.out / 'anchor_trajectory.npz', T_world_from_camera=anchors,
             role='Real endpoint coordinate anchors; actual intermediate poses are in reconstructed_trajectory.npz')
    np.savez_compressed(args.out / 'surfaces.npz', x=s['x'], y=s['y'], stereo_m=s['stereo_m'],
                        baseline_idw_m=s['baseline_idw_m'], video_m=raw, merged_m=merged, labels=labels)
    mesh = export_mesh(args.out / 'candidate_stereo_plus_video_m.obj', merged, xy, labels)
    record = dict(endpoints=source['endpoints'], pose=source['pose'], seed=args.seed,
                  generator=args.kind, input_movie_sha256=digest(args.movie), bundle_sha256=digest(args.bundle / 'manifest.json'),
                  pose_check_sha256=digest(args.pose_check / 'metrics.json'), grid_m=DX,
                  reconstruction='real-anchor PnP; unconditioned accepted frames only', used_frame_indices=chosen.tolist(),
                  video_tracks=len(points), triangulation_windows=windows, reprojection_px=summary(errors),
                  stereo_cells=int(measured.sum()), new_video_cells=int(add.sum()),
                  new_cell_area_m2=float(add.sum()*DX**2), mesh=mesh,
                  status='experimental synthetic terrain; not independently surveyed')
    # Evaluation-only data is first accessed after geometry has been finalized.
    if (args.source / 'validation.npz').exists():
        reference = np.load(args.source / 'validation.npz')['heldout_m']
        eligible = np.isfinite(reference) & inside & ~measured
        common = eligible & add
        linear = LinearNDInterpolator(xy[measured], s['stereo_m'][measured])(xy)
        same_linear = common & np.isfinite(linear)
        record['validation'] = dict(holdout=source['validation']['holdout'],
            reference='withheld registered stereo; not survey ground truth', measurable_gap_cells=int(eligible.sum()),
            tested_added_cells=int(common.sum()), reference_coverage=float(common.sum()/max(1, eligible.sum())),
            video_abs_height_error_m=summary(abs(gated[common]-reference[common])),
            matched_idw_abs_height_error_m=summary(abs(s['baseline_idw_m'][common]-reference[common])),
            linear_comparison_cells=int(same_linear.sum()),
            matched_linear_abs_height_error_m=summary(abs(linear[same_linear]-reference[same_linear])),
            video_on_linear_comparison_m=summary(abs(gated[same_linear]-reference[same_linear])),
            raw_before_envelope_m=summary(abs(raw[eligible & np.isfinite(raw)]-reference[eligible & np.isfinite(raw)])))
        np.savez_compressed(args.out / 'validation.npz', heldout_m=reference, scored_cells=common)
    (args.out / 'metrics.json').write_text(json.dumps(record, indent=2, allow_nan=False))
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'bundle', 'pose-check', 'movie', 'out']:
        p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--kind', required=True, choices=['procedural_control', 'learned'])
    p.add_argument('--seed', required=True, type=int)
    run(p.parse_args())
