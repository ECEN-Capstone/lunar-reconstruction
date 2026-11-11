"""Portable VACE input preparation and optional GPU inference (not yet GPU validated).

Prepare needs only the ordinary reconstruction environment. Run needs a separate
CUDA PyTorch/Diffusers environment. Commanded camera poses remain hypotheses.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def prepare(args):
    from .video_bridge import read
    from .video_triangulate import decode
    run = args.source
    record = json.loads((run / 'metrics.json').read_text())
    frames = decode(run / 'transition.mp4')
    support = np.load(run / 'support.npz')['valid']
    trajectory = np.load(run / 'trajectory.npz')
    n = len(frames)
    if n % 4 != 1 or support.shape != np.asarray(frames).shape:
        raise ValueError('Expected 4k+1 video frames and matching support masks')
    if len(trajectory['T_world_from_camera']) != n:
        raise ValueError('Trajectory and frame count differ')
    if args.size < 128 or args.size % 16:
        raise ValueError('Size must be a multiple of 16, at least 128')
    if args.anchor_every < 1:
        raise ValueError('Anchor interval must be positive')
    # Use uncompressed real endpoints; no withheld observation is read.
    frames[0] = read(record['endpoints'][0])['image']
    frames[-1] = read(record['endpoints'][1])['image']
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    (out / 'frames').mkdir()
    (out / 'masks').mkdir()
    conditioned = []
    for i, frame in enumerate(frames):
        im = Image.fromarray(frame).convert('RGB').resize((args.size, args.size), Image.Resampling.LANCZOS)
        valid = np.asarray(Image.fromarray(support[i].astype('uint8') * 255).resize(
            (args.size, args.size), Image.Resampling.NEAREST)) > 0
        endpoint = i in (0, n - 1)
        anchor = args.mode == 'pose_anchors' and i % args.anchor_every == 0 and not endpoint
        mask = np.zeros(valid.shape, 'uint8') if endpoint else np.where(valid & anchor, 0, 255).astype('uint8')
        # VACE encodes both inactive and reactive streams. White masking alone
        # does not remove source image information from the reactive stream.
        # Neutralize all generation regions, matching first/last-frame usage.
        im = Image.fromarray(np.where(mask[:, :, None] == 0, np.asarray(im), 128).astype('uint8'))
        im.save(out / 'frames' / f'{i:04d}.png')
        Image.fromarray(mask).save(out / 'masks' / f'{i:04d}.png')
        if endpoint or anchor:
            conditioned.append(i)
    height, width = trajectory['frame_shape']
    K = trajectory['K'].copy()
    K[0] *= args.size / width
    K[1] *= args.size / height
    np.savez(out / 'commanded_trajectory.npz', K=K,
             T_world_from_camera=trajectory['T_world_from_camera'], frame_shape=[args.size, args.size])
    files = sorted(p for p in out.rglob('*') if p.is_file())
    manifest = dict(schema=2, mode=args.mode, frames=n, width=args.size, height=args.size,
                    fps=12, conditioned_frame_indices=conditioned, endpoints=record['endpoints'],
                    pose=record['pose'], model='Wan-AI/Wan2.1-VACE-1.3B-diffusers',
                    prompt='A continuous grayscale lunar rover navigation camera view moving over a static rocky lunar surface. Fixed lighting, fixed camera optics, black sky. Terrain and rocks remain stationary and geometrically consistent.',
                    negative_prompt='camera cuts, crossfade, dissolve, morphing rocks, moving ground, changing lighting, people, text, color',
                    mask_convention='black = conditioned; white = generate',
                    generation_regions='neutral RGB 128; no procedural pixels in the reactive stream',
                    pose_status='commanded only; generated camera motion must be checked independently',
                    validation_status='prepared, no learned inference executed',
                    source_hashes={f: digest(run / f) for f in ['transition.mp4', 'trajectory.npz', 'support.npz', 'metrics.json']},
                    preparer_sha256=digest(__file__),
                    files={p.relative_to(out).as_posix(): digest(p) for p in files})
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: manifest[k] for k in ['mode', 'frames', 'width', 'conditioned_frame_indices', 'validation_status']}, indent=2))


def generate(args):
    # Verify portable data before importing or allocating any large GPU models.
    m = json.loads((args.bundle / 'manifest.json').read_text())
    if m.get('schema', 0) < 2:
        raise ValueError('Regenerate the bundle: schema 1 exposed procedural pixels in the reactive stream')
    for name, expected in m['files'].items():
        p = (args.bundle / name).resolve()
        if not p.is_relative_to(args.bundle.resolve()) or digest(p) != expected:
            raise ValueError(f'Bundle integrity check failed: {name}')
    if args.out.exists():
        raise FileExistsError(args.out)
    import torch
    import diffusers
    from diffusers import AutoencoderKLWan, WanVACEPipeline, UniPCMultistepScheduler
    from diffusers.utils import export_to_video
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA PyTorch required; use prepare on the CPU machine')
    from .gpu_probe import report
    hardware = report()
    # CPU offload is not additional physical RAM on Jetson. Avoid default full
    # precision model loading on a <=8 GB shared-memory system.
    if Path('/etc/nv_tegra_release').exists() and not args.prompt_embeds:
        memory = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
        if memory['MemTotal'] < 12 * 1024 * 1024:
            raise RuntimeError('This standard VACE loader is not validated for a <=8 GB Jetson. A separately tested quantized/staged loader or larger GPU host is needed. No model downloaded.')
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    load = dict(revision=args.revision, local_files_only=args.local_files_only)
    model_source = str(args.local_model) if args.local_model else m['model']
    if args.local_model:
        downloaded = json.loads((args.local_model / 'download_manifest.json').read_text())
        if downloaded['model'] != m['model'] or downloaded['revision'] != args.revision:
            raise ValueError('Local model manifest does not match requested checkpoint')
    cached = None
    text_options = {}
    if args.prompt_embeds:
        from safetensors.torch import load_file
        metadata = json.loads(args.prompt_embeds.with_suffix('.json').read_text())
        if any(metadata[k] != value for k, value in [('model', m['model']), ('revision', args.revision),
                                                     ('prompt', m['prompt']), ('negative_prompt', m['negative_prompt'])]):
            raise ValueError('Cached embeddings do not match model, revision or prompt')
        if digest(args.prompt_embeds) != metadata['sha256']:
            raise ValueError('Cached embedding checksum mismatch')
        cached = load_file(str(args.prompt_embeds))
        text_options = {'text_encoder': None, 'tokenizer': None}
    vae = AutoencoderKLWan.from_pretrained(model_source, subfolder='vae', torch_dtype=torch.float32, **load)
    pipe = WanVACEPipeline.from_pretrained(model_source, vae=vae, torch_dtype=dtype, **text_options, **load)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, flow_shift=3.0)
    pipe.vae.enable_tiling()
    if args.offload == 'sequential':
        pipe.enable_sequential_cpu_offload()
    elif args.offload == 'model':
        pipe.enable_model_cpu_offload()
    else:
        pipe.to('cuda')
    images = [Image.open(args.bundle / 'frames' / f'{i:04d}.png').convert('RGB') for i in range(m['frames'])]
    masks = [Image.open(args.bundle / 'masks' / f'{i:04d}.png').convert('L') for i in range(m['frames'])]
    torch.cuda.reset_peak_memory_stats()
    text_inputs = ({k: value.to(dtype=dtype) for k, value in cached.items()} if cached is not None
                   else dict(prompt=m['prompt'], negative_prompt=m['negative_prompt']))
    generated = pipe(**text_inputs, video=images, mask=masks,
                     height=m['height'], width=m['width'], num_frames=m['frames'], num_inference_steps=args.steps,
                     guidance_scale=5.0, conditioning_scale=1.0,
                     generator=torch.Generator(device='cpu').manual_seed(args.seed), output_type='pil').frames[0]
    if len(generated) != m['frames']:
        raise RuntimeError('Model returned unexpected frame count')
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'frames').mkdir()
    for i, im in enumerate(generated):
        im.save(args.out / 'frames' / f'{i:04d}.png')
    export_to_video(generated, str(args.out / 'generated.mp4'), fps=m['fps'])
    endpoint_mae = [float(np.mean(np.abs(np.array(generated[i], dtype=float) - np.array(images[i], dtype=float)))) for i in [0, -1]]
    result = dict(bundle_sha256=digest(args.bundle / 'manifest.json'), model=m['model'], revision=args.revision,
                  mode=m['mode'], seed=args.seed, steps=args.steps, hardware=hardware,
                  torch=torch.__version__, diffusers=diffusers.__version__, runner_sha256=digest(__file__),
                  cached_embeddings_sha256=digest(args.prompt_embeds) if args.prompt_embeds else None,
                  peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(), endpoint_mae_8bit=endpoint_mae,
                  status='generated; pose and reconstruction validity untested',
                  warning='Input poses are commands, not measured output poses. Do not fuse as measured terrain.')
    (args.out / 'inference.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


def encode(args):
    """Encode prompts on a separate CPU host; no video transformer is loaded."""
    import torch
    import diffusers
    from diffusers import WanVACEPipeline
    from transformers import AutoTokenizer, UMT5EncoderModel
    from safetensors.torch import save_file
    m = json.loads((args.bundle / 'manifest.json').read_text())
    if args.out.exists() or args.out.with_suffix('.json').exists():
        raise FileExistsError(args.out)
    torch.set_num_threads(args.threads)
    kwargs = dict(revision=args.revision, cache_dir=str(args.cache) if args.cache else None)
    model_source = str(args.local_model) if args.local_model else m['model']
    if args.local_model:
        downloaded = json.loads((args.local_model / 'download_manifest.json').read_text())
        if downloaded['model'] != m['model'] or downloaded['revision'] != args.revision:
            raise ValueError('Local model manifest does not match requested checkpoint')
    tokenizer = AutoTokenizer.from_pretrained(model_source, subfolder='tokenizer', **kwargs)
    encoder = UMT5EncoderModel.from_pretrained(model_source, subfolder='text_encoder',
                                             torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, **kwargs).eval()
    pipe = WanVACEPipeline(tokenizer=tokenizer, text_encoder=encoder, vae=None, scheduler=None, transformer=None)
    # T5 masks padding keys. Avoid spending CPU time encoding hundreds of
    # padding positions, then restore the pipeline's 512-position zero padding.
    lengths = [len(ids) for ids in tokenizer([m['prompt'], m['negative_prompt']], truncation=False)['input_ids']]
    if max(lengths) > 512:
        raise ValueError('Prompt exceeds the model token budget')
    sequence_length = min(512, max(32, ((max(lengths)+31)//32)*32))
    print(f'Encoding {lengths} tokens with {sequence_length} T5 positions on CPU', flush=True)
    with torch.inference_mode():
        positive, negative = pipe.encode_prompt(m['prompt'], negative_prompt=m['negative_prompt'],
                                                device='cpu', dtype=torch.bfloat16, max_sequence_length=sequence_length)
    positive = torch.nn.functional.pad(positive, (0, 0, 0, 512-sequence_length))
    negative = torch.nn.functional.pad(negative, (0, 0, 0, 512-sequence_length))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    save_file({'prompt_embeds': positive.contiguous(), 'negative_prompt_embeds': negative.contiguous()}, str(args.out))
    metadata = dict(model=m['model'], revision=args.revision, prompt=m['prompt'], negative_prompt=m['negative_prompt'],
                    sha256=digest(args.out), torch=torch.__version__, diffusers=diffusers.__version__,
                    shape=list(positive.shape), device='cpu', dtype='bfloat16')
    metadata['encoded_sequence_length'] = sequence_length
    args.out.with_suffix('.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--source', type=Path, required=True)
    prep.add_argument('--out', type=Path, required=True)
    prep.add_argument('--size', type=int, default=480)
    prep.add_argument('--mode', choices=['endpoints_only', 'pose_anchors'], default='pose_anchors')
    prep.add_argument('--anchor-every', type=int, default=4)
    run = sub.add_parser('run')
    run.add_argument('--bundle', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--revision', required=True, help='Pinned model repository commit for reproducibility')
    run.add_argument('--seed', type=int, default=7)
    run.add_argument('--steps', type=int, default=30)
    run.add_argument('--offload', choices=['none', 'model', 'sequential'], default='model')
    run.add_argument('--local-files-only', action='store_true')
    run.add_argument('--prompt-embeds', type=Path, help='Precomputed safetensors plus JSON from encode; avoids loading T5 on Jetson')
    run.add_argument('--local-model', type=Path, help='Verified local directory from model_fetch')
    enc = sub.add_parser('encode')
    enc.add_argument('--bundle', required=True, type=Path)
    enc.add_argument('--revision', required=True)
    enc.add_argument('--out', required=True, type=Path)
    enc.add_argument('--cache', type=Path)
    enc.add_argument('--local-model', type=Path)
    enc.add_argument('--threads', type=int, default=4)
    args = p.parse_args()
    {'prepare': prepare, 'run': generate, 'encode': encode}[args.command](args)


if __name__ == '__main__':
    main()
