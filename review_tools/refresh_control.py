"""Rerun the saved 480px procedural control against schema-2 inputs for review.

Uses existing pipeline modules unchanged. No inference or Jarvis operations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    out = args.out.resolve()
    base = ROOT/'output/chronological_video'
    bundle = base/'learned_inputs/holdout046_pose_anchors_v2'
    source = base/'holdout046_7'
    previous = base/'baseline_unconditioned_eval'
    movie = ROOT/'tmp/baseline480.mp4'
    old = json.loads((previous/'metrics.json').read_text())
    if sha(movie) != old['input_movie_sha256']:
        raise ValueError('Control movie does not match the historical evaluation')
    manifest = json.loads((bundle/'manifest.json').read_text())
    if manifest['schema'] != 2:
        raise ValueError('Expected corrected schema-2 input bundle')
    for name, expected in manifest['files'].items():
        path = (bundle/name).resolve()
        if not path.is_relative_to(bundle.resolve()) or sha(path) != expected:
            raise ValueError(f'Bundle payload mismatch: {name}')
    for name, expected in manifest['source_hashes'].items():
        if sha(source/name) != expected:
            raise ValueError(f'Bundle source mismatch: {name}')
    paths = list((ROOT/'reconstruction').glob('*.py')) + [bundle/'manifest.json', source/'surfaces.npz', source/'validation.npz']
    for endpoint in manifest['endpoints']:
        paths += [ROOT/'artifacts/runs/r11_filtered_batch'/endpoint/f for f in
                  ['provenance.json', 'rectified_left.png', 'xyz_rectified_calibration_units.npy']]
    fingerprints = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(movie, out/'control480.mp4')
    record = dict(kind='procedural control, not learned video', status='running',
                  input_sha256=fingerprints, movie_sha256=sha(out/'control480.mp4'),
                  runner_sha256=sha(Path(__file__)), commands=[])
    def save():
        (out/'review_run.json').write_text(json.dumps(record, indent=2, allow_nan=False))
    save()
    commands = [
        [sys.executable, '-m', 'reconstruction.video_pose_check', '--bundle', str(bundle),
         '--movie', str(out/'control480.mp4'), '--out', str(out/'pose_check')],
        [sys.executable, '-m', 'reconstruction.evaluate_video', '--source', str(source),
         '--bundle', str(bundle), '--pose-check', str(out/'pose_check'), '--movie', str(out/'control480.mp4'),
         '--kind', 'procedural_control', '--seed', '7', '--out', str(out/'evaluation')]]
    for i, command in enumerate(commands):
        start = time.monotonic()
        print(f'Starting {command[2]}', flush=True)
        with (out/f'stage_{i}.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        record['commands'].append(dict(argv=command, exit_code=result.returncode, seconds=time.monotonic()-start))
        if result.returncode:
            record['status'] = 'failed; inspect stage log'
            save()
            raise RuntimeError(f'{command[2]} exited {result.returncode}')
        save()
        print(f'Finished {command[2]} in {time.monotonic()-start:.1f}s', flush=True)
    if any(sha(ROOT/path) != expected for path, expected in fingerprints.items()):
        record['status'] = 'invalidated: evidence or source changed during run'
        save()
        raise RuntimeError(record['status'])
    equality = {}
    for file in ['surfaces.npz', 'reconstructed_trajectory.npz', 'validation.npz']:
        with np.load(previous/file, allow_pickle=False) as a, np.load(out/'evaluation'/file, allow_pickle=False) as b:
            equality[file] = set(a.files) == set(b.files) and all(np.array_equal(a[k], b[k], equal_nan=True) for k in a.files)
    poses = json.loads((out/'pose_check/metrics.json').read_text())
    metrics = json.loads((out/'evaluation/metrics.json').read_text())
    record.update(status='completed', historical_arrays_exactly_reproduced=equality,
                  pose_check_sha256=sha(out/'pose_check/metrics.json'),
                  pose_array_sha256=sha(out/'pose_check/anchor_poses.npz'),
                  evaluation_sha256=sha(out/'evaluation/metrics.json'),
                  accepted_frames=poses['accepted_frames'], accepted_unconditioned_frames=poses['accepted_unconditioned_frames'],
                  validation=metrics['validation'])
    save()
    print(json.dumps({k:record[k] for k in ['status', 'historical_arrays_exactly_reproduced', 'accepted_frames', 'accepted_unconditioned_frames']}, indent=2))


if __name__ == '__main__':
    main()
