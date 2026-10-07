# Terrain completion pilot — 5 October 2026

A three-scene experiment increased filtered stereo pixels by 14–39%. Gridding the geometry and interpolating missing cells produced 99.8–100% grid coverage inside the selected terrain footprints with a 50 cm maximum distance to supporting geometry. These are measured-plus-inferred surfaces for simulation. Hidden rocks and craters are not independently recovered.

## Recommendation and files

Start with [obs_034 extended terrain](artifacts/runs/r15_terrain_completion/obs_034/terrain_extended_m.obj), the best-supported of the three pilot scenes. Also available: [obs_029 extended terrain](artifacts/runs/r15_terrain_completion/obs_029/terrain_extended_m.obj) and [obs_029 continuous simulation terrain](artifacts/runs/r15_terrain_completion/obs_029/terrain_simulation_m.obj).

**New `terrain_*_m.obj` files are already in metres: use scale 1 1 1.** The inverse rectification and calibrated left camera center restore nominal rover-local axes, including the camera mounting tilt. Z is nominal rover-up, not independently measured gravity. The mm interpretation follows Iyer et al., LPSC 2024 abstract 1180, whose nominal baseline is 240 mm; the calibrated baseline remains 242.0594 mm. Do not scale these new files by 0.001 again.

The outputs are height surfaces, open at their outer perimeter, with no overhangs or enclosed volume. They have not been tested in Gazebo. All nine OBJ exports were parsed back and verified for finite vertices, valid indices, positive winding and nonzero triangle area.

## Method

The old mesh requires valid neighboring image pixels, <2% axial depth change and <60.5 mm edges. These rules fragment even otherwise plausible terrain. Shadows, saturation, stereo occlusion and weak texture create further gaps. The new experiment keeps the old results and performs:

1. Relax stereo matching: block width 5 → 7 pixels, uniqueness 15 → 5, left/right tolerance 1 → 2 pixels, texture standard deviation 2 → 1, speckle size 100 → 50. Relax support-filter median difference 2 → 3 pixels, neighbors 8 → 5 and minimum component size 200 → 50. Retain fixed-rig pair rejection and original raw-information masks.
2. Transform the geometry into metres and nominal rover-local coordinates. Grid the original strict data into 5 cm cells, requiring at least two points and taking median height. Crop to X = 0.75–6 m forward and Y = ±2 m; 5 cm spacing is not a 5 cm accuracy claim.
3. Preserve original occupied cell medians. Add relaxed stereo only in empty cells within 20 cm of original support, with height disagreement no greater than `0.04 m + tan(35 degrees) × support distance`. This screening envelope is a heuristic, not a statistical error bound or lunar slope law.
4. Fill between anchors using piecewise-linear Delaunay interpolation. It preserves planar trends and stays between supporting vertex heights, avoiding interpolation overshoot. Unlike mesh capping, it models one terrain elevation per horizontal location. It can still smooth away an unseen crater or rock.

| Mode | Maximum distance to nearest supporting cell | Intended use |
|---|---:|---|
| balanced | 25 cm | Restrained filling; larger gaps remain |
| extended | 50 cm | Preferred coverage/error compromise in this pilot |
| simulation | Unrestricted inside the support convex hull | Continuous assumed terrain |

No extrapolation occurs outside the support hull. Distance to nearest support is not a maximum hole diameter: long narrow gaps can qualify. A convex hull can bridge disconnected patches and occlusions. The farthest filled cell in this pilot was 56 cm from support.

## Coverage results

The coverage denominator is occupied grid cells inside each completed support convex hull within the crop. These percentages do not represent image pixels or the full scene.

| Scene | Original filtered pixels | Relaxed filtered pixels | Pixel gain | Original occupied grid | Balanced | Extended | Simulation |
|---|---:|---:|---:|---:|---:|---:|---:|
| obs_003 | 69,844 | 96,777 | 38.6% | 42.8% | 98.6% | 100% | 100% |
| obs_029 | 109,175 | 139,632 | 27.9% | 31.6% | 87.8% | 99.8% | 100% |
| obs_034 | 257,590 | 293,811 | 14.1% | 73.8% | 99.9% | 100% | 100% |

The terrain gate accepted 353 / 249 / 314 additional cells and rejected 43 / 152 / 72 candidate new cells respectively. Original occupied cell heights changed by exactly zero. Completed projected triangle areas are 8.45 / 9.98 / 10.70 m².

Sparse feature checks sampled only 15 / 25 / 12 newly accepted raw stereo pixels; their 95th-percentile disparity discrepancies were 0.69 / 0.68 / 0.66 pixels. These samples favor textured terrain. Common strict/relaxed depth changed by 0.44% / 0.31% / 0.30% at the 95th percentile, but rare larger outliers remained. The final terrain therefore retains original anchors and gates new ones.

## Error checks

Remove entire physical disks from original occupied cells, interpolate using only the remaining original cells, then compare with withheld heights. Relaxed stereo is excluded to prevent leakage. For each radius, test up to 16 seeded random centers plus a second set of 16 centers targeting local relief/outliers, spaced at least 30 cm apart. Patches may overlap, so sample counts are not independent. Predictions outside the training hull are excluded; recovery counts are recorded in `spatial_holdout.json`.

| Hidden disk diameter | Random-test 95th-percentile error across scenes | Relief-targeted 95th-percentile error across scenes |
|---|---:|---:|
| 10 cm | 0.65–1.06 cm | 1.46–3.02 cm |
| 25 cm | 0.82–1.48 cm | 1.75–3.36 cm |
| 50 cm | 1.17–1.95 cm | 2.13–2.78 cm |
| 1 m | 1.86–4.74 cm | 1.74–6.40 cm |

The largest difference was **14.77 cm**, in a relief-targeted 1 m patch of obs_029. Linear interpolation beat the tested 12-neighbor inverse-distance weighting in the random-test 95th percentiles. These results measure agreement with existing noisy reconstruction, **not absolute lunar accuracy**. Real missing regions disproportionately include shadowed rocks and crater walls. Their errors can exceed the tested values, and a smooth fill does not establish safe traversability.

Completed triangle slopes have 95th percentiles around 14–20 degrees, with maxima 49–70 degrees. Steep features may be real rocks or inherited stereo artifacts. No global 15-degree slope cap was imposed, since it would erase potential hazards. Slopes use nominal rover-up, not measured gravity.

`python -m reconstruction.check_completion` passed plane recovery across a disk, outside-hull rejection, camera-frame/mm-to-m conversion, OBJ readback, winding and area checks. Coverage and mesh renders were visually inspected. Original source imagery/calibration and earlier reconstructions were not modified.

## Artifacts and reproduction

- [Pilot metrics](artifacts/runs/r15_terrain_completion/summary.json)
- [obs_029 coverage and provenance map](artifacts/runs/r15_terrain_completion/obs_029/coverage_comparison.png)
- [obs_029 before/after mesh](artifacts/runs/r15_terrain_completion/obs_029/mesh_comparison.png)
- [obs_034 before/after mesh](artifacts/runs/r15_terrain_completion/obs_034/mesh_comparison.png)
- [Implementation](reconstruction/complete_terrain.py), [configuration](configs/completion.json), [geometric checks](reconstruction/check_completion.py)

Each observation folder also includes `terrain_grids.npz` (original, gated relaxed and completed heights, XY positions, support distances), `surface_labels.npy`, `completion_provenance.json`, `spatial_holdout.json`, and three OBJs. Labels are 0 outside, 1 original stereo median, 2 gated relaxed stereo median, 3 balanced-distance interpolation, 4 more distant interpolation. Labels indicate provenance, not calibrated probabilities.

```powershell
.\.venv\Scripts\python.exe -m reconstruction.complete_terrain --run my_completion_run
.\.venv\Scripts\python.exe -m reconstruction.check_completion
```

Use a new run name; the runner refuses overwrites. This is a three-scene pilot, not a replacement for all 50 frame meshes or six registered components. The relaxed stereo intermediates still use the legacy calibration-unit exporter; only `terrain_*_m.obj` and the terrain grids are converted products.

Next: test the obs_034 extended mesh in the simulator. For a larger environment, combine accepted views in their existing registration component before filling, so overlapping observations constrain more gaps. Broad regions with no observations should use explicitly synthetic rock/crater alternatives for robustness testing. Their feature placements cannot be uniquely reconstructed from missing data.

## Supporting sources

The [Ames Stereo Pipeline point2dem documentation](https://stereopipeline.readthedocs.io/en/stable/tools/point2dem.html) provides bounded DEM hole filling, while its [correlation guidance](https://stereopipeline.readthedocs.io/en/stable/correlation.html) describes larger support kernels for reducing holes. NASA's [DUST simulator](https://software.nasa.gov/software/MSC-27522-1) combines elevation data with representative crater/rock distributions. These support the approach, not this pilot's accuracy.
