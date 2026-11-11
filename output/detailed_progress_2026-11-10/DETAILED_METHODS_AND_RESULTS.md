# Reconstruction methods and complete result atlas

Evidence snapshot: 10 November 2026. Slides 1–13 remain the 15-minute presentation; the appended atlas supplies the full review record. All meshes are renders of actual saved OBJ outputs. No new reconstruction or learned model is claimed.

## Slide 33: Detailed evidence atlas: what is actually available

Slides 1–13 remain the result-first 15-minute route. Slides 14–32 are the original technical appendix. This expanded atlas documents the actual saved outputs at the 10 November snapshot. It does not count multiple seeds, parameter sweeps or procedural controls as independent learned video methods. The all-observation rendering is an illustrative command-derived placement, not a global reconstruction. Individual mesh panels use independent complete extents, nominal up and no vertical exaggeration. Color on real/generated mesh panels is per-panel relative height; provenance colors on video panels have a different explicit legend. All OBJ faces are drawn; empty image margins are trimmed, geometry is not cropped.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/atlas_manifest.json

## Slide 34: 1. Camera rays and metric convention

Source CAHV has non-unit A vectors. Normalizing A alone changes the camera model. Original archival report predates the later nominal-baseline paper; metric outputs use the subsequent mm convention. Absolute scale uncertainty and calibration covariance are unavailable. Nominal rover-local Z is not independently measured lunar vertical.
Rig calibration provides relative rays; it does not provide the rover’s global trajectory.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/geometry.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/RECONSTRUCTION_REPORT.md
- C:/Users/rhunt/Documents/Capstone/reconstruction/TERRAIN_COMPLETION.md

## Slide 35: 2. Pair admission and dense stereo matching

The pair gate checks the fixed calibrated rig, before dense matching. Fundamental-matrix estimation rejects feature mismatches but does not replace calibration. Raw masks prevent corrected gray values from disguising sensor saturation. Thresholds here are the production stereo stage, before the final r11 support filter.
Failure of the calibrated pair gate cannot be fixed by accepting more dense pixels.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/stereo.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_034/provenance.json

## Slide 36: 3. Support filtering, triangulation and open meshes

No smoothing, plane fitting or hole filling changes retained observed XYZ. Local coverage is whole-image pixel acceptance, not the fraction of lunar terrain recovered. The atlas converts exported camera coordinates to nominal rover coordinates only for display. Raw SGBM used disparity ≥16 before this support stage tightened it to 32.
For small errors, σZ/Z ≈ σd/d; low disparity magnifies error, even with subpixel consistency.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/configs/filtering.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/stereo.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/RECONSTRUCTION_REPORT.md

## Slide 37: 4. Register observations only where overlap supports it

Target depth is checked after pose fitting, but both views share calibration biases. Non-tree edges are cycle diagnostics. This is not global bundle adjustment or a measured lunar trajectory. There are 37 components: six multi-observation groups and 31 singletons. Duplicated acquisitions can weaken the independence of view counts.
Fused voxel count and multi-view-supported voxel count are different quantities.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/configs/registration.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/register.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/RECONSTRUCTION_REPORT.md

## Slide 38: 5. Fill terrain holes while retaining source labels

The footprint is a selected projected convex envelope, not surveyed terrain boundaries. Mesh projected area differs from cell count × grid area at boundary triangles. Closure removes open edges but cannot recover hidden craters, rocks, or correct an erroneous upper surface. Large unsupported spans have no terrain accuracy bound.
More complete geometry is useful for simulation; inferred areas must remain distinguishable.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/configs/completion.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/close_terrain.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/TERRAIN_COMPLETION.md

## Slide 39: 6. Construct a procedural monocular video

Noise is fixed in world coordinates and tapers with distance from anchors, rather than changing terrain through time. The two real endpoint images remain actual input photographs. Distant panorama appearance is excluded from geometric support. Playback length is not the rover’s physical travel duration. These clips are procedural, not learned diffusion outputs.
This creates a controlled image experiment from an assumed surface; it does not observe unknown terrain.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/video_bridge.py

## Slide 40: 7. Estimate and check poses from output frames

Conditioned frames and unconditioned frames are reported separately. A frozen image can yield a valid stationary pose; this is not proof of reconstructable camera motion. Pose-check hashes bind the returned clip and anchor bundle. The current one-anchor path lacks an independent second-anchor depth test.
Pose reprojection tests image consistency; useful triangulation also needs parallax and stable geometry.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/video_pose_check.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/evaluate_video.py

## Slide 41: 8. Sparse video reconstruction: three-view geometry

The small reported reprojection residuals are after rejection by the 0.85 px gate. They are not an independent 3D accuracy metric. In the external evaluator, selected valid frames are compressed into a new list; original index gaps remain recorded but are not fully retained in tracking-window construction. This is a known evaluation limitation.
Check geometry, accepted-cell coverage and withheld terrain error together.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/video_triangulate.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/evaluate_video.py

## Slide 42: 9. Dense video reconstruction: height-plane search

The search is along height, not a free 3D point search. Best cost uniqueness excludes nearby levels by eight 1 cm steps. Dense reconstruction currently has no explicit per-cell ray-angle/parallax gate; frozen-video candidates demonstrate the resulting acceptance weakness.
1 cm height search spacing is numerical resolution, not achieved terrain accuracy.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/video_triangulate.py

## Slide 43: 10. Merge candidates, compare seeds, close the surface

Seed agreement measures repeatability under this prior, not external correctness. The seed integration audit also found that duplicate run entries can count as extra votes despite the unique-seed precondition; inputs must be de-duplicated before promotion. Height gates can improve surviving error by selecting a small subset and bias results toward the interpolation prior.
The visible completed mesh mixes evidence and inference; source proportions must accompany it.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/video_bridge.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/video_integrate.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/close_terrain.py

## Slide 44: 11. Evaluate pose and depth without survey truth

Registered stereo is a noisy reference with shared calibration and possible pose bias, not ground truth. Spatial depth-mask tests retain endpoint photographs and already-estimated poses: they are easier than withholding an entire observation. The original exploratory rule requires ≥100 scored cells, median≤5 cm and p90≤15 cm, but passing this rule does not establish improvement over a baseline.
Compare methods on fixed data and matched protocols; do not rank different subsets or resolutions.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/reconstruction/video_bridge.py
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/collaboration_review/2026-11-09/COMPARISON_FINDINGS.md

## Slide 45: 12. Separate pose error from depth error

The existing sensitivity experiment illustrates non-identifiability; its variants are not confidence intervals. Six of nine variants passed the height fit and five reached vertical bounds. The additional ablations listed are proposed next work, not completed evidence. Keep rendering truth separate and use it only for controlled synthetic evaluation.
A smooth surface or good height fit alone cannot validate horizontal pose.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/collaboration_review/pose_sensitivity_2026-11-09/FINDINGS.md

## Slide 46: Observed terrain atlas: 001–004

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_001/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_001/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_001/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_002/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_002/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_002/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_003/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_003/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_003/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_004/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_004/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_004/rectified_left.png

## Slide 47: Observed terrain atlas: 005–008

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_005/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_005/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_005/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_006/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_006/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_006/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_007/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_007/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_007/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_008/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_008/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_008/rectified_left.png

## Slide 48: Observed terrain atlas: 009–012

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_009/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_009/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_009/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_010/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_010/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_010/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_011/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_011/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_011/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_012/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_012/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_012/rectified_left.png

## Slide 49: Observed terrain atlas: 013–017

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_013/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_013/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_013/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_014/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_014/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_014/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_016/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_016/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_016/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_017/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_017/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_017/rectified_left.png

## Slide 50: Observed terrain atlas: 018–021

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_018/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_018/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_018/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_019/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_019/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_019/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_020/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_020/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_020/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_021/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_021/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_021/rectified_left.png

## Slide 51: Observed terrain atlas: 022–025

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_022/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_022/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_022/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_023/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_023/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_023/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_024/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_024/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_024/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_025/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_025/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_025/rectified_left.png

## Slide 52: Observed terrain atlas: 026–029

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_026/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_026/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_026/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_027/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_027/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_027/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_028/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_028/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_028/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_029/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_029/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_029/rectified_left.png

## Slide 53: Observed terrain atlas: 030–034

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_030/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_030/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_030/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_031/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_031/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_031/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_033/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_033/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_033/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_034/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_034/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_034/rectified_left.png

## Slide 54: Observed terrain atlas: 035–040

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_035/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_035/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_035/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_038/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_038/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_038/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_039/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_039/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_039/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_040/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_040/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_040/rectified_left.png

## Slide 55: Observed terrain atlas: 041–045

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_041/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_041/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_041/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_042/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_042/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_042/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_044/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_044/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_044/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_045/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_045/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_045/rectified_left.png

## Slide 56: Observed terrain atlas: 046–049

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_046/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_046/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_046/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_047/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_047/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_047/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_048/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_048/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_048/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_049/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_049/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_049/rectified_left.png

## Slide 57: Observed terrain atlas: 051–054

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_051/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_051/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_051/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_052/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_052/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_052/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_053/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_053/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_053/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_054/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_054/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_054/rectified_left.png

## Slide 58: Observed terrain atlas: 055–056

Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_055/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_055/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_055/rectified_left.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_056/local_mesh_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_056/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r11_filtered_batch/obs_056/rectified_left.png

## Slide 59: Registered groups: 003 / 005 / 010

These are the all-observed union OBJ meshes from r12, not completed terrain. The exported meshes and the voxel cloud counts describe different representations. Report distinct-view support rather than implying all voxels have multiple views. Each panel has its own full spatial extent and elevation color range.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_003/mesh_observed_union_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_003/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_005/mesh_observed_union_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_005/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_010/mesh_observed_union_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_010/metrics.json

## Slide 60: Registered groups: 029 / 044 / 051

These are the all-observed union OBJ meshes from r12, not completed terrain. The exported meshes and the voxel cloud counts describe different representations. Report distinct-view support rather than implying all voxels have multiple views. Each panel has its own full spatial extent and elevation color range.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_029/mesh_observed_union_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_029/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_044/mesh_observed_union_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_044/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_051/mesh_observed_union_calibration_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r12_registration/component_obs_051/metrics.json

## Slide 61: obs_003: all three completion settings

All three models are rendered from their respective saved OBJ exports. Strict input heights are unchanged. Filled hull-cell fraction and projected triangle area have different boundary conventions. Simulation fills the whole hull, regardless of nearest-support distance. These renders show the top surface only; closure is separate.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_003/completion_metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_003/terrain_balanced_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_003/terrain_extended_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_003/terrain_simulation_m.obj

## Slide 62: obs_029: all three completion settings

All three models are rendered from their respective saved OBJ exports. Strict input heights are unchanged. Filled hull-cell fraction and projected triangle area have different boundary conventions. Simulation fills the whole hull, regardless of nearest-support distance. These renders show the top surface only; closure is separate.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_029/completion_metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_029/terrain_balanced_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_029/terrain_extended_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_029/terrain_simulation_m.obj

## Slide 63: obs_034: all three completion settings

All three models are rendered from their respective saved OBJ exports. Strict input heights are unchanged. Filled hull-cell fraction and projected triangle area have different boundary conventions. Simulation fills the whole hull, regardless of nearest-support distance. These renders show the top surface only; closure is separate.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_034/completion_metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_034/terrain_balanced_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_034/terrain_extended_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/artifacts/runs/r15_terrain_completion/obs_034/terrain_simulation_m.obj

## Slide 64: stereo_trial_1: strict and relaxed diagnostics

The original fixed-rig camera gate failed for this generated pair. These diagnostic runs bypass that gate to reveal what dense matching does. No raw sensor images exist, so raw-quality masking cannot be applied. Meshes use arbitrary baseline=1 scale. Numerical filter acceptance does not validate the geometry.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/generated_stereo_trial/stereo_trial_1/diagnostic_strict/INVALID_GEOMETRY_mesh_baseline_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/generated_stereo_trial/stereo_trial_1/diagnostic_strict/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/generated_stereo_trial/stereo_trial_1/diagnostic_relaxed/INVALID_GEOMETRY_mesh_baseline_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/generated_stereo_trial/stereo_trial_1/diagnostic_relaxed/metrics.json

## Slide 65: stereo_trial_2: strict and relaxed diagnostics

The original fixed-rig camera gate failed for this generated pair. These diagnostic runs bypass that gate to reveal what dense matching does. No raw sensor images exist, so raw-quality masking cannot be applied. Meshes use arbitrary baseline=1 scale. Numerical filter acceptance does not validate the geometry.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/generated_stereo_trial/stereo_trial_2/diagnostic_strict/INVALID_GEOMETRY_mesh_baseline_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/generated_stereo_trial/stereo_trial_2/diagnostic_strict/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/generated_stereo_trial/stereo_trial_2/diagnostic_relaxed/INVALID_GEOMETRY_mesh_baseline_units.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/generated_stereo_trial/stereo_trial_2/diagnostic_relaxed/metrics.json

## Slide 66: more relaxed: both trials

Full saved OBJ geometry for both trials. No smoothing, outlier deletion, face decimation or geometric cropping. All panels retain independent full extents and arbitrary baseline units. Held-out disparity residual is computed only where held-out feature locations also survive dense acceptance; it is not a whole-surface 3D error. The row-adjusted family also changes the image alignment. Exact profile parameters are in the source metrics.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/more_relaxed/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/more_relaxed/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/more_relaxed/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/more_relaxed/metrics.json

## Slide 67: uber relaxed: both trials

Full saved OBJ geometry for both trials. No smoothing, outlier deletion, face decimation or geometric cropping. All panels retain independent full extents and arbitrary baseline units. Held-out disparity residual is computed only where held-out feature locations also survive dense acceptance; it is not a whole-surface 3D error. The row-adjusted family also changes the image alignment. Exact profile parameters are in the source metrics.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/uber_relaxed/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/uber_relaxed/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/uber_relaxed/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/uber_relaxed/metrics.json

## Slide 68: uber relaxed no checks: both trials

Full saved OBJ geometry for both trials. No smoothing, outlier deletion, face decimation or geometric cropping. All panels retain independent full extents and arbitrary baseline units. Held-out disparity residual is computed only where held-out feature locations also survive dense acceptance; it is not a whole-surface 3D error. The row-adjusted family also changes the image alignment. Exact profile parameters are in the source metrics.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/uber_relaxed_no_checks/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/uber_relaxed_no_checks/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/uber_relaxed_no_checks/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/uber_relaxed_no_checks/metrics.json

## Slide 69: uber relaxed wide window: both trials

Full saved OBJ geometry for both trials. No smoothing, outlier deletion, face decimation or geometric cropping. All panels retain independent full extents and arbitrary baseline units. Held-out disparity residual is computed only where held-out feature locations also survive dense acceptance; it is not a whole-surface 3D error. The row-adjusted family also changes the image alignment. Exact profile parameters are in the source metrics.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/uber_relaxed_wide_window/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/uber_relaxed_wide_window/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/uber_relaxed_wide_window/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/uber_relaxed_wide_window/metrics.json

## Slide 70: uber relaxed row adjusted: both trials

Full saved OBJ geometry for both trials. No smoothing, outlier deletion, face decimation or geometric cropping. All panels retain independent full extents and arbitrary baseline units. Held-out disparity residual is computed only where held-out feature locations also survive dense acceptance; it is not a whole-surface 3D error. The row-adjusted family also changes the image alignment. Exact profile parameters are in the source metrics.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/uber_relaxed_row_adjusted/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/uber_relaxed_row_adjusted/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/uber_relaxed_row_adjusted/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/uber_relaxed_row_adjusted/metrics.json

## Slide 71: row adjusted tighter: both trials

Full saved OBJ geometry for both trials. No smoothing, outlier deletion, face decimation or geometric cropping. All panels retain independent full extents and arbitrary baseline units. Held-out disparity residual is computed only where held-out feature locations also survive dense acceptance; it is not a whole-surface 3D error. The row-adjusted family also changes the image alignment. Exact profile parameters are in the source metrics.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/row_adjusted_tighter/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/row_adjusted_tighter/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/row_adjusted_tighter/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/row_adjusted_tighter/metrics.json

## Slide 72: row adjusted strict matching: both trials

Full saved OBJ geometry for both trials. No smoothing, outlier deletion, face decimation or geometric cropping. All panels retain independent full extents and arbitrary baseline units. Held-out disparity residual is computed only where held-out feature locations also survive dense acceptance; it is not a whole-surface 3D error. The row-adjusted family also changes the image alignment. Exact profile parameters are in the source metrics.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/row_adjusted_strict_matching/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_1/row_adjusted_strict_matching/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/row_adjusted_strict_matching/uber_relaxed.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/row_adjusted_strict_matching/metrics.json

## Slide 73: Trial 2: where relaxed matching accepts pixels

Trial 2 acceptance masks above, disparity below, for all seven sweep profiles. Percentages divide by the entire image. False sky correspondences and broad disparity plateaus should be inspected with the full geometry. Trial 2 row adjustment has only seven held-out feature matches, so its low residual on a few accepted matches provides limited evidence.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/stereo_trial_2/comparison.png
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/uber_relaxed/REPORT.md

## Slide 74: Estimated-pose control: 044 → 047

Actual saved terrain for baseline_unconditioned_eval. obs_044 to obs_047. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Video RMSE 4.90 cm vs matched IDW 0.77 cm / linear 0.85 cm; no demonstrated gain.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/baseline_unconditioned_eval/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/baseline_unconditioned_eval/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/baseline_unconditioned_eval_frames.png

## Slide 75: Depth-hole control: 0.5 m diameter

Actual saved terrain for disk_0.25. obs_033 to obs_034. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Video RMSE 8.06 cm vs matched IDW 2.48 cm; no demonstrated gain.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/disk_0.25/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/disk_0.25/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/disk_0.25_frames.png

## Slide 76: Depth-hole control: 1.0 m diameter

Actual saved terrain for disk_0.5. obs_033 to obs_034. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Video RMSE 7.37 cm vs matched IDW 4.02 cm; no demonstrated gain.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/disk_0.5/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/disk_0.5/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/disk_0.5_frames.png

## Slide 77: 044 → 047: seed 17, withhold 046

Actual saved terrain for holdout046_17. obs_044 to obs_047. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Video RMSE 7.58 cm vs matched IDW 3.72 cm; no demonstrated gain.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_17/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_17/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/holdout046_17_frames.png

## Slide 78: 044 → 047: seed 27, withhold 046

Actual saved terrain for holdout046_27. obs_044 to obs_047. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Video RMSE 8.61 cm vs matched IDW 3.81 cm; no demonstrated gain.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_27/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_27/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/holdout046_27_frames.png

## Slide 79: 044 → 047: seed 7, withhold 046

Actual saved terrain for holdout046_7. obs_044 to obs_047. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Video RMSE 7.16 cm vs matched IDW 3.78 cm; no demonstrated gain.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_7/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/holdout046_7_frames.png

## Slide 80: 044 → 047: three-seed consensus, withhold 046

Actual saved terrain for holdout046_model. obs_044 to obs_047. Three procedural seeds integrated; remaining holes receive linear interpolation. Video RMSE 8.45 cm vs matched IDW 3.52 cm / linear 1.25 cm; no demonstrated gain.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_model/terrain_top_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_model/metrics.json

## Slide 81: 045 → 048: seed 7, withhold 047

Actual saved terrain for holdout047_7. obs_045 to obs_048. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Only 4 reference cells scored; insufficient support for an accuracy conclusion.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout047_7/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout047_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/holdout047_7_frames.png

## Slide 82: Long-path sensitivity: 4.6 m / 15°

Actual saved terrain for long_7. obs_033 to obs_034. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Conditional model: no independent withheld-terrain error is available for this run.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/long_7/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/long_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/long_7_frames.png

## Slide 83: 044 → 048: seed 7, withhold 046

Actual saved terrain for longer046_7. obs_044 to obs_048. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Video RMSE 11.08 cm vs matched IDW 2.83 cm; no demonstrated gain.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/longer046_7/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/longer046_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/longer046_7_frames.png

## Slide 84: 4 m / 10° command prior: seed 17

Actual saved terrain for mid036_17. obs_033 to obs_034. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Conditional model: no independent withheld-terrain error is available for this run.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_17/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_17/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/mid036_17_frames.png

## Slide 85: 4 m / 10° command prior: seed 27

Actual saved terrain for mid036_27. obs_033 to obs_034. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Conditional model: no independent withheld-terrain error is available for this run.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_27/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_27/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/mid036_27_frames.png

## Slide 86: 4 m / 10° command prior: seed 7

Actual saved terrain for mid036_7. obs_033 to obs_034. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Conditional model: no independent withheld-terrain error is available for this run.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_7/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/mid036_7_frames.png

## Slide 87: 4 m / 10° command prior: integrated model

Actual saved terrain for mid036_model. obs_033 to obs_034. Three procedural seeds integrated; remaining holes receive linear interpolation. Conditional model: no independent withheld-terrain error is available for this run.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_model/terrain_top_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_model/metrics.json

## Slide 88: Short-path sensitivity: 3.4 m / 5°

Actual saved terrain for short_7. obs_033 to obs_034. Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface. Conditional model: no independent withheld-terrain error is available for this run.
All geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/short_7/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/short_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/detailed_progress_2026-11-10/figures/short_7_frames.png

## Slide 89: Video result ledger 1 / 2

Metrics transcribed directly from each run JSON. RMSE values in centimetres; each row uses its own scored cells. Rows differ in endpoint pair, support, pose protocol, resolution, spatial holdout and seed, so this table cannot rank video-generation methods. Dashes mean no corresponding independent metric, not zero error. All are procedural results.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/baseline_unconditioned_eval/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/disk_0.25/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/disk_0.5/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_17/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_27/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_model/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout047_7/metrics.json

## Slide 90: Video result ledger 2 / 2

Metrics transcribed directly from each run JSON. RMSE values in centimetres; each row uses its own scored cells. Rows differ in endpoint pair, support, pose protocol, resolution, spatial holdout and seed, so this table cannot rank video-generation methods. Dashes mean no corresponding independent metric, not zero error. All are procedural results.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/long_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/longer046_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_17/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_27/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_7/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_model/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/short_7/metrics.json

## Slide 91: Invalid temporal controls still export candidate meshes

These are real saved evaluator outputs for a frozen image repeated 33 times and a linear endpoint crossfade. Most visible mesh geometry comes from endpoint stereo; its presence must not be mistaken for video reconstruction success. Frozen has four added dense cells and zero sparse points; crossfade adds 49 cells. Only zero and one reference cells, respectively, are scored. Require negative-control rejection and explicit per-cell parallax before promoting candidate surfaces.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/collaboration_review/negative_controls_2026-11-09/frozen_first_endpoint/evaluation/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/collaboration_review/negative_controls_2026-11-09/frozen_first_endpoint/evaluation/metrics.json
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/collaboration_review/negative_controls_2026-11-09/linear_endpoint_crossfade/evaluation/candidate_stereo_plus_video_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/collaboration_review/negative_controls_2026-11-09/linear_endpoint_crossfade/evaluation/metrics.json

## Slide 92: Actual closed video-terrain models

Actual closed OBJ exports, showing sides and underside as part of each model. These are Matplotlib mesh renders, not Blender import validation. Closed meshes preserve the existing top and append an artificial base and vertical walls. Both have one connected component, consistent outward winding, and zero boundary or nonmanifold edges/vertices according to saved closure checks. Their upper surfaces still mix observed and inferred cells.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/holdout046_model/closed/terrain_closed_m.obj
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/chronological_video/mid036_model/closed/terrain_closed_m.obj

## Slide 93: What the results justify doing next

This is a work plan, not a record of completed experiments. Keep the professor’s request for more than ten methods as an explicit unfulfilled benchmark target. The colleague will return a ZIP from his GPU. No such learned-result ZIP has been evaluated at this snapshot. Fix acceptance controls and establish comparable evaluation before choosing a reconstruction model. Use actual mesh import screenshots and planner diagnostics for the simulation comparison. Image segmentation has proposals but no validated rock/crater prior yet.

Sources:
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/collaboration_review/2026-11-09/COMPARISON_FINDINGS.md
- C:/Users/rhunt/Documents/Capstone/reconstruction/output/collaboration_review/negative_controls_2026-11-09/FINDINGS.md

## Machine-readable full results

See atlas_manifest.json for exact per-run metrics, model SHA256 hashes, extents, input paths and render paths. See local_observation_results.csv for all 50 observations.
