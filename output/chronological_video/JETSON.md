# Jetson experiment setup

The authorized SSH connection to Jarvis works. Read-only inspection on 2026-11-07
identified an Orin Nano Super developer kit with 7.3 GiB usable system RAM,
approximately 6.4 GiB available before setup, no swap, and approximately 97 GB
free storage. The installed platform reports Jetson Linux R39.2.1, Ubuntu 24.04,
Python 3.12.3, NVIDIA driver 595.78, and driver CUDA compatibility 13.2. The
JetPack metapackage is absent, so use the L4T release as the exact platform ID.

All experiment files are under `/home/rhunt/capstone-video`. No OS upgrade,
reflash, power-mode change, swap change or system Python replacement was made.
The temporary PC text-encoding environment is `tmp/learned_cpu` in this repo;
the ordinary reconstruction `.venv` is unchanged.

## Memory strategy

The pinned model is `Wan-AI/Wan2.1-VACE-1.3B-diffusers`, revision
`ec4d2cb062b548996b179d493fdd05340de702a1`.

- Its text encoder checkpoint is 11.36 GB. Encode the fixed positive/negative
  prompts on the 32 GB PC once; transfer the small safetensors embeddings.
- Load only the video transformer and VAE on the Jetson. The transformer
  checkpoint is 7.15 GB on disk; loading at reduced precision saves weight RAM,
  but activation, VAE and CUDA memory still have to fit.
- Begin with 33 frames at 256 × 256 for a feasibility test. The 480 × 480
  endpoint-only and pose-anchor bundles are ready for a subsequent comparison.
- CPU offloading on Jetson shares the same physical RAM. It is not equivalent
  to adding a desktop host RAM pool. Generation has not yet been demonstrated.

## Runtime status

An isolated `.venv` contains Diffusers 0.35.2, Transformers 4.57.1 and Accelerate
1.11.0. The initially inspected NVIDIA SBSA PyTorch 2.11 wheel targets SM 11.0 and
12.1, not this Orin. An upstream PyTorch 2.11/CUDA 13.0 wheel runs basic CUDA
matrix operations, but explicitly warns about the Orin SM 8.7 target. Do not
describe that as a validated model runtime. An Orin-targeted Python 3.12 wheel
from the Jetson AI Lab CUDA 12.9 index explicitly contains `sm_87` kernels. It is
being installed with CUDA 12 runtime libraries in a separate `.venv-orin`.
Actual inference and kernel compatibility still need validation.

Ordinary Hugging Face and Xet downloads stalled. The repository now includes a
resumable byte-range downloader, `reconstruction.model_fetch`, which checks
provider SHA256 hashes for model weights and Git blob hashes for configuration
files. Large weights and caches stay in ignored temporary/model directories.
The PC text model download completed and passed all checksums. CPU prompt
encoding completed: finite positive/negative tensors of shape 1 × 512 × 4096,
stored in an 8,388,800-byte safetensors file (less than 0.5 MB compressed with its
large zero-padding region). Encoding skipped masked padding positions; a small
UMT5 equivalence check differed by at most 5.96e-7. The embeddings and matching
prompt/model metadata have been transferred to the Jetson.

The video model download and `.venv-orin` dependency installation are still in
progress. `reconstruction/jetson_smoke.py` provides a guarded launcher: wait for
installation, verify SM 8.7 plus float32/bfloat16 matrix, attention and 3D
convolution operations, wait for the verified model manifest, then attempt a
four-step 256-pixel video with sequential offloading. It records status and
fails on missing prerequisites. No learned video has been produced yet.

The 256-pixel procedural control failed intermediate-frame real-anchor pose
checks (only two endpoint frames accepted). Thus the low-resolution smoke run
can test memory/runtime feasibility only. Reconstruction validation requires
higher-resolution output; the 480-pixel control passed all 33 pose checks.

## Commands after hardware/runtime validation

On the PC, download just the encoder and tokenizer, then encode:

```powershell
tmp/learned_cpu/Scripts/python -m reconstruction.model_fetch --revision ec4d2cb062b548996b179d493fdd05340de702a1 --parts text_encoder tokenizer --out tmp/wan_text_model --workers 8
tmp/learned_cpu/Scripts/python -m reconstruction.learned_video encode --bundle output/chronological_video/learned_inputs/holdout046_pose_anchors --revision ec4d2cb062b548996b179d493fdd05340de702a1 --local-model tmp/wan_text_model --out output/chronological_video/learned_inputs/lunar_prompt.safetensors
```

On the Jetson, download only `transformer vae scheduler` with `model_fetch`.
Supply `--local-model`, the matching `--revision` and `--prompt-embeds` to
`reconstruction.learned_video run`. Inference refuses to overwrite output.
Save package versions, memory diagnostics, raw generated frames and the video.
Do not substitute the real input endpoints into the output to conceal endpoint
drift; the runner measures endpoint image differences.

After inference, run the real-anchor pose diagnostic and withheld-observation
terrain comparison on the PC. Commanded poses must not silently become measured
poses. A nice-looking video alone is not evidence of accurate gap geometry.

Sources: [NVIDIA Tegra memory architecture](https://docs.nvidia.com/cuda/cuda-for-tegra-appnote/index.html),
[Jetson package index](https://pypi.jetson-ai-lab.io/),
[VACE interface](https://huggingface.co/docs/diffusers/api/pipelines/wan#diffusers.WanVACEPipeline).
