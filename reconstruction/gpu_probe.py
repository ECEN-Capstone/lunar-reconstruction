"""Read-only hardware report. Copy this file to the Jetson; run python3 gpu_probe.py."""
import importlib.metadata
import json
import platform
import shutil
import subprocess
from pathlib import Path


def report():
    result = {'system': platform.system(), 'machine': platform.machine(),
              'python': platform.python_version()}
    for name, path in [('device', '/proc/device-tree/model'),
                       ('l4t_release', '/etc/nv_tegra_release'),
                       ('memory', '/proc/meminfo')]:
        p = Path(path)
        if p.exists():
            value = p.read_text(errors='replace').replace('\x00', '').strip()
            if name == 'memory':
                value = '\n'.join(line for line in value.splitlines()
                                  if line.split(':')[0] in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'))
            result[name] = value
    if shutil.which('dpkg-query'):
        query = subprocess.run(['dpkg-query', '-W', '-f=${Version}', 'nvidia-jetpack'],
                               capture_output=True, text=True, timeout=10)
        result['jetpack_package'] = query.stdout.strip() or 'metapackage not installed; use L4T release'
    result['packages'] = {}
    for name in ['torch', 'diffusers', 'transformers', 'accelerate', 'safetensors']:
        try:
            result['packages'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result['packages'][name] = None
    if result['packages']['torch']:
        code = '''import torch,json
r={'torch':torch.__version__,'cuda_build':torch.version.cuda,'cuda_available':torch.cuda.is_available()}
if r['cuda_available']:
 r.update(device=torch.cuda.get_device_name(), capability=torch.cuda.get_device_capability(), compiled_arches=torch.cuda.get_arch_list(), free_total_bytes=torch.cuda.mem_get_info(), bf16=torch.cuda.is_bf16_supported())
print(json.dumps(r))'''
        try:
            p = subprocess.run([__import__('sys').executable, '-c', code], capture_output=True,
                               text=True, timeout=45)
            result['torch_probe'] = json.loads(p.stdout) if p.returncode == 0 else p.stderr[-2000:]
        except (subprocess.TimeoutExpired, ValueError) as exc:
            result['torch_probe'] = str(exc)
    result['note'] = 'Read-only diagnostic; no packages installed, models downloaded, or settings changed.'
    return result


if __name__ == '__main__':
    print(json.dumps(report(), indent=2))
