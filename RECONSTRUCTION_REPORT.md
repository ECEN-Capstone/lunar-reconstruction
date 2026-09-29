# Lunar stereo reconstruction technical record

Executed 2026-09-29. Original imagery and metadata are read-only inputs. **Metric certification remains blocked by missing calibration-unit/frame and acquisition-motion evidence.**

The executed pipeline produced 50 support-filtered local point clouds (4,969,574 per-frame points), 50 partial local meshes, and six registered/fused components. Six candidate pairs were rejected. Seventeen of 129 tested registration links passed the stated checks; 31 frames remain singletons. These results preserve observed geometry and unknown regions, but do not meet the requested certified metric/simulator-ready milestone. Full configurations, results and failure cases follow.

## Initial investigation

The starting repository contains 224 PNGs, a 56-row candidate stereo manifest, 3 PDFs (two versions/copies of the archive SIS), 12 XML labels, 13 text files and 3 CSVs. There is no prior reconstruction code or experiment output in the working tree; Git history contains two data/documentation commits. No AGENTS.md was found.

The nested `chandrayaan-3-documentation/nav/document/ch3_nav_pds_dp_archive_sis.pdf` is readable. The top-level SIS has corrupt compressed streams and failed text extraction. The nested SIS is version 2.0, July 2024; it adds CAHV calibration, mobility, exposure and gain appendices. The quick guide and SIS establish NRL/NRR as raw and NCL/NCR as radiometrically calibrated products, correcting the uncertainty in the sorted archive README. `mob` is a rover mobility identifier, not a globally unique sequence number. Repeated mobility identifiers must not be paired without timestamps and station information.

Individual image XML labels are absent. Available XMLs describe the bundle, calibration and document collections. The SIS has one sample image label (obs_003 left). Its recorded size 538421 bytes and MD5 `981e24e50057fc4c1b5cc06196fe5550` exactly match the repository PNG, so the sample is useful evidence for that image: UTC start 2023-08-25T10:40:15.3807Z, selected frame 3, gain 2, integration 20 lines (7 ms). Its inclinometer fields have a different timestamp and undocumented attitude conventions; zero roll/pitch fields are not used as measured level terrain. It is not a complete pose stream. Appendix I contains commanded mobility summaries with slip and date inconsistencies, not measured per-image six-degree-of-freedom poses.

## Calibration cautions under investigation

CAHV centers are directly provided but their length unit and reference frame are not stated in the model text, XML labels, or Appendix H. No conversion to metres is currently authorized by evidence. Center separation will be retained in **calibration units**. Distortion parameters and covariance are unavailable. The supplied model is linear/pinhole; omission of distortion is a model limitation, not a measured zero distortion calibration.

Axis vectors have norms different from one despite the textual unit-vector definition. The literal Appendix H projection `u=H·(X-C)/(A·(X-C))`, `v=V·(X-C)/(A·(X-C))` is the baseline. Normalizing A alone changes the camera model and must be treated as a separate sensitivity experiment, never a silent correction.

Candidate left/right timestamps differ by approximately 30–43 seconds. The filename times are imaging start times, not simultaneous stereo timestamps. Applying fixed rig extrinsics requires an explicit stationary-rig assumption, to be assessed using image correspondences. Static-scene geometry alone cannot exclude translation along the baseline.

## Execution log

- Dependency setup: local `.venv` uses bundled Python 3.12 and existing NumPy/Pillow. Installing OpenCV, SciPy, Matplotlib and PyMuPDF required network permission after sandbox socket denial.
- Document extraction: pypdf failed on the top-level SIS but succeeded on the nested SIS; extracted text retained under `artifacts/investigation/`.

## Camera calibration and provenance

`L` and `R` below refer to `nav/calibration/ch3_nav_left_cahv.txt` and `ch3_nav_right_cahv.txt` under the documentation tree. All values apply to 1024 x 1024 imagery. Derived decimal precision is computational precision, not measurement accuracy.

| Parameter | Value | Units | Source / derivation | Status | Confidence / limitation |
|---|---|---|---|---|---|
| Left center C | (-14.75594, 124.24118, 326.07168) | Unspecified length | L | Directly supplied | Frame name and unit missing |
| Right center C | (-6.40296, -117.67110, 324.87617) | Same source length | R | Directly supplied | Requires common frame as intended by paired models |
| Baseline vector | (8.35298, -241.91228, -1.19551) | Source length | C_R - C_L | Derived | Applies only to stationary rig |
| Baseline length | 242.059399185 | Source length | Norm of baseline vector | Derived | Not certified millimetres or metres |
| Left A | (1, 0.004296, -0.165492) | Dimensionless | L | Directly supplied | Norm 1.013610407, contrary to unit-vector description |
| Right A | (1, 0.014939, -0.180854) | Dimensionless | R | Directly supplied | Norm 1.016332300 |
| Left H | (498.239481, -1416.743211, -77.511692) | Pixel projection coefficients | L | Directly supplied | Use with supplied A |
| Left V | (241.480345, 6.423157, -1480.974653) | Pixel projection coefficients | L | Directly supplied | Use with supplied A |
| Right H | (517.434318, -1416.421622, -104.037138) | Pixel projection coefficients | R | Directly supplied | Use with supplied A |
| Right V | (236.239929, 12.943905, -1489.032846) | Pixel projection coefficients | R | Directly supplied | Use with supplied A |
| Left fx, fy | 1399.793905, 1402.591882 | Pixels | RQ of [H;V;A], normalized K33 | Derived | Literal CAHV pinhole equivalent |
| Right fx, fy | 1401.170301, 1400.359769 | Pixels | Same method | Derived | Literal CAHV pinhole equivalent |
| Left cx, cy | 491.510356, 473.617410 | Pixels | Same method | Derived | No arbitrary image-center substitution |
| Right cx, cy | 498.668117, 489.607415 | Pixels | Same method | Derived | No arbitrary image-center substitution |
| Left/right skew | -9.132161 / 4.581818 | Pixels | Same method | Derived | Preserved by full projective homographies |
| Relative rotation and translation | Full matrices in `artifacts/investigation/calibration.json` | Rotation dimensionless; translation source length | Camera RQ and centers | Derived | Rig-local, not lunar-global pose |
| Rectified f | 1400.978964 | Pixels | Mean of four derived focal components | Derived virtual-camera setting | Does not replace physical calibration |
| Rectified principal point | (511.5, 511.5) | Pixels | Center of chosen virtual 1024-pixel canvas | Chosen output coordinate convention | Not claimed as measured physical principal point |
| Focal length | 21 | mm | SIS p.19 table 3 | Directly supplied nominal specification | Not used in place of CAHV |
| Pixel pitch | 15 x 15 | micrometres | SIS p.18 table 3 | Directly supplied nominal specification | 21 mm / 15 micrometres = 1400 pixels agrees approximately with CAHV |
| Sensor image size | 8.5 x 8.5 | mm | SIS p.19 table 3 | Directly supplied | Inconsistent with 1024 x 15 micrometres = 15.36 mm; not used |
| Distortion coefficients | None supplied | — | CAHV and associated XML | Unavailable | Linear model used as delivered; zero coefficients not claimed measured |
| Calibration covariance / error | None supplied | — | All calibration files | Unavailable | No absolute error bound can be certified |
| UTC acquisition start | Filename timestamps, 2023-08-23 through 2023-09-02 | UTC | SIS sample label and naming convention | Directly supplied, parsed | Four decimal places are fractional seconds; guide's “nanoseconds” wording is inconsistent |
| Left/right interval | 29.9602–43.2644; median 40.5689 | Seconds | Independently parsed manifest timestamps | Derived | Sorted-archive README's median 40.6892 is incorrect for these 56 rows; rig stationarity is assumed |
| Exposure and gain | Three candidate settings per product | ms, integration lines, gain setting | SIS Appendices J/K | Directly supplied documentary tables | Selected frame index generally absent without image XML |
| Per-image global pose / gravity direction | None available | — | Archive investigation | Unavailable | Commanded paths and intermittent attitude remarks cannot establish exact poses |
| Metric conversion | None established | Metres per source length unit | No unit statement located | Unavailable | If units are later confirmed mm, multiply all lengths by 0.001; this is conditional, not current calibration |

No learned depth, generated terrain, assumed 0.24-m baseline, or commanded rover translation was used to set scale.

## Dataset characterization

All 224 PNGs are 1024 x 1024, 8-bit monochrome (`L`), with no embedded metadata found by Pillow. The 56 rows provide four products each. There are 56 images in each camera/family directory. Image and metadata hashes, dimensions, clipping fractions, XML leaf fields and LUT statistics are recorded in `artifacts/investigation/inventory.json`.

Six radiometric LUTs each contain a finite 1024 x 1024 array. They are pixelwise gain, offset and gain-offset tables, not geometric distortion maps. SIS Appendix G prescribes subtracting offset, applying gain and gain-offset, and rescaling by ranges. A literal reapplication on obs_003 does **not** reproduce the NC products: clipping and flooring to uint8 gives mean absolute differences 6.885 DN (left) and 7.027 DN (right), while rounding gives 7.385 and 7.527 DN. Therefore the existing NC products were used directly; a raw-to-NC regeneration claim is unsupported without clarifying archive processing/quantization. Original raw pixels are retained to identify lost information. This experiment and independent filename/interval assertions are saved in `metadata_audit.json`.

Duplicate-pixel findings: both NC images of obs_025 equal their corresponding raw images exactly; the right images of obs_030 and obs_031 are identical within each family. Left/right exposure, repeated mobility IDs, missing selected-frame labels and same-time different-ID products preclude treating all 56 rows as independent acquisitions. `duplicate_pixels.json` preserves exact paths.

Representative full-archive contact sheet:

![Raw left images](artifacts/investigation/raw_left_contact_sheet.jpg)

The most saturated raw left frames are obs_015 (78.33% pixels >=250) and obs_032 (90.12%). Several frames have row discontinuities/black lines, large shadows, sky and glare. These are input defects or information limitations, not geometry to synthesize.

## Geometric methodology

For each camera form M=[H;V;A]. Project a scene point with `p ~ M(X-C)`. RQ decomposition gives the equivalent intrinsic matrix and world-to-camera rotation; normalizing the entire matrix preserves the ratios. Normalizing A alone changes those ratios and is tested separately.

The rectified x-axis is `(C_R-C_L)/B`; the forward z-axis is the mean camera-axis direction projected perpendicular to x; y=z cross x. Each source-to-rectified image homography is `K_rect R_rect inverse(M)`. This preserves the supplied skew and avoids silently passing a skewed camera through an API that expects zero skew. Image remapping uses bilinear interpolation. The shared camera centers differ only along rectified x, so disparity `d=u_left-u_right` gives `Z=f B/d`, `X=(u-cx) Z/f`, `Y=(v-cy) Z/f`. Z is axial depth, not Euclidean range or gravity-referenced terrain elevation.

Mutual SIFT matches pass a 0.75 descriptor ratio test; fundamental-matrix RANSAC rejects mismatches. Calibration validation measures vertical residuals after **fixed supplied-model** rectification. F is not used to replace calibration. The median of 56 pairwise median vertical errors is 0.515 pixels for the literal model versus 1.276 pixels for axis-only normalization. Low-match rows are unreliable diagnostics. Obs_043 has 1811 matches but median vertical error 30.96 pixels and p90 56.63 pixels: this candidate pair violates fixed-rig geometry and is rejected. It may contain mis-associated imagery or motion; the archive cannot resolve which.

The dense matcher is OpenCV StereoSGBM 3-way, with 5 x 5 blocks, P1=200 and P2=800, 1/16-pixel disparity storage, uniqueness rejection and speckle filtering. The reverse matcher uses the corresponding negative disparity range. Subpixel left/right checks sample right disparity at `u-d`; <=1 pixel disagreement is required. Raw clipping/shadow and local texture masks are applied explicitly. Comparisons cover raw, archived radiometric correction and CLAHE; original imagery is never overwritten.

The first 256-disparity experiment demonstrably truncates near terrain. The 512-disparity experiment pads both images horizontally by the search width, crops output back, and explicitly rejects coordinates without source support. This permits valid disparities near image borders without accepting padding as observed imagery. Small disparities amplify error; baseline cutoff is 4 pixels, wider-run cutoff 16, support-filtered cutoff 32. These are algorithmic operating ranges, not claimed physical near/far distances.

Final support filtering adds a 16-pixel source border, a 5 x 5 median-disparity agreement <=2 pixels, at least 8 initially valid neighbours in that window, and connected regions of at least 200 pixels. This is deliberately incomplete: isolated small real rocks and narrow terrain patches may be removed. No plane, smoothing surface or hole filling is imposed on retained XYZ coordinates.

Meshing connects only valid neighbours sampled every 3 pixels. Triangles spanning >2% axial-depth change or an edge >0.25 supplied baselines are rejected. This makes a discontinuity-aware local observed surface, not a watertight terrain model. Unobserved shadows, sky and gaps stay open. PLY and OBJ exports retain source length units.

## Registration and fusion methodology

Candidate temporal links span at most three manifest rows. In the full run, all-frame ORB appearance comparisons additionally propose each frame's top three revisits with at least 25 ratio-test matches. Retrieval only proposes pairs; the same stricter geometric checks apply. Rectified left-image SIFT matches with source stereo depth supply 3D-to-2D correspondences. A deterministic 20% subset is held out of pose fitting. PnP RANSAC followed by inlier LM refinement estimates an SE(3) transform. Acceptance requires at least 30 depth correspondences, 20 PnP inliers, 50% training inliers, held-out median <=2 pixels and p90 <=4 pixels, a >=120-pixel feature span in both axes, positive held-out depth, and at least 8 target-depth checks with median relative 3D discrepancy <=3%.

Target stereo depth is not used to fit PnP; it provides a separate consistency check, though shared calibration biases remain. Successful links define local components; disconnected views are never placed at arbitrary global positions. A traversal composes transforms into each component's first camera frame. Non-tree edges are retained as cycle diagnostics. This is local registration, not an optimized globally anchored SLAM trajectory.

Voxel fusion averages observations at spacing 0.025 times the source baseline (6.051485 source units). It records distinct-frame support and exports both all-observed and at-least-two-view clouds. Repeated same-view images can increase support without supplying independent geometry; support counts are not an accuracy certificate. No TSDF/Poisson hole filling is used because uncertain poses and severe holes would create unsupported surfaces.

## Numerical verification

Synthetic camera projection, homography, disparity and backprojection round trips passed: maximum vertical disagreement 5.68e-13 pixels and maximum 3D error 2.18e-11 source units. A textured synthetic stereo pair with known 24-pixel shift returned +24 left and -24 right disparities. These tests verify implementation conventions, not physical camera calibration or lunar accuracy.

## Accuracy interpretation and unresolved blockers

Subpixel match agreement is internal image consistency, not measured centimetre accuracy. No surveyed ground truth, measured calibration uncertainty or camera-unit statement is available. For small errors, `sigma_Z/Z approximately sigma_d/d`; at the final 32-pixel cutoff a hypothetical 0.5-pixel disparity error alone is 1.56%, before calibration, stationarity and matching biases. This is a sensitivity illustration, not an empirical uncertainty bound. Low left/right error can occur for incorrect repetitive-texture matches.

The 30–43-second stereo acquisition gap requires a stationary rig. Good epipolar agreement supports the orientation model but cannot detect extra motion exactly parallel to the baseline: such motion changes effective baseline and depth scale without changing epipolar lines. Provider telemetry or a stationary-acquisition guarantee is required to close that ambiguity.

**The requested fully defensible metric success criterion is not yet established.** The pipeline executes through PLY and local mesh, but absolute metre scale and gravity-referenced simulator placement remain blocked by missing unit/frame documentation and per-acquisition motion evidence. It would be scientifically incorrect to declare the output simulator-ready simply because OBJ imports successfully.

## References

- Local primary mission source: `chandrayaan-3-documentation/nav/document/ch3_nav_pds_dp_archive_sis.pdf`, v2.0, especially pp.18–19, 34–35, 44–48 and 50–61. Rendered pages 18, 19, 50 and 51 are preserved in investigation outputs; page 51 visually checked against extracted equations.
- Local quick user guide: `chandrayaan-3-documentation/ch3_nav_pds4_data_products_users_guide_v1_0.pdf`. Its example left/right row labels conflict with its explicit filename-code definition; camera codes and sample SIS image label are used.
- [ISRO PRADAN FAQ](https://pradan.issdc.gov.in/ch3/faq.xhtml): confirms UTC filename time interpretation.
- [PDS CAHV model definition](https://pds.nasa.gov/datastandards/documents/dd/v1/PDS4_PDS_DD_1O00/webhelp/all/ch34s05.html): camera model semantics.
- [OpenCV camera geometry](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html) and [StereoSGBM reference](https://docs.opencv.org/4.13.0/d2/d85/classcv_1_1StereoSGBM.html): algorithm/API references. Installed OpenCV version is recorded per run.

## Engineering handoff

What works: source inventory and integrity audit; literal CAHV rectification with image validation; raw and calibrated SGBM experiments; auditable disparity/depth/masks; source-unit point-cloud export; conservative local meshing; feature/depth-validated local camera registration and voxel fusion where overlap permits. Original imagery and calibration files are preserved.

What remains unsupported: absolute metre scale, acquisition-time effective baseline, global lunar position, gravity-referenced slopes, a complete connected rover trajectory, hidden terrain, continuous collision-ready mesh, and a demonstrated absolute accuracy bound. Mesh holes and uncertain areas must remain unknown space for planning, not be treated as flat traversable ground. A mesh import is not validation for rover navigation.

The next technically justified step is to obtain the instrument team's CAHV **length-unit and coordinate-frame declaration**, the per-product XML labels/selected-frame information, and a stationarity record or acquisition procedure for the separated left/right exposures. The instrument handbook referenced by the SIS is not present. Confirming these can establish whether the supplied centers legitimately support metric depth. An independently measured target or trusted terrain DEM is then needed to test absolute error. Obs_043 requires a pairing/identity investigation before triangulation. Dense calibration refinement should use original calibration observations or diverse validated scenes with held-out checks, not an arbitrary image warp chosen to look better.

For navigation simulation, resolve scale and gravity first, select a validated local component, then define how unknown regions constrain traversability. A continuous surface or global alignment should not be inferred solely to satisfy simulator file requirements.

No original source data were committed, redistributed, or modified. Generated artifacts remain local and ignored by Git; preserve `artifacts/` with this report when handing off the capstone.
<!-- GENERATED_RESULTS -->

## Executed experiments and measured results

All runs below were executed locally. A run directory is the authoritative record: configuration, inputs/hashes, coordinate convention, metrics and intermediate arrays remain together. Runtime metrics exclude some plotting/export overhead. Algorithmic consistency statistics are not ground-truth errors.

| Run | Input / change | Retained points | Coverage | Median SIFT disparity difference (px) | Conclusion |
|---|---|---:|---:|---:|---|
| [r01_raw_obs003](artifacts/runs/r01_raw_obs003/metrics.json) | obs_003 raw, 256 disparities | 123,115 | 11.74% | 0.207 | End-to-end raw baseline; near ground truncated, distant and border outliers. |
| [r02_calibrated_obs003](artifacts/runs/r02_calibrated_obs003/metrics.json) | obs_003 NC, same matcher | 148,250 | 14.14% | 0.191 | More initial support; raw clipping can be disguised by radiometry. |
| [r03_raw_clahe_obs003](artifacts/runs/r03_raw_clahe_obs003/metrics.json) | obs_003 raw + CLAHE | 129,904 | 12.39% | 0.213 | Small coverage gain; no demonstrated feature-error benefit. Not selected for final batch. |
| [r04_raw_obs029](artifacts/runs/r04_raw_obs029/metrics.json) | obs_029 raw, 256 disparities | 99,390 | 9.48% | 0.166 | Rock/terrain reference; same near-range truncation. |
| [r05_wide_raw_obs029](artifacts/runs/r05_wide_raw_obs029/metrics.json) | obs_029 raw, 512 disparities, padding, d>=16 | 134,544 | 12.83% | 0.168 | Recovers closer ground; source-border outliers remain. |
| [r06_wide_calibrated_obs029](artifacts/runs/r06_wide_calibrated_obs029/metrics.json) | obs_029 NC, same wider matcher | 163,945 | 15.64% | 0.158 | Improves feature agreement/support, but needs original-raw quality mask. |
| [r07_wide_raw_obs003](artifacts/runs/r07_wide_raw_obs003/metrics.json) | obs_003 raw, wider matcher | 144,717 | 13.80% | 0.204 | Complete raw pipeline with closer terrain; source-unit scale only. |

`r08_quality_batch`: 50 reconstructed, 6 rejected. Retained 6,523,972 per-frame points before support filtering; median per-frame coverage 12.82%. Median of per-frame SIFT disparity medians: 0.177 pixels. These totals contain overlapping observations and residual mismatches.

Rejected rows: obs_015, obs_032, obs_036, obs_037, obs_043, obs_050. Obs_043 fails rig geometry. The others lack sufficient reliable feature matches under glare/saturation/poor texture; this rejects available evidence, not necessarily the underlying physical pair.

`r11_filtered_batch`: 50 filtered point clouds and 50 local meshes, totaling 4,969,574 per-frame points and 508,095 triangles. Median coverage 10.03%. This is a collection of local observations, not the size of a unique global surface.

`r09_registration_pilot`: tested the first 12 unfiltered accepted frames, yielding local components {003,004}, {005,006}, {010,012}. Border/far outliers visible in all-observed fusion prompted final support filtering. Pilot retained for comparison.

`r10_filter_pilot_obs003`: removed isolated/border/depth-discontinuous support from obs_003; retained 69,844 points and 6,671 triangles. Inspected before filtering all 50 frames.

`r13_rejection_test_obs043`: deliberately attempted inconsistent raw pair through the standalone API; expected `ReconstructionRejected` was observed and no cloud was exported.

### Per-observation dense results

| Observation | Initial points | Final supported points | Final coverage | Local mesh faces | Initial SIFT comparisons | Initial median / p90 disparity discrepancy (px) |
|---|---:|---:|---:|---:|---:|---:|
| obs_001 | 30,228 | 18,045 | 1.72% | 1,856 | 159 | 0.257 / 0.730 |
| obs_002 | 25,327 | 14,890 | 1.42% | 503 | 14 | 0.331 / 0.467 |
| obs_003 | 99,934 | 69,844 | 6.66% | 6,671 | 75 | 0.203 / 0.642 |
| obs_004 | 127,472 | 100,634 | 9.60% | 10,995 | 89 | 0.177 / 0.466 |
| obs_005 | 188,387 | 155,546 | 14.83% | 16,038 | 35 | 0.117 / 0.349 |
| obs_006 | 117,624 | 85,296 | 8.13% | 7,595 | 19 | 0.102 / 0.254 |
| obs_007 | 90,092 | 61,289 | 5.84% | 6,732 | 17 | 0.147 / 0.352 |
| obs_008 | 64,600 | 36,778 | 3.51% | 4,546 | 66 | 0.202 / 0.657 |
| obs_009 | 125,376 | 107,405 | 10.24% | 12,662 | 116 | 0.156 / 0.430 |
| obs_010 | 208,190 | 181,768 | 17.33% | 16,879 | 109 | 0.201 / 0.443 |
| obs_011 | 61,403 | 27,707 | 2.64% | 2,617 | 33 | 0.173 / 0.608 |
| obs_012 | 156,028 | 136,851 | 13.05% | 11,229 | 174 | 0.200 / 0.545 |
| obs_013 | 124,319 | 103,023 | 9.83% | 6,868 | 68 | 0.171 / 0.425 |
| obs_014 | 131,230 | 109,123 | 10.41% | 7,664 | 74 | 0.139 / 0.421 |
| obs_016 | 43,050 | 11,562 | 1.10% | 1,168 | 16 | 0.171 / 1.412 |
| obs_017 | 213,383 | 167,836 | 16.01% | 18,065 | 115 | 0.223 / 0.611 |
| obs_018 | 145,338 | 108,384 | 10.34% | 10,370 | 62 | 0.171 / 0.385 |
| obs_019 | 222,166 | 187,766 | 17.91% | 19,105 | 142 | 0.210 / 0.694 |
| obs_020 | 154,227 | 107,236 | 10.23% | 9,639 | 61 | 0.187 / 0.495 |
| obs_021 | 127,437 | 79,716 | 7.60% | 7,104 | 66 | 0.159 / 0.340 |
| obs_022 | 137,654 | 85,894 | 8.19% | 5,540 | 57 | 0.165 / 0.508 |
| obs_023 | 162,606 | 122,017 | 11.64% | 8,791 | 60 | 0.222 / 0.529 |
| obs_024 | 118,171 | 72,020 | 6.87% | 6,128 | 78 | 0.201 / 0.534 |
| obs_025 | 141,266 | 100,072 | 9.54% | 9,140 | 55 | 0.185 / 0.549 |
| obs_026 | 99,240 | 68,614 | 6.54% | 5,622 | 50 | 0.165 / 0.457 |
| obs_027 | 178,298 | 143,195 | 13.66% | 17,012 | 138 | 0.158 / 0.437 |
| obs_028 | 189,926 | 164,417 | 15.68% | 20,367 | 126 | 0.198 / 0.509 |
| obs_029 | 126,396 | 109,175 | 10.41% | 15,729 | 132 | 0.154 / 0.454 |
| obs_030 | 169,284 | 146,589 | 13.98% | 18,694 | 182 | 0.157 / 0.418 |
| obs_031 | 172,819 | 150,684 | 14.37% | 19,242 | 177 | 0.161 / 0.404 |
| obs_033 | 164,258 | 116,766 | 11.14% | 13,213 | 104 | 0.152 / 0.478 |
| obs_034 | 289,122 | 257,590 | 24.57% | 31,359 | 155 | 0.168 / 0.408 |
| obs_035 | 161,602 | 142,576 | 13.60% | 20,479 | 98 | 0.182 / 0.398 |
| obs_038 | 24,381 | 15,770 | 1.50% | 1,636 | 27 | 0.215 / 0.510 |
| obs_039 | 31,608 | 23,207 | 2.21% | 2,961 | 40 | 0.231 / 0.470 |
| obs_040 | 77,024 | 65,423 | 6.24% | 8,622 | 82 | 0.178 / 0.458 |
| obs_041 | 138,596 | 124,936 | 11.91% | 21,854 | 157 | 0.175 / 0.408 |
| obs_042 | 80,838 | 44,993 | 4.29% | 2,634 | 27 | 0.210 / 0.501 |
| obs_044 | 169,290 | 124,564 | 11.88% | 8,764 | 69 | 0.130 / 0.592 |
| obs_045 | 96,678 | 66,899 | 6.38% | 4,646 | 96 | 0.183 / 0.410 |
| obs_046 | 168,888 | 122,839 | 11.71% | 10,825 | 35 | 0.158 / 0.679 |
| obs_047 | 228,349 | 178,900 | 17.06% | 19,653 | 111 | 0.189 / 0.545 |
| obs_048 | 122,418 | 99,196 | 9.46% | 11,794 | 178 | 0.179 / 0.487 |
| obs_049 | 107,824 | 50,421 | 4.81% | 3,559 | 39 | 0.217 / 0.454 |
| obs_051 | 171,806 | 130,791 | 12.47% | 8,447 | 63 | 0.184 / 0.544 |
| obs_052 | 146,310 | 102,259 | 9.75% | 7,219 | 64 | 0.176 / 0.381 |
| obs_053 | 168,937 | 122,953 | 11.73% | 9,385 | 81 | 0.136 / 0.518 |
| obs_054 | 53,956 | 20,653 | 1.97% | 1,789 | 10 | 0.164 / 0.379 |
| obs_055 | 29,469 | 9,666 | 0.92% | 683 | 37 | 0.185 / 0.577 |
| obs_056 | 141,147 | 115,796 | 11.04% | 14,002 | 85 | 0.171 / 0.449 |

Disparity comparisons use retained dense pixels coinciding with robust SIFT matches and <1-pixel fixed-model vertical residual. They are sparse checks selected for reliable texture, not unbiased tests over shadows or all terrain. Nearest-pixel sampling adds quantization relative to subpixel features. Final support filtering preserves retained XYZ values; it does not re-estimate disparity.

### Representative outputs

Raw milestone, preserved unchanged:

![Raw stereo baseline](artifacts/runs/r01_raw_obs003/diagnostics.png)

Final support-filtered terrain and rock observation:

![Filtered obs_029](artifacts/runs/r11_filtered_batch/obs_029/filtered_diagnostics.png)

Actual exported triangles read back from PLY; holes were not filled:

![Local mesh](artifacts/runs/r11_filtered_batch/obs_029/mesh_views.png)

Largest supported single-frame cloud:

![Filtered obs_034](artifacts/runs/r11_filtered_batch/obs_034/filtered_diagnostics.png)

[Obs_034 point cloud](artifacts/runs/r11_filtered_batch/obs_034/points_calibration_units.ply) and [observed-surface mesh](artifacts/runs/r11_filtered_batch/obs_034/local_mesh_calibration_units.obj).

### Final registration and fusion

`r12_registration`: tested 129 temporal/retrieval links among 50 filtered frames; accepted 17. Found 6 multi-frame components and 31 singletons. No transform is invented between disconnected components.

| Accepted link | Held-out count | Held-out median / p90 (px) | Target depth checks | Median relative 3D difference |
|---|---:|---:|---:|---:|
| obs_003 -> obs_004 | 53 | 0.460 / 0.631 | 140 | 0.04% |
| obs_005 -> obs_006 | 7 | 0.361 / 0.926 | 8 | 0.24% |
| obs_010 -> obs_012 | 22 | 0.287 / 0.607 | 102 | 0.62% |
| obs_012 -> obs_013 | 15 | 0.377 / 0.885 | 64 | 1.00% |
| obs_012 -> obs_014 | 10 | 0.314 / 0.539 | 44 | 1.18% |
| obs_013 -> obs_014 | 63 | 0.414 / 0.593 | 221 | 0.05% |
| obs_029 -> obs_030 | 8 | 0.635 / 0.891 | 33 | 0.75% |
| obs_029 -> obs_031 | 8 | 0.471 / 0.717 | 34 | 0.85% |
| obs_030 -> obs_031 | 111 | 0.389 / 0.552 | 543 | 0.00% |
| obs_044 -> obs_046 | 10 | 0.692 / 0.913 | 21 | 0.58% |
| obs_044 -> obs_047 | 11 | 0.489 / 0.761 | 43 | 1.85% |
| obs_045 -> obs_048 | 13 | 0.490 / 0.730 | 50 | 1.96% |
| obs_046 -> obs_047 | 9 | 0.386 / 0.655 | 37 | 0.66% |
| obs_047 -> obs_048 | 9 | 0.668 / 2.010 | 39 | 0.40% |
| obs_051 -> obs_052 | 28 | 0.491 / 0.735 | 31 | 0.22% |
| obs_051 -> obs_053 | 29 | 0.378 / 0.866 | 36 | 0.21% |
| obs_052 -> obs_053 | 50 | 0.349 / 0.530 | 216 | 0.02% |

| Component frames | Fused all-observed voxels | Voxels with >=2 frame support |
|---|---:|---:|
| obs_003, obs_004 | 24,019 | 6,234 |
| obs_005, obs_006 | 55,830 | 3,895 |
| obs_010, obs_012, obs_014, obs_013 | 90,954 | 8,659 |
| obs_029, obs_031, obs_030 | 51,544 | 21,591 |
| obs_044, obs_047, obs_046, obs_048, obs_045 | 136,699 | 2,277 |
| obs_051, obs_053, obs_052 | 67,831 | 11,134 |

Maximum composed-edge cycle disagreement: 0.0834 degrees and 3.808 source length units. Tree edges are included and trivially close; non-tree edges are the useful checks. No global accuracy claim follows from small cycle residuals.

Representative fusion in the obs_029 component:

![Local fusion](artifacts/runs/r12_registration/component_obs_029/fusion_views.png)

[Multi-view supported cloud](artifacts/runs/r12_registration/component_obs_029/cloud_multiview_supported_calibration_units.ply); [camera trajectory](artifacts/runs/r12_registration/component_obs_029/camera_trajectory.json).

### Registered observed-surface meshes

Exported 6 component meshes by transforming existing observed triangles into each component frame. No surfaces are added between observations. These triangle unions retain overlapping faces and open boundaries; they are not watertight collision geometry.

| Component | Vertices | Observed triangles |
|---|---:|---:|
| [component_obs_003](artifacts/runs/r12_registration/component_obs_003/mesh_observed_union_calibration_units.obj) | 19,005 | 17,666 |
| [component_obs_005](artifacts/runs/r12_registration/component_obs_005/mesh_observed_union_calibration_units.obj) | 26,772 | 23,633 |
| [component_obs_010](artifacts/runs/r12_registration/component_obs_010/mesh_observed_union_calibration_units.obj) | 59,024 | 42,640 |
| [component_obs_029](artifacts/runs/r12_registration/component_obs_029/mesh_observed_union_calibration_units.obj) | 45,244 | 53,665 |
| [component_obs_044](artifacts/runs/r12_registration/component_obs_044/mesh_observed_union_calibration_units.obj) | 65,792 | 55,682 |
| [component_obs_051](artifacts/runs/r12_registration/component_obs_051/mesh_observed_union_calibration_units.obj) | 39,531 | 25,051 |

The largest assembled mesh is shown below. Its broad holes and incomplete coverage are real limitations, not missing visualization effects.

![Registered observed mesh](artifacts/runs/r12_registration/component_obs_044/mesh_views.png)

### Final validation

Read back 118 PLY exports, checking exact vertex/face counts, finite XYZ, index bounds and file length. Representative meshes additionally have positive triangle areas and were visually rendered from the exported data. Rehashed all 255 original input files: 0 changed. Numerical geometry tests and expected rejection test passed. `pip check` reported no broken requirements.

`r14_baseline_reproduction`: reran the full raw obs_003 pipeline after implementation updates. Left/right disparity, depth and XYZ arrays were exactly equal to r01, including invalid-value locations. See `artifacts/investigation/reproducibility.json`.

