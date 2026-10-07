# Chandrayaan-3 lunar terrain reconstruction

Conventional CAHV stereo geometry, OpenCV SGBM, conservative point clouds and local meshes, plus validated local camera registration and voxel fusion. Original mission inputs are never modified.

**Legacy outputs retain the camera files' original units, now interpreted as millimetres using the mission Navcam paper. New `terrain_*_m.obj` outputs are already in metres.** The [terrain completion pilot](TERRAIN_COMPLETION.md) adds relaxed stereo and labelled hole filling for simulation. Gravity alignment, acquisition motion and absolute accuracy remain unverified. Read [RECONSTRUCTION_REPORT.md](RECONSTRUCTION_REPORT.md) for the earlier conservative experiments; its unresolved-unit statements predate the paper evidence.

## Environment

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

`chandrayaan-3-navcam-sorted/` holds 56 candidate pairs in raw NR and calibrated NC families. `stereo_pairs.csv` maps filenames; acquisition time and mobility ID together matter. `chandrayaan-3-documentation/nav/` holds calibration and PDS4 documentation. `reconstruction/` is the implementation; `configs/` holds reproducible settings; `artifacts/investigation/` and `artifacts/runs/` hold local results. Images, environments and generated artifacts are ignored by Git; source code, configs, report and README are tracked deliverables. Preserve the local artifacts separately when moving this repository.

The dataset includes a mission-provider redistribution notice in the quick guide and SIS. Keep source-data provenance with capstone deliverables.
