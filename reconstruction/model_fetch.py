"""Resumable range downloads of pinned public Hugging Face safetensors models.

Use when large ordinary/Xet transfers time out. Every completed LFS file is
SHA256 checked against the model provider's metadata before being published.
Partial files and chunk progress survive an interrupted run. No model code runs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import threading
import time
import urllib.parse
import urllib.request


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def fetch(args):
    if not re.fullmatch('[0-9a-f]{40}', args.revision):
        raise ValueError('Pin an exact 40-character model commit')
    api = f'https://huggingface.co/api/models/{args.model}/revision/{args.revision}?blobs=true'
    with urllib.request.urlopen(api, timeout=30) as response:
        metadata = json.load(response)
    if metadata['sha'] != args.revision:
        raise ValueError('Unexpected resolved model revision')
    args.out.mkdir(parents=True, exist_ok=True)
    chunk_size = 16 * 1024 * 1024
    tasks, states, hashes = [], {}, {}
    lock = threading.Lock()
    for info in metadata['siblings']:
        name = info['rfilename']
        if name != 'model_index.json' and name.split('/')[0] not in args.parts:
            continue
        if not name.endswith(('.json', '.safetensors', '.model', '.txt')):
            continue
        path = (args.out / name).resolve()
        if not path.is_relative_to(args.out.resolve()):
            raise ValueError('Unsafe model filename')
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://huggingface.co/{args.model}/resolve/{args.revision}/{urllib.parse.quote(name)}?download=true'
        lfs = info.get('lfs')
        if not lfs:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            # Git blob identity verifies ordinary repository config/tokenizer files.
            blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if blob != info['blobId']:
                raise ValueError(f'Git blob checksum mismatch: {name}')
            path.write_bytes(data)
            hashes[name] = sha(path)
            continue
        expected, size = lfs['sha256'], lfs['size']
        hashes[name] = expected
        if path.exists() and path.stat().st_size == size and sha(path) == expected:
            print('Already verified', name, flush=True)
            continue
        partial, progress = path.with_suffix(path.suffix+'.partial'), path.with_suffix(path.suffix+'.progress.json')
        done = set()
        if partial.exists() and progress.exists():
            previous = json.loads(progress.read_text())
            if previous.get('sha256') == expected and previous.get('size') == size and partial.stat().st_size == size:
                done = set(previous['done'])
            else:
                raise ValueError(f'Partial file belongs to a different checkpoint: {name}')
        else:
            with partial.open('wb') as f:
                f.truncate(size)
        state = dict(path=path, partial=partial, progress=progress, done=done, size=size, expected=expected)
        states[name] = state
        for start in range(0, size, chunk_size):
            if start not in done:
                tasks.append((name, url, start, min(size, start+chunk_size)-1))

    def one(task):
        name, url, start, end = task
        for attempt in range(4):
            try:
                request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
                with urllib.request.urlopen(request, timeout=45) as response:
                    expected_range = f'bytes {start}-{end}/{states[name]["size"]}'
                    if response.status != 206 or response.headers.get('Content-Range') != expected_range:
                        raise ValueError(f'Unexpected range response: {name} at {start}')
                    data = response.read(end-start+2)
                if len(data) != end-start+1:
                    raise ValueError(f'Incomplete range: {name} at {start}')
                state = states[name]
                # Each worker owns a file handle, so seek positions cannot race.
                with state['partial'].open('r+b') as f:
                    f.seek(start); f.write(data); f.flush()
                with lock:
                    state['done'].add(start)
                    state['progress'].write_text(json.dumps(dict(sha256=state['expected'], size=state['size'], done=sorted(state['done']))))
                return len(data)
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)

    total, complete, started = sum(end-start+1 for _, _, start, end in tasks), 0, time.monotonic()
    print(f'Downloading {total/1e9:.2f} GB in {len(tasks)} resumable ranges', flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        jobs = [executor.submit(one, task) for task in tasks]
        for i, future in enumerate(as_completed(jobs)):
            complete += future.result()
            if i % 8 == 0 or i == len(jobs)-1:
                print(f'{complete/1e9:.2f}/{total/1e9:.2f} GB; {complete/1e6/max(1,time.monotonic()-started):.2f} MB/s', flush=True)
    for name, state in states.items():
        if sha(state['partial']) != state['expected']:
            raise ValueError(f'SHA256 mismatch: {name}; retained partial file for inspection')
        state['partial'].replace(state['path'])
        state['progress'].unlink(missing_ok=True)
        print('Verified', name, flush=True)
    (args.out / 'download_manifest.json').write_text(json.dumps(dict(model=args.model, revision=args.revision, files=hashes), indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', default='Wan-AI/Wan2.1-VACE-1.3B-diffusers')
    p.add_argument('--revision', required=True)
    p.add_argument('--parts', nargs='+', required=True)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--workers', type=int, default=6)
    fetch(p.parse_args())
