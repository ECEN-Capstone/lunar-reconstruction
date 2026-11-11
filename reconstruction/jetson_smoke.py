"""Finish a queued Jetson setup and attempt one explicitly labelled smoke run.

Uses an existing environment/model download. Does not install software, change
system settings or treat a successful video as validated terrain.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--install-pid', type=int, required=True)
    p.add_argument('--download-pid', type=int, required=True)
    p.add_argument('--job-name', default='smoke256_seed7')
    args = p.parse_args()
    root = args.root.resolve()
    status_file = root / (args.job_name + '_status.json')
    if status_file.exists():
        raise FileExistsError(status_file)
    started = time.monotonic()
    state = dict(job=args.job_name, started_utc=datetime.now(timezone.utc).isoformat(),
                 interpretation='Memory/runtime feasibility only; not a terrain validation experiment')
    def status(phase, **fields):
        state.update(phase=phase, elapsed_seconds=round(time.monotonic()-started), **fields)
        status_file.write_text(json.dumps(state, indent=2))
        print(phase, flush=True)
    def running(pid, token):
        try:
            return token in Path(f'/proc/{pid}/cmdline').read_text().replace('\0', ' ')
        except FileNotFoundError:
            return False
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['HF_HOME'] = str(root / 'cache')
    python = root / '.venv-orin/bin/python'
    # The Jetson wheel expects CUDA in system paths; keep our CUDA libraries
    # isolated in this venv instead of installing/replacing system CUDA.
    library_root = root / '.venv-orin/lib/python3.12/site-packages/nvidia'
    libraries = [str(p) for p in library_root.glob('*/lib')]
    if env.get('LD_LIBRARY_PATH'):
        libraries.append(env['LD_LIBRARY_PATH'])
    env['LD_LIBRARY_PATH'] = ':'.join(libraries)
    try:
        status('waiting_for_runtime_install')
        while running(args.install_pid, 'pip install'):
            if time.monotonic()-started > 7200:
                raise TimeoutError('Runtime setup exceeded two hours')
            time.sleep(10)
        status('checking_orin_gpu_kernels')
        probe = '''import json,torch
import torch.nn.functional as F
assert torch.cuda.is_available(), 'CUDA unavailable'
arches=torch.cuda.get_arch_list()
assert 'sm_87' in arches, f'Orin target missing: {arches}'
r={'torch':torch.__version__,'cuda':torch.version.cuda,'arches':arches,'device':torch.cuda.get_device_name()}
with torch.inference_mode():
 for dtype in [torch.float32,torch.bfloat16]:
  a=torch.randn(128,128,device='cuda',dtype=dtype)
  assert torch.isfinite(a@a).all()
  q=torch.randn(1,4,64,32,device='cuda',dtype=dtype)
  assert torch.isfinite(F.scaled_dot_product_attention(q,q,q)).all()
  im=torch.randn(1,4,3,16,16,device='cuda',dtype=dtype)
  w=torch.randn(4,4,3,3,3,device='cuda',dtype=dtype)
  assert torch.isfinite(F.conv3d(im,w,padding=1)).all()
torch.cuda.synchronize()
r['math_checks']='matmul, attention, conv3d: float32 and bfloat16 passed'
r['free_total_bytes']=torch.cuda.mem_get_info()
print(json.dumps(r))'''
        result = subprocess.run([str(python), '-c', probe], env=env, cwd=root,
                                capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise RuntimeError('GPU probe failed: '+result.stderr[-4000:])
        gpu = json.loads(result.stdout.strip().splitlines()[-1])
        (root / (args.job_name+'_gpu.json')).write_text(json.dumps(gpu, indent=2))
        status('waiting_for_verified_video_model', gpu=gpu)
        model = root / 'models/wan-vace-1.3b'
        while not (model / 'download_manifest.json').exists():
            if not running(args.download_pid, 'reconstruction.model_fetch'):
                raise RuntimeError('Video downloader ended without a verified manifest; inspect model-download.log')
            if time.monotonic()-started > 7200:
                raise TimeoutError('Model preparation exceeded two hours')
            time.sleep(15)
        status('running_four_step_smoke_inference')
        command = [str(python), '-u', '-m', 'reconstruction.learned_video', 'run',
                   '--bundle', 'output/chronological_video/learned_inputs/smoke256_pose_anchors_v2',
                   '--out', 'output/chronological_video/'+args.job_name,
                   '--revision', 'ec4d2cb062b548996b179d493fdd05340de702a1',
                   '--local-model', str(model), '--local-files-only',
                   '--prompt-embeds', 'output/chronological_video/learned_inputs/lunar_prompt.safetensors',
                   '--steps', '4', '--seed', '7', '--offload', 'sequential']
        subprocess.run(command, env=env, cwd=root, check=True, timeout=7200)
        status('smoke_video_created_not_validated')
    except Exception as exc:
        status('failed', error=str(exc))
        raise


if __name__ == '__main__':
    main()
