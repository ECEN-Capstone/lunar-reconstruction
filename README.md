# Chandrayaan-3 lunar terrain reconstruction

Conventional CAHV stereo geometry, OpenCV SGBM, conservative point clouds and local meshes, plus validated local camera registration and voxel fusion. Original mission inputs are never modified.

**Legacy outputs retain the camera files' original units, now interpreted as millimetres using the mission Navcam paper. New `terrain_*_m.obj` outputs are already in metres.** The [terrain completion pilot](TERRAIN_COMPLETION.md) adds relaxed stereo and labelled hole filling for simulation. Gravity alignment, acquisition motion and absolute accuracy remain unverified. Read [RECONSTRUCTION_REPORT.md](RECONSTRUCTION_REPORT.md) for the earlier conservative experiments; its unresolved-unit statements predate the paper evidence.

## Get the data and results

### November 10 methods and results

- Read the illustrated methods paper as a [PDF](output/methods_paper/Pragyan_terrain_reconstruction_methods.pdf) or an [editable Word document](output/methods_paper/Pragyan_terrain_reconstruction_methods.docx). Pages 5–6 work through the rover route and timestamp associations. Pages 12–14 quantify what the procedural video contributed and how it compared with withheld real stereo.
- Open the [results gallery](output/detailed_progress_2026-11-10/RESULTS_GALLERY.html) locally after cloning to inspect renders of 102 saved OBJ products and play the clips. The [atlas manifest](output/detailed_progress_2026-11-10/atlas_manifest.json) identifies the corresponding model files and hashes.
- Browse [all 93 slide previews](output/detailed_progress_2026-11-10/slide_previews/), [detailed methods and results](output/detailed_progress_2026-11-10/DETAILED_METHODS_AND_RESULTS.md), and [speaker notes](output/progress_presentation/DETAILED_REPORT_AND_SPEAKER_NOTES.md).
- Trace the [placement of all 56 observations](output/all_observations_overlay/README.md), inspect the [video reconstruction experiments](output/chronological_video/REPORT.md), and compare them against the [fixed-region interpolation baseline](output/collaboration_review/2026-11-09/COMPARISON_FINDINGS.md).

### Clone with Git LFS

This repository includes mission inputs, reconstruction artifacts, and completed terrain outputs using **Git LFS**. Install Git LFS before cloning. The complete working data is approximately **5.4 GiB**; LFS download bandwidth is charged to the repository owner's allowance. Preserve the mission-provider notices and source provenance with any further distribution. See [GitHub's LFS billing documentation](https://docs.github.com/en/billing/concepts/product-billing/git-lfs) for current allowances.

```powershell
git lfs install
git clone git@github.com:ECEN-Capstone/lunar-reconstruction.git
cd lunar-reconstruction
git lfs pull
```

For an existing clone, run `git lfs install`, `git pull --ff-only`, then `git lfs pull`. A three-line file beginning with `version https://git-lfs.github.com/spec/v1` is an LFS pointer: download its content with `git lfs pull` before opening it as an image or mesh. Prefer a Git/LFS clone over GitHub's Download ZIP, whose inclusion of LFS content depends on repository settings.

To download only the completed terrain assets, first clone without fetching LFS content, then request those folders:

```powershell
$env:GIT_LFS_SKIP_SMUDGE = "1"
git clone git@github.com:ECEN-Capstone/lunar-reconstruction.git
Remove-Item Env:\GIT_LFS_SKIP_SMUDGE
cd lunar-reconstruction
git lfs pull --include="output/closed_terrain/**,output/largest_terrain/**,output/completed_terrain_renders/**" --exclude=""
```

Useful starting points:

- [Obs 034 closed OBJ](output/closed_terrain/obs_034/terrain_closed_m.obj).
- [Obs 044 component closed OBJ](output/largest_terrain/component_obs_044/closed/terrain_closed_m.obj), combining observations 044 through 048.
- [Completed terrain renders](output/completed_terrain_renders/).
- [Generated-stereo experiment report](output/generated_stereo_trial/REPORT.md) and [uber relaxed results](output/uber_relaxed/REPORT.md).
- [Slide figures and copy](output/generated_stereo_slide_pack/).

The closed terrain OBJ files use metres. Legacy `*_calibration_units` files use millimetres; generated-stereo diagnostic meshes use arbitrary baseline units. Completion includes inferred terrain and artificial walls/base; closed topology does not establish physical accuracy or flight readiness.

Source code, JSON configuration, metadata, and Markdown reports use ordinary Git. Numerical arrays, meshes, image assets, archives, and large calibration tables use LFS. `.venv`, Python caches, secrets files, and new scratch files under `tmp/` remain excluded. Existing tracked scratch files predate this setup.

## Python environment

Python 3.12 was used. In PowerShell from this repository:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The existing `.venv` is ready in the execution environment. The recorded complete environment is `artifacts/investigation/environment_freeze.txt`. Python may instead be invoked through any installed Python 3.12 executable when the launcher does not list 3.12. On this machine the executable used was `C:\Users\rhunt\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`, with `-m venv --system-site-packages .venv`, followed by installing missing packages. A new standalone environment can use the full requirements file.

## Reproduce

```powershell
# Inventory files, hashes, metadata, LUTs, duplicate pixels, all-pair geometry
.\.venv\Scripts\python.exe -m reconstruction.investigate
.\.venv\Scripts\python.exe -m reconstruction.audit_metadata
# Synthetic tests of projection, triangulation and disparity sign
.\.venv\Scripts\python.exe -m reconstruction.check_geometry
# First milestone: raw stereo -> rectification -> disparity -> depth -> PLY
.\.venv\Scripts\python.exe -m reconstruction.stereo --observation obs_003 --run my_raw_baseline
# Wider disparity search, raw information mask, calibrated intensity
.\.venv\Scripts\python.exe -m reconstruction.stereo --config configs/terrain.json --observation obs_029 --run my_terrain
# All supported pairs, with an explicit rejection log
.\.venv\Scripts\python.exe -m reconstruction.batch --run my_batch
# Spatial support filtering, preserving the preceding run
.\.venv\Scripts\python.exe -m reconstruction.filter_clouds --batch my_batch --run my_filtered
# Estimate poses and fuse each connected component separately
.\.venv\Scripts\python.exe -m reconstruction.register --batch my_filtered --run my_registration
# Assemble observed triangles within each registered component; holes remain
.\.venv\Scripts\python.exe -m reconstruction.assemble_meshes --batch my_filtered --registration my_registration
# Re-open PLY exports, check mesh topology, render meshes and re-hash source files
.\.venv\Scripts\python.exe -m reconstruction.inspect_outputs --batch my_filtered --registration my_registration
```

Run names must be new: scripts refuse to overwrite existing experiment directories. Investigation outputs are regenerable summaries. Dense baseline runs save original left/right disparity arrays, rectified and matching images, axial depth, XYZ arrays, individual filtering masks, PLY point clouds, PLY/OBJ local meshes, provenance, metrics and diagnostics. Filtered runs refer back to their baseline for disparity and right imagery. Coordinates are x right, y down, z forward in the rectified left camera. Fused components use their first camera as origin; they are not one globally georeferenced map.

## Current results

- [Chronological video experiment](output/chronological_video/REPORT.md): procedural monocular-video reconstruction, conditional mobility-based bridging, closed terrain integration, and heldout error comparisons. The procedural video results currently perform worse than interpolation; learned video inference remains a separate experiment.

- [Technical report](RECONSTRUCTION_REPORT.md): calibration provenance, experiment comparisons, all frame metrics, failures and precise blockers.
- [Largest supported frame preview](artifacts/runs/r11_filtered_batch/obs_034/filtered_diagnostics.png), [PLY cloud](artifacts/runs/r11_filtered_batch/obs_034/points_calibration_units.ply), [OBJ mesh](artifacts/runs/r11_filtered_batch/obs_034/local_mesh_calibration_units.obj).
- [Representative multi-frame fusion](artifacts/runs/r12_registration/component_obs_029/fusion_views.png) and [supported fused PLY](artifacts/runs/r12_registration/component_obs_029/cloud_multiview_supported_calibration_units.ply).
- [Registration and component results](artifacts/runs/r12_registration/components.json); component folders include trajectories, clouds, and observed-triangle mesh unions.

There are 50 filtered frame clouds and local meshes, six fused components, and six rejected candidate pairs. The newer three-scene completion pilot adds nine metre-scale OBJ variants; see [results and limitations](TERRAIN_COMPLETION.md). These remain experimental simulator surfaces, with acquisition stationarity and gravity alignment unresolved.

## Configuration

- `configs/baseline.json`: unmodified raw 8-bit input, 256 disparities, 5-pixel block. Retained as an intentionally limited baseline.
- `configs/terrain.json`: 512 disparities with matching padding, 1-pixel left/right consistency, raw clipping/shadow masks, uniqueness and speckle rejection. Padding compensates for OpenCV's fixed search strip; source-coordinate validity still gates every point.
- `configs/filtering.json`: source-border rejection, minimum disparity, neighbourhood support and connected-component thresholds. This sacrifices coverage; small real features can be excluded.
- `configs/registration.json`: temporal search window, PnP inlier thresholds, held-out validation, independent target-depth checks, and voxel size expressed as a fraction of the supplied baseline.

Use `--family NR` or `--family NC` and `--preprocessing none` or `--preprocessing clahe` for controlled stereo comparisons. None of these algorithm settings is a physical camera calibration parameter. Camera quantities are read directly from `chandrayaan-3-documentation/nav/calibration/*cahv.txt`.

## Repository map

Uber relaxed generated-stereo sweep: [results](output/uber_relaxed/REPORT.md), [textured OBJ bundle](output/uber_relaxed/uber_relaxed_meshes.zip), [settings](configs/uber_relaxed.json). Run `python -m reconstruction.uber_relaxed --output output/uber_relaxed_new` to reproduce. Includes extreme filter relaxation and an empirical right-image row correction; all coordinates are arbitrary baseline units. Production settings are unchanged.

Generated stereo experiment: [report and results](output/generated_stereo_trial/REPORT.md), [split-image ZIP](output/generated_stereo_trial/split_stereo_images.zip). Both supplied generated pairs fail the original camera geometry gate. The [runner](reconstruction/generated_stereo_trial.py) preserves native splits, makes 1024-pixel analysis copies, tests real controls, and exports explicitly invalid-geometry dense diagnostics without weakening production rejection. [Artifact checks](reconstruction/check_generated_trial.py) verify splits, source hashes, diagnostic exports, and exact real-control reproduction.

`chandrayaan-3-navcam-sorted/` holds 56 candidate pairs in raw NR and calibrated NC families. Its `stereo_pairs.csv` maps filenames; acquisition time and mobility ID together matter. `chandrayaan-3-documentation/nav/` holds calibration and PDS4 documentation. `reconstruction/` is the implementation; `configs/` holds reproducible settings; `artifacts/investigation/` and `artifacts/runs/` hold the saved experiment results. Mission images and generated artifacts are versioned with Git LFS as described above; local environments and caches are excluded.

The dataset includes a mission-provider redistribution notice in the quick guide and SIS. Keep source-data provenance with capstone deliverables.
