# Uber relaxed

## Findings

Simply relaxing thresholds produces more triangles but no convincing full terrain reconstruction. Removing almost all rejection creates long spikes, including geometry from the sky. Trial 1 improves materially after an empirical row correction; trial 2 has too few reliable correspondences to support a similarly strong conclusion. The meshes are open experimental surfaces, not closed simulator collision assets.

Coverage below is accepted disparity pixels divided by the entire 1024 x 1024 image, including sky; it is not terrain area, mesh area, or a claim that all those pixels survive triangle construction.

Experimental generated-stereo rule sweep. Existing production defaults and prior outputs are unchanged. The named admission gate is 16 matches, median row error <=30 px, and p90 <=60 px; both generated pairs are admitted. This affects acceptance only; it cannot make horizontal SGBM search different image rows.

## Sweep

| Pair | Profile | Whole-image coverage | Pass 2 px LR among accepted | Triangles | Largest connected component |
|---|---|---:|---:|---:|---:|
| stereo_trial_1 | more_relaxed | 19.0% | 98.5% | 7,104 | 5.1% |
| stereo_trial_1 | uber_relaxed | 30.1% | 88.4% | 28,197 | 40.3% |
| stereo_trial_1 | uber_relaxed_no_checks | 85.5% | 40.0% | 192,479 | 99.6% |
| stereo_trial_1 | uber_relaxed_wide_window | 60.7% | 36.3% | 126,686 | 94.3% |
| stereo_trial_1 | uber_relaxed_row_adjusted | 45.0% | 93.4% | 71,473 | 66.1% |
| stereo_trial_1 | row_adjusted_tighter | 25.1% | 100.0% | 5,397 | 5.1% |
| stereo_trial_1 | row_adjusted_strict_matching | 19.1% | 100.0% | 899 | 10.1% |
| stereo_trial_2 | more_relaxed | 16.6% | 98.3% | 6,419 | 4.4% |
| stereo_trial_2 | uber_relaxed | 24.5% | 88.9% | 19,615 | 27.1% |
| stereo_trial_2 | uber_relaxed_no_checks | 85.2% | 33.9% | 191,854 | 99.6% |
| stereo_trial_2 | uber_relaxed_wide_window | 59.1% | 30.9% | 121,324 | 93.6% |
| stereo_trial_2 | uber_relaxed_row_adjusted | 28.7% | 90.4% | 29,043 | 43.0% |
| stereo_trial_2 | row_adjusted_tighter | 8.8% | 100.0% | 8,254 | 13.6% |
| stereo_trial_2 | row_adjusted_strict_matching | 3.4% | 100.0% | 2,542 | 7.0% |

Previous diagnostic whole-image coverage: trial 1 strict 0.55%, relaxed 4.12%; trial 2 strict 0.61%, relaxed 4.00%. These runs already ignored the failed camera gate.

## What was relaxed

- Matching uniqueness: 15 originally, 5 relaxed, now 2 or 0. Speckle rejection is disabled in the five original sweep variants.
- Internal and external LR tolerance: originally 1 px, up to 16 px in uber relaxed. No-checks requests 512 px internally (the entire disparity search width) and removes the external check.
- Minimum disparity: 16 originally, 8 / 4 / 1 px. Near-zero positive disparity allows extremely distant geometry.
- Texture and brightness gates are progressively removed. Rectification overlap, valid correspondence image bounds, positive disparity and the SGBM search bound are retained.
- Mesh discontinuity limit: original 2%, now 10%, 50%, or effectively unlimited. Triangle edge limits increase from 0.25 baselines to 1, 10, or effectively unlimited.
- Wide-window variant uses 21 x 21 matching blocks. Larger blocks sacrifice local detail.
- Row-adjusted variant additionally fits a vertical affine correction to the right image using 80% of feature matches. The held-out 20% evaluates alignment and disparity independently of that fit. This is an empirical camera-model change, not merely a relaxed threshold.

The two additional row-adjusted follow-ups restore 1 px internal LR rejection, 1–2 px external LR rejection, uniqueness 5 or 15, speckle rejection, and mesh depth-jump limits of 5% or 2%. Both retain the lower 4 px minimum disparity and brightness >4, and do not restore saturation masking. The strict-matching name therefore does not mean every original production gate is restored.

## Geometry gate and held-out evidence

Original admission requires >=40 matches, median row error <=1 px and p90 <=2 px. The following measured thresholds are the minimum needed to admit each pair under the original camera model:

| Pair | Available gate matches | Required median allowance | Required p90 allowance |
|---|---:|---:|---:|
| stereo_trial_1 | 1313 | 8.06 px | 10.36 px |
| stereo_trial_2 | 19 | 26.61 px | 28.36 px |

### stereo_trial_1

Row correction used 1564 training matches and 392 held-out matches. Held-out median vertical error changed from 8.48 to 0.67 px; corrected p90 is 2.28 px.

| Profile | Accepted held-out matches | Median disparity disagreement | p90 disagreement |
|---|---:|---:|---:|
| more_relaxed | 68/392 | 100.66 px | 366.35 px |
| uber_relaxed | 104/392 | 81.70 px | 373.01 px |
| uber_relaxed_no_checks | 361/392 | 127.34 px | 379.69 px |
| uber_relaxed_wide_window | 200/392 | 485.65 px | 495.12 px |
| uber_relaxed_row_adjusted | 279/392 | 0.29 px | 0.88 px |
| row_adjusted_tighter | 257/392 | 0.24 px | 0.74 px |
| row_adjusted_strict_matching | 234/392 | 0.25 px | 0.68 px |

### stereo_trial_2

Row correction used 27 training matches and 7 held-out matches. Held-out median vertical error changed from 22.73 to 1.33 px; corrected p90 is 10.31 px.

| Profile | Accepted held-out matches | Median disparity disagreement | p90 disagreement |
|---|---:|---:|---:|
| more_relaxed | 3/7 | 95.17 px | 253.62 px |
| uber_relaxed | 4/7 | 174.27 px | 281.39 px |
| uber_relaxed_no_checks | 7/7 | 94.92 px | 269.54 px |
| uber_relaxed_wide_window | 5/7 | 212.06 px | 460.76 px |
| uber_relaxed_row_adjusted | 5/7 | 0.27 px | 163.35 px |
| row_adjusted_tighter | 3/7 | 0.14 px | 0.15 px |
| row_adjusted_strict_matching | 3/7 | 0.16 px | 0.24 px |

The held-out split applies to fitting the row warp, not unseen images. Disparity disagreement is evaluated only where each profile accepts a held-out feature, so low error with few retained features cannot establish accuracy across the full scene. These features are image correspondences, not measured 3D ground truth.

## Files and interpretation

Each profile contains `uber_relaxed.obj`, `terrain.mtl`, `texture.png`, arrays, validity and metrics. Keep the OBJ, MTL and PNG together for texture. Geometry uses arbitrary baseline units, NOT metres. No hole filling, manual geometry edits, outlier cropping or smoothing was used to make these mesh previews. A large connected component means a more connected mesh, not correct stereo depth. The consistency and feature checks use image agreement; no ground truth exists for these generated images.

See `comparison.png` for masks/disparities and `mesh_comparison.png` for full mesh geometry in each trial. The viewer ZIP contains all seven profiles for each trial (14 textured OBJ meshes).

Run: `python -m reconstruction.uber_relaxed --output output/uber_relaxed_new`. The input split images and reference features come from the existing generated-stereo experiment.
