# Chronological video reconstruction: collaboration handoff

Prepared 2026-11-07; allocation updated 2026-11-09. **Independent review has resumed.
No learned output has been received locally.** The colleague now uses his own GPU;
Jarvis is available to the user and this assistant. Its jobs were last observed paused.
This update supersedes the ownership instructions in the original handoff ZIP.
It does not start remote jobs or authorize agents to message each other.

## Objective and current result

Generate monocular video between chronological rover observations using the best
available pose evidence, reconstruct it, quantify error against withheld real
stereo, and integrate useful inferred terrain with the existing stereo pipeline.
Unseen terrain must remain explicitly labelled synthetic.

The implemented **procedural** baseline renders a hypothesized textured terrain
along a camera path, reconstructs the resulting video independently, and combines
it with stereo. It produces closed OBJ/STL models, but currently performs worse
than interpolation. It is not MarsGen or diffusion generation.

Key evidence:

- 044 → 047, withholding observation 046: three-seed consensus scored 85 of 561
  eligible cells. Video height RMSE = **8.45 cm**, same-cell linear interpolation
  = **1.25 cm**, IDW = **3.52 cm**. Reference is registered stereo, not survey truth.
- Conditional 033 → 034 bridge: approximately **49.98 m²** completed envelope;
  9,872 strict stereo cells unchanged, 253 relaxed stereo cells, 994 synthetic
  video cells, 8,888 interpolation cells. Only **250 cells / 0.625 m²** of video
  support lie outside both endpoint footprint hulls. Closure checks pass; this
  does not establish flight readiness or physical accuracy.
- Real-anchor camera checks pass all 33 frames of the 480-pixel procedural
  control. For 24 unconditioned frames, median trajectory differences are
  4.7 mm / 0.050°. The 256-pixel control has **zero accepted unconditioned poses**;
  use 256 only for runtime feasibility, not terrain validation.
- External-video evaluation at 480 pixels, using estimated poses and excluding
  conditioning frames, adds 638 cells but scores only 21: RMSE 4.90 cm versus
  linear 0.85 cm. This is a different protocol from the first result above.
- Among 49 adjacent intervals with supported stereo: seven have registered poses
  and enough translation, one has a configured mobility prior, 35 have no pose in
  the current graph/prior catalog, three have insufficient translation, and three
  share timestamps. There is no solved global rover trajectory.

Read `output/chronological_video/REPORT.md` for figures, metrics and reproduction.
`JETSON.md` records setup history; the restart notes below supersede its older
in-progress descriptions. All paths below are relative to the repo unless noted.

## Recommended division of responsibility

### Colleague's Astra: implementation and execution owner

Own implementation and learned-video execution on the colleague's own GPU:

1. Verify the colleague's GPU runtime and obtain the pinned model on that machine.
2. Transfer the corrected **schema 2 / `_v2`** input bundles and current scripts there.
3. Run a feasibility test, then the higher-resolution learned experiment. Jetson
   setup and its suspended download are no longer prerequisites for this work.
4. Compare endpoint-only versus pose-anchor conditioning, initially on the
   044 → 047 heldout-046 case; use matching seeds/settings for fair comparisons.
5. Run `video_pose_check` and `evaluate_video`; diagnose failures without silently
   relaxing acceptance criteria or substituting commanded camera poses.
6. After the controlled experiment works, run the actual nonregistered 033 → 034
   interval, retaining its conditional pose assumptions. Prepare its input bundles
   with the same schema-2 preparer; only the 044 → 047 bundles currently exist.
7. If there is usable support, run seeds 7/17/27 and integrate labelled candidates
   through `video_integrate`. Quantify coverage and errors, including worse results.
8. Return a branch/commit or patch plus the compact result package below. If
   hardware is inadequate, report the measured failure and resource use before
   choosing a different execution machine. Record the actual GPU and memory used.

Suggested ownership: Astra edits all implementation scripts, configuration and
experiment outputs during this phase. It may fix evaluation code as needed, but
must describe changes to validation criteria and rerun the affected controls.

### This assistant: independent review and final synthesis

Keep my remaining usage for reviewing Astra's returned evidence rather than
duplicating the GPU work. I will review heldout-data exclusion, camera-pose
evidence, fair baseline comparisons, provenance and unchanged stereo geometry;
check mesh closure/results; then consolidate the report and slide figures.
During Astra's work, I should make no concurrent changes to its implementation.
Jarvis is available for this assistant's complementary work; the user has complete
access and the colleague is using a separate GPU. Its partially prepared runtime
and paused download can remain preserved until a specific local job needs them.
Separate hardware does not remove the need to coordinate source-code ownership.

The user reports the colleague's Astra is working. This assistant has not sent it
a message or created a new chat. See the independent review addendum under
`output/collaboration_review/2026-11-09/REVIEW.md` for requested validation fixes.

## Repository and transfer

Repository: `git@github.com:ECEN-Capstone/lunar-reconstruction.git`.
Current local root: `C:/Users/rhunt/Documents/Capstone/reconstruction`.
The implementation and new outputs are **uncommitted and not on GitHub**.

The accompanying ZIP is an overlay containing source, configs, documentation and
the chronological experiment outputs. It excludes `.git`, virtual environments,
large model caches, credentials and the original mission dataset. On a clean
clone with the existing Git LFS data downloaded, create a work branch and extract
the overlay at the repository root. Do not overwrite a colleague's uncommitted
work; use a separate clone/worktree if necessary. See `HANDOFF_MANIFEST.json` in
the ZIP for the exact base commit and file checksums. Do not commit the handoff
ZIP itself back into the repo.

Original data required by the scripts lives under `artifacts/runs/r11_filtered_batch`,
`r12_registration`, `r15_terrain_completion`, and the NavCam calibration directory.
These come from the existing repository/LFS checkout, not the overlay ZIP.

## Jetson restart notes — last observed state at pause

Host: `rhunt@jarvis` through the user's Tailscale network. Credentials are excluded.
The user confirmed colleague access, but subsequently assigned learned generation
to the colleague's own GPU. These historical Jetson notes are retained for this
assistant's future use, not as tasks for the colleague.

Remote workspace: `/home/rhunt/capstone-video`.
Hardware: Orin Nano Super, 8 GB class / 7.3 GiB usable RAM, no swap; L4T R39.2.1,
Ubuntu 24.04, Python 3.12.3. No OS upgrade, reflash or power changes were made.

- `.venv-orin`: PyTorch **2.8.0**, CUDA **12.9**, compiled **sm_87**, plus
  Diffusers 0.35.2, Transformers 4.57.1, Accelerate 1.11.0. The earlier `.venv`
  is an unsuitable trial runtime; do not use it for the main experiment.
- Initial smoke job `smoke256_seed7` **failed before inference** because libraries
  were missing. It is terminal, not waiting. Preserve its failure logs.
- Subsequently installed `nvidia-nvtx-cu12==12.6.77` (newer NVTX lacked the legacy
  library) and `nvidia-cufile-cu12==1.14.1.1`.
- OpenBLAS was downloaded from Ubuntu and extracted locally into
  `runtime-libs/usr/lib/aarch64-linux-gnu/openblas-pthread/`. **The runtime has not
  been retested after this extraction.** Add this folder to the process's
  `LD_LIBRARY_PATH`, alongside `.venv-orin/lib/python3.12/site-packages/nvidia/*/lib`.
  Use `ldd` to identify any further missing dependencies. Do not replace system CUDA.
- Repo `reconstruction/jetson_smoke.py` sets the NVIDIA paths but still needs the
  OpenBLAS path added. Verify imports and float32/bfloat16 matmul, attention and
  3D convolution before loading a full model.
- The video-model downloader, last PID **11192**, was suspended with **SIGSTOP**
  when the user paused. Verify its current command line/state before sending
  SIGCONT; never signal a reused PID. If it no longer exists, use the resumable
  downloader against the same directory instead of discarding partial files.
- Model directory: `models/wan-vace-1.3b`; log: `model-download.log`. It is a pinned
  Wan-AI/Wan2.1-VACE-1.3B-diffusers checkpoint, revision
  `ec4d2cb062b548996b179d493fdd05340de702a1`. Completion requires the verified
  `download_manifest.json`, not merely the presence of partial files.
- The corrected v2 transfer was **canceled at the password prompt**. Jarvis still
  has old input bundles/runner copies. Transfer current source and `_v2` bundles
  before restarting inference. Use a new job name because status files cannot
  be overwritten. The old root-level `jetson_smoke.py` is also stale; use the
  current repo module after fixing its library path.

Local PC text encoding is complete. `learned_inputs/lunar_prompt.safetensors`
under `output/chronological_video` contains finite positive/negative tensors,
shape 1 × 512 × 4096. Its SHA256 is
`129f8797f64f6e9c9b48e866b9db8cd8ef29b34da25887e0afb1cf45ac1d461d`.
This file and its JSON metadata already exist on Jarvis with that same checksum.
It avoids loading the 11.36 GB text encoder on the Jetson. The local source model
cache is verified at `tmp/wan_text_model`; do not download/encode it again.

## Critical experiment correction

VACE encodes image information in both its inactive and reactive streams. White
masks alone do not remove procedural pixels. Schema-2 preparation replaces every
white-mask pixel with RGB 128, retaining real endpoints and only selected valid
pose-anchor regions. All three `_v2` bundles were checked for this property.
The current runner rejects schema-1 bundles. Old bundles are superseded; no learned
result was generated from them. Prompt embeddings remain valid because prompts
and the model revision did not change.

## Result package Astra should return

- Code commit/patch and exact invocation, model revision, package versions,
  runtime/memory observations, failures and any changes to the validation gates.
- Each run's original generated MP4 and PNG frames, `inference.json`, input bundle
  manifest, pose-check JSON/NPZ, reconstruction metrics/surfaces, and seed.
- Same-cell video versus IDW/linear error statistics with scored/eligible cell
  counts and coverage; report raw errors before filtering as well.
- For integrated terrain: OBJ/STL, provenance grid/CSV, closure validation and
  evidence that strict stereo geometry is unchanged. Distinguish true areas
  between endpoint footprints from holes inside either existing footprint.
- One contact sheet, one provenance map, one error comparison; a short statement
  of what worked, what failed, and what remains conditional.

Do not call a four-step smoke output a validated reconstruction. Do not replace
generated endpoint frames with real images to hide drift. Do not use heldout 046
to generate images or estimate the input endpoint trajectory. Do not describe
synthetic consensus, a watertight mesh, or a plausible-looking video as ground truth.
