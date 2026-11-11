"""Read-only audit of saved experiments; writes only this review directory."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

import numpy as np
from PIL import Image
from scipy.interpolate import LinearNDInterpolator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reconstruction.close_terrain import read_obj, validate

BASE = ROOT / 'output/chronological_video'
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def main():
    sources = list((ROOT / 'reconstruction').glob('video_*.py')) + [
        ROOT / 'reconstruction/evaluate_video.py', ROOT / 'reconstruction/learned_video.py']
    before = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    report = dict(review_date='2026-11-09', scope='Local saved procedural results; no Jarvis access or learned inference',
                  source_sha256=before, bundles={}, integrated={}, external_control={})
    for name in ['holdout046_endpoints_v2', 'holdout046_pose_anchors_v2', 'smoke256_pose_anchors_v2']:
        folder = BASE / 'learned_inputs' / name
        m = json.loads((folder / 'manifest.json').read_text())
        assert m['schema'] == 2
        for file, expected in m['files'].items():
            assert sha(folder / file) == expected, (name, file)
        generated_pixels = 0
        actual_conditioned = []
        for i in range(m['frames']):
            pixels = np.array(Image.open(folder / 'frames' / f'{i:04d}.png'))
            mask = np.array(Image.open(folder / 'masks' / f'{i:04d}.png'))
            assert np.isin(mask, [0, 255]).all()
            assert (pixels[mask == 255] == 128).all()
            generated_pixels += int((mask == 255).sum())
            if (mask == 0).any():
                actual_conditioned.append(i)
        assert actual_conditioned == m['conditioned_frame_indices']
        report['bundles'][name] = dict(all_file_hashes_verified=True,
            neutral_generation_pixels=generated_pixels, conditioned_indices=actual_conditioned,
            unconditioned_frames=m['frames'] - len(actual_conditioned), manifest_sha256=sha(folder / 'manifest.json'))

    for prefix, model in [('holdout046', 'holdout046_model'), ('mid036', 'mid036_model')]:
        folder = BASE / model
        grid = np.load(folder / 'integrated_grid.npz')
        s = np.load(BASE / f'{prefix}_7/surfaces.npz')
        measured = np.isfinite(s['stereo_m'])
        assert np.array_equal(grid['height_m'][measured], s['stereo_m'][measured])
        assert (grid['labels'][measured] == 1).all()
        m = json.loads((folder / 'metrics.json').read_text())
        counts = {str(i): int((grid['labels'] == i).sum()) for i in range(1, 5)}
        assert counts == m['cell_counts']
        inside = np.isfinite(s['baseline_idw_m'])
        gap = inside & ~grid['endpoint_A_footprint'] & ~grid['endpoint_B_footprint']
        video = grid['labels'] == 3
        assert int((gap & video).sum()) == m['between_footprints_video_cells']
        top_v, top_f = read_obj(folder / 'terrain_top_m.obj')
        closed_v, closed_f = read_obj(folder / 'closed/terrain_closed_m.obj')
        assert np.array_equal(top_v, closed_v[:len(top_v)])
        assert np.array_equal(top_f, closed_f[:len(top_f)])
        closure = validate(closed_v, closed_f)
        # Additional independent edge-count computation on the actual disk mesh.
        edges = np.sort(np.concatenate([closed_f[:, [0, 1]], closed_f[:, [1, 2]], closed_f[:, [2, 0]]]), axis=1)
        _, edge_counts = np.unique(edges, axis=0, return_counts=True)
        assert (edge_counts == 2).all()
        record = dict(strict_cells_unchanged=int(measured.sum()), counts=counts,
            between_footprints_video_cells=int((gap & video).sum()),
            between_footprints_video_area_m2=float((gap & video).sum() * .05 ** 2),
            between_footprints_total_cells=int(gap.sum()), top_geometry_preserved_in_closed_obj=True,
            closed_obj_validation=closure, closed_obj_sha256=sha(folder / 'closed/terrain_closed_m.obj'))
        if prefix == 'holdout046':
            ref = np.load(BASE / f'{prefix}_7/validation.npz')['heldout_m']
            observed = np.isin(grid['labels'], [1, 2])
            linear = LinearNDInterpolator(grid['xy_m'][observed], grid['height_m'][observed])(grid['xy_m'])
            common = np.isfinite(ref) & video
            values = dict(video=rmse(grid['height_m'][common], ref[common]),
                          linear=rmse(linear[common], ref[common]),
                          idw=rmse(s['baseline_idw_m'][common], ref[common]))
            for key, field in [('video', 'consensus_video_m'), ('linear', 'same_cell_linear_m'), ('idw', 'same_cell_idw_m')]:
                assert np.isclose(values[key], m['holdout'][field]['rmse'], atol=1e-12)
            record['heldout'] = dict(scored_cells=int(common.sum()), eligible_cells=int((np.isfinite(ref) & inside & ~observed).sum()), rmse_m=values)
        report['integrated'][model] = record

    folder = BASE / 'baseline_unconditioned_eval'
    m = json.loads((folder / 'metrics.json').read_text())
    s = np.load(folder / 'surfaces.npz')
    ref = np.load(folder / 'validation.npz')['heldout_m']
    measured = np.isfinite(s['stereo_m'])
    assert np.array_equal(s['merged_m'][measured], s['stereo_m'][measured])
    xy = np.stack(np.meshgrid(s['x'], s['y'], indexing='ij'), -1)
    linear = LinearNDInterpolator(xy[measured], s['stereo_m'][measured])(xy)
    common = np.isfinite(ref) & (s['labels'] == 3)
    eligible = np.isfinite(ref) & np.isfinite(s['baseline_idw_m']) & ~measured
    raw = eligible & np.isfinite(s['video_m'])
    values = dict(video=rmse(s['merged_m'][common], ref[common]), idw=rmse(s['baseline_idw_m'][common], ref[common]),
                  linear=rmse(linear[common], ref[common]), raw_before_envelope=rmse(s['video_m'][raw], ref[raw]))
    for key, field in [('video', 'video_abs_height_error_m'), ('idw', 'matched_idw_abs_height_error_m'),
                       ('linear', 'matched_linear_abs_height_error_m'), ('raw_before_envelope', 'raw_before_envelope_m')]:
        assert np.isclose(values[key], m['validation'][field]['rmse'], atol=1e-12)
    trajectory = np.load(folder / 'reconstructed_trajectory.npz')
    assert trajectory['original_frame_indices'].tolist() == m['used_frame_indices']
    assert not set(m['used_frame_indices']) & set(range(0, 33, 4))
    packaged_check = BASE / 'baseline_pose_check/metrics.json'
    bound_dir = ROOT / 'tmp/baseline_pose_check_hashed'
    if not bound_dir.exists():
        bound_dir = OUT / 'evidence/baseline_pose_check_hashed'
    check = json.loads((bound_dir / 'metrics.json').read_text())
    assert sha(bound_dir / 'metrics.json') == m['pose_check_sha256']
    assert check['movie_sha256'] == m['input_movie_sha256']
    assert check['bundle_sha256'] == m['bundle_sha256']
    bound_poses = np.load(bound_dir / 'anchor_poses.npz')
    assert np.array_equal(bound_poses['T_world_from_camera'][m['used_frame_indices']], trajectory['T_world_from_camera'])
    preserved = OUT / 'evidence/baseline_pose_check_hashed'
    preserved.mkdir(parents=True, exist_ok=True)
    for file in ['metrics.json', 'anchor_poses.npz']:
        if (bound_dir / file).resolve() != (preserved / file).resolve():
            shutil.copyfile(bound_dir / file, preserved / file)
    report['external_control'] = dict(scored_cells=int(common.sum()), eligible_cells=int(eligible.sum()),
        raw_before_envelope_cells=int(raw.sum()), rmse_m=values, strict_cells_unchanged=int(measured.sum()),
        used_unconditioned_frames=len(m['used_frame_indices']),
        packaged_pose_check_matches_recorded_hash=sha(packaged_check) == m['pose_check_sha256'],
        matching_pose_check_preserved_at=str(preserved.relative_to(ROOT)),
        caveat='Existing control predates v2 bundles; its pose-check manifest hash is not valid for a new v2 experiment.')
    assert before == {str(p.relative_to(ROOT)): sha(p) for p in sources}, 'Source changed during audit; rerun against fixed revision'
    report['status'] = 'Numerical, mesh and bundle checks passed; missing packaged pose evidence recovered from tmp. See REVIEW.md for design issues.'
    (OUT / 'audit_results.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({k: report[k] for k in ['status', 'external_control']}, indent=2))


if __name__ == '__main__':
    main()
