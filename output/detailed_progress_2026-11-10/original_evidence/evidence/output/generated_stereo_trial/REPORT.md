# Generated stereo pipeline experiment

Both supplied canvases were split losslessly; separate 1024 x 1024 grayscale analysis copies were prepared. Resize assumes the requested field of view and does not establish actual generated camera intrinsics.

## Results

| Pair | Reciprocal matches | Median fixed CAHV error (px) | p90 (px) | Within 2 px | Pipeline |
|---|---:|---:|---:|---:|---|
| real_A | 73 | 0.45 | 0.90 | 98.6% | accepted |
| real_C | 40 | 0.70 | 1.46 | 92.5% | rejected |
| stereo_trial_1 | 1956 | 8.46 | 11.08 | 0.0% | rejected |
| stereo_trial_2 | 34 | 25.93 | 48.92 | 0.0% | rejected |

The table uses all reciprocal SIFT matches without fitted-camera prefiltering. The production gate uses its existing 8,000-feature lower-contrast SIFT + fitted-F outlier rejection, then requires at least 40 matches, median rectified row error <=1 px and p90 <=2 px. The real production controls check original raw counterparts, while the independent analysis uses calibrated imagery. Their counts therefore differ. Real C has reasonable median/p90 independent calibration residuals, but the actual pipeline rejects it with only 24 usable matches, below the 40-match minimum.

## Dense matching despite failed geometry

These separate diagnostic runs deliberately ignore the failed camera check, while reusing the production SGBM matcher and mesh builder. They do NOT change the production gate. Intensity and texture masks operate on generated pixels; no real raw sensor data exists for these outputs.

| Generated pair | Profile | Filter-accepted pixels | Fraction of whole image | Mesh triangles |
|---|---|---:|---:|---:|
| stereo_trial_1 | strict | 5,742 | 0.55% | 289 |
| stereo_trial_1 | relaxed | 43,178 | 4.12% | 2,334 |
| stereo_trial_2 | strict | 6,417 | 0.61% | 343 |
| stereo_trial_2 | relaxed | 41,904 | 4.00% | 2,381 |

Any OBJ under `diagnostic_*` is named `INVALID_GEOMETRY_mesh_baseline_units.obj`: arbitrary baseline = 1, not metres or millimetres. These are numerical failure-case artifacts, not usable reconstructed lunar terrain. They are intentionally not hole-filled, fused, or made into collision assets.

## Interpretation

These two saved outputs do not preserve the original Navcam camera relationship under the requested framing. More feature matches or a denser SGBM mask cannot fix that. A fitted alternate fundamental matrix is explored with held-out features in `results.json`, but does not establish intended camera pose, physical scale, or correct depth. A near-planar image warp can also fit many features without proving useful stereo parallax.

For a controlled synthetic stereo test, render both cameras from one shared 3D scene with known calibration and depth ground truth. Existing metre-scale terrain can provide that scene. Image generation may then be evaluated as appearance augmentation without silently replacing the camera geometry.

## Reproduction

Run `python -m reconstruction.generated_stereo_trial --package <original-package-directory> --output <new-workspace-output-directory>`. Run names must be new. Original images are hashed before/after and never modified. Native halves are byte-equivalent in decoded pixels to their original canvas regions. Calibration files are checked against the package copies. The output contains split images, actual pipeline acceptance/rejection results, geometry visualizations, dense disparity/masks/XYZ/OBJ diagnostics, and full JSON metrics.
