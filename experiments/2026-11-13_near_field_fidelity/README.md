# Near-field fidelity experiments (2026-11-13)

Branch: `feat/improve-reconstruction-fidelity`. This folder is self-contained. It does **not** modify the pipeline code under `reconstruction/` or any existing `artifacts/` run. (The project convention puts evaluation scripts in `lunar-reconstruction-evaluation`, so this folder can be moved there unchanged.)

Provenance labels used throughout: **measured** = production r08/r11 settings; **experimental** = ground-slanted matching and/or left-only shadow mask; Earth-data results are labelled with the dataset name. Nothing here is interpolated or synthetic, except the production fused grid, which is used only as a comparison.

## What was tested

1. **Reproduction.** Re-running SGBM on the r08 rectified pairs reproduces `disparity_left_px.npy` bit-for-bit. Recomputing the r08 masks and the r11 support filter reproduces both validity masks exactly for obs_044 (0 differing pixels), and recomputed fusion plus the 5 cm grid reproduces 9,573 observed cells.
2. **Near-field variants** (`variants.py`, `proposed.py`):
   - production (r08)
   - relaxed checks (uniqueness 5, speckle off)
   - half resolution
   - 3×3 and 9×9 blocks
   - ground-slanted windows
   - ground-slanted windows + left-only, undilated shadow/saturation mask

   For the slanted windows, a robust plane d = a·x + b·y + c is fitted to near-field disparities from the existing r08 pass (rows ≥ 600, so no SIFT is needed). The right image is warped by that plane, SGBM searches −64…+128 px of residual, and the exact back-mapping is d = d_g + r·(1 − a). The left-right check is done in the warped domain. The downstream r08 and r11 filters are applied unchanged.
3. **Accuracy checks.** SIFT matches are split odd/even (odd ones fit the prior in the SIFT-prior variant; even ones are held out). Cross-pair height agreement is measured on 5 cm cells seen by two pairs.
4. **Rock trace** (`trace2.py`, `rockfilters.py`). Three rocks: obs_044 (x 255–390, y 692–752), obs_047 (565–615, 840–885) and obs_048 (688–722, 622–650). Relief is measured above a local plane fitted to a surrounding ring.
5. **Fused grid** (`fuse_grid.py`, `crosspair.py`). Same r12 poses, the same 6 mm voxel fusion (stride 2) and the same 5 cm lattice. "Hybrid" = experimental matcher where the ground prior is ≥ 85 px (≤ ~4 m), production elsewhere.
6. **Earth data** (`polar_gt_pose.py`, `polar_eval.py`, `trav_eval.py`). NASA Ames POLAR datasets, downloaded Nov 13, 2026:
   - POLAR Stereo, Terrain03_MeanDistr: PosA and PosC at 1500 mm, rover lights off, four sun azimuths, one exposure per scene chosen for a near-field median closest to ~70 DN with ≤5% saturation. Ground truth comes from `GroundTruth_RectifiedRangeMaps`. That projection was recovered by DLT (exact fit: f 1991.49, cx 965.76, cy 599.85). SIFT-vs-lidar disparities still showed a 0.4–1.6 px affine offset, which was removed before scoring (SGBM is never used to fit it).
   - POLAR Traverse, View1: traverses 1/2 (1.3 m) and 4/5 (0.65 m), positions 2/4/6/8 m, rectified to 1024 px to match the NavCam scale. The rig's vertical misalignment against the shared calibration was 0.7–3.5 px; it was corrected per pair from SIFT before matching. Traverse lidar has not been used yet.

## Headline numbers

Ranges are across obs_044–048; "near" = bottom third, inside the left rectified image.

| | Production | Experimental (slanted + left-only mask) |
|---|---|---|
| Near: left-right-consistent depth | 8–20% | 38–52% |
| Near: after the r11 support filter | 0.2–5.6% | 34.6–48.0% |
| Whole image after r11 | 7.0–18.8% | 17.8–40.8% |
| Fused 5 cm cells observed within 2 m of a camera | 11.7% | 72.0% (hybrid) |
| Fused footprint observed | 31.0% | 36.9% (hybrid) |
| Cross-pair median \|dz\|, cells < 2 m | 4.0 mm (65 cells) | 2.2 mm (636 cells) |

Full per-observation values are in `results/`. Figures are in `figures/`.

## Corrections to the Nov 11 diagnosis (also listed in the reply notes)

- **Right-camera visibility.** Only 67–72% of the near field has its match inside the right rectified image (the left strip, where x < disparity + right-image edge, is never seen). The earlier "99.8%" figure doesn't hold under the ground-plane estimate, so it's worth re-checking how it was computed.
- **The 5 cm grid is not the largest rock-detail loss for 2–7 cm rocks.** They are lost at the r08 raw-information filter (68–93% of matched rock pixels) and then the r11 support filter.
- **Speckle/uniqueness are not the root cause.** Relaxing them raises returned disparities to 54–60%, but those values are mostly inconsistent (near-field LR error median up to 54 px), and only 0.5–7% survive the filters.
- **Stage percentages depend on the denominator.** Near-field "SGBM returns" is 12–28% when the denominator excludes the black rectification border, or 18–33% when it includes it.

## Reproduce

```bash
export LR_ROOT=/path/to/lunar-reconstruction NF_OUT=$PWD/results POLAR_DIR=~/Downloads/polar_eval
python scripts/make_sift.py
python scripts/variants.py r08,relaxed,half,half_relaxed,block3,block9   # writes variants_*.json
python scripts/variants.py r08,half,slant,slant_relaxed,slant_pass1,slant_pass1_relaxed
python scripts/proposed.py
python scripts/make_hybrid.py
python scripts/trace2.py; python scripts/fuse_grid.py; python scripts/crosspair.py   # trace2/fuse_grid import trace.py, which reads results/d_*_slant_pass1.npy from variants.py
python scripts/fig_funnel.py; python scripts/fig_images.py; python scripts/fig_map.py; python scripts/fig_earth.py; python scripts/fig_preskew.py
python scripts/polar_gt_pose.py && python scripts/polar_eval.py && python scripts/trav_eval.py
```

Requires numpy, opencv (with SIFT) and scipy. The scripts were run with OpenCV 5.0.0, NumPy 2.3 and SciPy 1.18. POLAR inputs are not committed: the extracted subsets live in a local `polar_eval/` folder (default `~/Downloads/polar_eval`, set `POLAR_DIR`) holding `sel2/`, `trav/`, the ground-truth maps and calibration.

Sources: https://ti.arc.nasa.gov/dataset/IRG_PolarDB/ (POLAR Stereo, Wong et al. 2017) and https://ti.arc.nasa.gov/dataset/PolarTrav/ (POLAR Traverse, Hansen, Wong & Fong 2024). Keep their attribution with any redistribution.
