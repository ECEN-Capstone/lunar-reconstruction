"""Probe unchanged video validation with explicitly invalid frozen/crossfade clips."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import cv2
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
    source = base/'holdout046_7'
    bundle = base/'learned_inputs/holdout046_endpoints_v2'
    manifest = json.loads((bundle/'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        file = (bundle/name).resolve()
        if not file.is_relative_to(bundle.resolve()) or sha(file) != expected:
            raise ValueError(f'Invalid bundle payload: {name}')
    first, last = [cv2.imread(str(bundle/'frames'/f'{i:04d}.png')) for i in [0, manifest['frames']-1]]
    if first is None or last is None:
        raise ValueError('Cannot read real endpoint images')
    paths = list((ROOT/'reconstruction').glob('*.py')) + list(bundle.rglob('*.npz')) + [bundle/'manifest.json',
        source/'metrics.json', source/'surfaces.npz', source/'validation.npz']
    hashes = {str(path.relative_to(ROOT)):sha(path) for path in paths}
    out.mkdir(parents=True, exist_ok=False)
    report = dict(status='running', kind='Explicit negative controls; not learned generation',
        source_sha256=hashes, reviewer_sha256=sha(Path(__file__)), runs={})
    def save():
        (out/'negative_control_review.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    save()
    for name in ['frozen_first_endpoint', 'linear_endpoint_crossfade']:
        folder = out/name
        folder.mkdir()
        movie = folder/'negative_control.mp4'
        writer = cv2.VideoWriter(str(movie), cv2.VideoWriter_fourcc(*'mp4v'), manifest['fps'], first.shape[1::-1])
        if not writer.isOpened():
            raise RuntimeError('Cannot open negative-control video encoder')
        for t in np.linspace(0, 1, manifest['frames']):
            frame = first if name.startswith('frozen') else cv2.addWeighted(first, 1-float(t), last, float(t), 0)
            writer.write(frame)
        writer.release()
        rec = dict(movie_sha256=sha(movie), commands=[],
            construction='First real endpoint repeated' if name.startswith('frozen') else 'Pixelwise linear blend of real endpoints; no 3D rendering',
            expected_interpretation='No physical translation in frozen clip; crossfade is not a rigid-scene camera traversal')
        report['runs'][name] = rec
        commands = [
            [sys.executable, '-m', 'reconstruction.video_pose_check', '--bundle', str(bundle),
             '--movie', str(movie), '--out', str(folder/'pose_check')],
            [sys.executable, '-m', 'reconstruction.evaluate_video', '--source', str(source), '--bundle', str(bundle),
             '--pose-check', str(folder/'pose_check'), '--movie', str(movie), '--kind', 'procedural_control',
             '--seed', '7', '--out', str(folder/'evaluation')]]
        for i, cmd in enumerate(commands):
            print(f'{name}: starting {cmd[2]}', flush=True)
            start = time.monotonic()
            with (folder/f'stage_{i}.log').open('w', encoding='utf-8') as log:
                result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            rec['commands'].append(dict(argv=cmd, exit_code=result.returncode, seconds=time.monotonic()-start))
            save()
            if result.returncode:
                rec['pipeline_stopped_at'] = cmd[2]
                rec['failure_log_tail'] = (folder/f'stage_{i}.log').read_text()[-1500:]
                break
        checkfile = folder/'pose_check/metrics.json'
        if checkfile.exists():
            check = json.loads(checkfile.read_text())
            rec.update(accepted_frames=check['accepted_frames'], accepted_unconditioned_frames=check['accepted_unconditioned_frames'],
                       total_unconditioned_frames=check['unconditioned_frames'], pose_check_sha256=sha(checkfile),
                       pose_array_sha256=sha(folder/'pose_check/anchor_poses.npz'))
            poses = np.load(folder/'pose_check/anchor_poses.npz')
            xyz = poses['T_world_from_camera'][poses['valid'], :3, 3]
            rec['accepted_pose_extent_m'] = np.ptp(xyz, axis=0).tolist() if len(xyz) else None
            rec['accepted_pose_path_length_m'] = float(np.linalg.norm(np.diff(xyz, axis=0), axis=1).sum())
        metricsfile = folder/'evaluation/metrics.json'
        if metricsfile.exists():
            metrics = json.loads(metricsfile.read_text())
            rec.update(new_video_cells=metrics['new_video_cells'], validation=metrics.get('validation'),
                       evaluation_sha256=sha(metricsfile), outcome='Evaluator produced candidate; inspect coverage and errors before acceptance')
        save()
        print(f'{name}: accepted {rec.get("accepted_unconditioned_frames")} unconditioned poses; new cells {rec.get("new_video_cells")}', flush=True)
    if any(sha(ROOT/path) != expected for path,expected in hashes.items()):
        report['status'] = 'invalidated by changed source/evidence during review'
        save()
        raise RuntimeError(report['status'])
    report['status'] = 'completed diagnostic; see per-control outcomes, not an accuracy certification'
    save()


if __name__ == '__main__':
    main()
