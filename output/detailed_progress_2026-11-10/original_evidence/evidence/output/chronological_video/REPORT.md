# Chronological video reconstruction experiment

The procedural baseline now runs from real stereo endpoints through an estimated
camera trajectory, a synthetic monocular video, independent video reconstruction,
and integration with the original terrain pipeline. It produces closed OBJ/STL
surfaces, but has **not improved terrain accuracy over simple interpolation**.
Learned diffusion generation is a separate experiment currently being prepared;
none of the completed results below are MarsGen or Wan outputs.

## Results

| Experiment | Scored cells | Video height RMSE | Same-cell baseline RMSE |
|---|---:|---:|---:|
| 044 → 047, with 046 withheld, seed 7 | 143 / 561 | 7.16 cm | IDW 3.78 cm |
| 044 → 047, three-seed consensus | 85 / 561 | 8.45 cm | IDW 3.52 cm; linear 1.25 cm |
| 044 → 048, with 046 withheld | 210 / 763 | 11.08 cm | IDW 2.83 cm |
| Fixed-pose depth holes, 0.5 m diameter | 675 / 2377 | 8.06 cm | IDW 2.48 cm |
| Fixed-pose depth holes, 1.0 m diameter | 1245 / 3814 | 7.37 cm | IDW 4.02 cm |

The reference is real, independently reconstructed stereo transformed into the
working frame, **not surveyed ground truth**. Counts and errors only describe the
cells both methods can be compared on. A separate 045 → 048 test scored only four
cells and is too sparse to support an accuracy claim. The depth-hole tests keep
the input photographs and fix poses estimated before masking depths; they test
missing depth completion, not fully withheld observations.

The harder 033 → 034 bridge uses a documented 10° counterclockwise turn and 4 m
drive as a conditional motion prior. No successful image-feature registration
links these endpoints. Shared terrain constrains elevation and tilt conditional
on that assumed horizontal displacement and yaw. On 27 spatially withheld shared
cells, median disagreement falls from 47.9 cm to 4.4 cm. The fitted elevation
change reaches its permitted lower bound, so this is a constrained hypothesis,
not a recovered or externally verified rover pose. Perturbing motion to 3.4 m/5°
or 4.6 m/15° materially changes video support (1335 and 655 new cells respectively,
versus 1352 for the nominal single-seed run).

## Integrated terrain

The [033 → 034 closed OBJ](mid036_model/closed/terrain_closed_m.obj) and
[STL](mid036_model/closed/terrain_closed_m.stl) cover a roughly **49.98 m² convex
envelope**, in metres. Source labels remain available in the grid and vertex CSV:

- 9,872 strict stereo cells, unchanged exactly;
- 253 cells from the original gated relaxed stereo pipeline;
- 994 cells supported by agreement between at least two of three synthetic video runs;
- 8,888 cells filled by ordinary linear interpolation.

Of 2,375 grid cells outside both endpoint footprint hulls, 250 receive video
support: approximately **0.625 m² of a 5.94 m² between-footprint region**. The
remaining completion is interpolation. Cell areas use a 5 cm grid; these are not
surveyed physical areas or per-face area attribution. Most generated terrain is
not a new observation. Seed agreement measures repeatability, not correctness.

The OBJ and STL have one connected component, zero open boundary edges, zero
nonmanifold edges/vertices, and consistent outward winding. An artificial base
and walls close the model. These checks establish topological closure; they do
not establish flight readiness, collision quality in Gazebo, gravity alignment,
or accurate unseen geometry.

## Figures and videos

- [Video contact sheet](figures/video_contact_sheet.png): distinguish the real
  endpoints from procedural intermediate views. Rendering artifacts remain.
- [Terrain source map](figures/terrain_provenance.png): explain measured versus
  synthetic coverage; black outlines are endpoint footprint hulls.
- [Integrated upper surface](figures/terrain_surface.png): geometry preview with
  the same provenance colors. It does not show the artificial underside.
- [Withheld-observation error comparison](figures/heldout_error.png): the key
  result is that interpolation beats video reconstruction on the matched cells.
- [044 → 047 baseline video](holdout046_7/transition.mp4).
- [033 → 034 baseline video](mid036_7/transition.mp4).

## What is implemented

1. Real accepted stereo registration where available; a documented mobility prior
   for 033 → 034 where registration fails. There is no complete global rover pose track.
2. A fixed, textured heightfield seeded from endpoint stereo, with plausible
   stochastic relief in holes, rendered along 33 camera poses. This is a procedural
   hypothesis generator, not an AI video model or a recovery of unseen terrain.
3. Video-only three-view tracking/triangulation plus dense height-plane matching.
   Reconstruction receives decoded frames, camera intrinsics/poses and a support
   mask; it does not read the generator's depths. Appearance-only background
   pixels are excluded.
4. Conservative integration: strict stereo remains unchanged; video fills only
   unmeasured cells after an envelope gate and cross-seed agreement; remaining
   holes use the original interpolation method. Every source is labelled.
5. Whole-observation and fixed-pose depth-hole tests. The analytic software test
   recovered a textured plane with 6.7 mm tracking p90 height error and 20 mm dense
   p90 error. This verifies parts of the code, not real lunar accuracy.

## Learned-video comparison and remaining work

`reconstruction.learned_video prepare` creates portable, hashed input bundles:
real endpoints only versus real endpoints plus sparse procedural pose anchors.
VACE black masks mean conditioned regions; white masks mean generated regions.
Intermediate anchor support is restricted to the render's terrain support.
The same withheld observation must remain excluded from generation.

`reconstruction.video_pose_check` now estimates per-frame PnP poses from real
endpoint stereo features, with heldout feature checks and rejection when the two
anchors disagree. It keeps failed poses as NaN and reports conditioned versus
unconditioned frames separately. On the controlled 044 → 047 procedural video,
all 33 frames passed; among 24 unconditioned frames, the median difference from
the known rendering trajectory was 4.7 mm translation and 0.050° rotation
(maximum 17.6 mm and 0.125°). This is a software/control diagnostic, not a learned
video result or independent lunar pose validation.

The external-video evaluation route has also been exercised on that procedural
control: it reconstructs only those 24 unconditioned frames using the estimated
PnP poses, preserves all 8,385 strict stereo cells, and adds 638 candidate cells.
Only 21 cells overlap the withheld reference (3.7% coverage); on them video RMSE
is 4.90 cm versus 0.77 cm IDW and 0.85 cm linear interpolation. This small test is
not an accuracy success. It uses a different resolution and frame/pose selection
from the earlier table and must not be presented as an apples-to-apples improvement.
See `baseline_unconditioned_eval/metrics.json` for raw pre-filter errors too.

The proposed smaller backend is **Wan2.1 VACE 1.3B**, not the MarsGen lunar model
and not the 14B first/last-frame model. The optional inference adapter has not yet
been validated on a GPU. A successful video still needs camera-motion checking:
the supplied trajectory describes the commanded render, not necessarily the
camera motion achieved by the learned generator. Do not silently treat it as
measured output poses or fuse the result as real terrain.

Next: establish a compatible GPU environment, run a small inference, compare
endpoint-only and pose-anchor videos with the same seeds, evaluate output camera
consistency and heldout terrain errors, and require an accuracy/coverage benefit
over interpolation before promoting generated geometry. With no overlapping
features or verified relative pose, the bridge remains conditional even if it
looks convincing. Generalizing from the single documented mobility prior to the
whole traverse is still outstanding.

The [chronological interval inventory](chronological_catalog.json) covers 50
supported stereo observations and 49 adjacent intervals: seven have registered
poses with at least 5 cm translation, three have registered poses but too little
translation, one has the configured conditional mobility prior, 35 have no
relative pose in the current graph/prior catalog, and three share a timestamp.
This inventory does not assert that no additional priors could be extracted
from the archive; it identifies what the implementation can currently use.

## Reproduce

From the repository root with its existing reconstruction environment:

```powershell
$env:MPLCONFIGDIR='tmp/bridge_mpl'
python -m reconstruction.check_video_bridge
python -m reconstruction.video_bridge --start obs_044 --end obs_047 --holdout obs_046 --seed 7 --out output/chronological_video/new_holdout_7
# Repeat with seeds 17 and 27, then supply all three run directories:
python -m reconstruction.video_integrate output/chronological_video/holdout046_7 output/chronological_video/holdout046_17 output/chronological_video/holdout046_27 --out output/chronological_video/new_integrated
python -m reconstruction.video_bridge --start obs_033 --end obs_034 --seed 7 --out output/chronological_video/new_mid036_7
python -m reconstruction.video_bridge --start obs_033 --end obs_034 --holdout-radius .5 --out output/chronological_video/new_disk_05
python -m reconstruction.video_figures
python -m reconstruction.learned_video prepare --source output/chronological_video/holdout046_7 --mode endpoints_only --out output/chronological_video/new_endpoints_bundle
python -m reconstruction.learned_video prepare --source output/chronological_video/holdout046_7 --mode pose_anchors --out output/chronological_video/new_pose_bundle
```

Experiment directories must be new. Exact metrics are saved in each run's JSON.
Older development outputs in `tmp/chronological_video_development` are superseded.

Sources: [Wan repository](https://github.com/Wan-Video/Wan2.1),
[VACE interface and mask semantics](https://huggingface.co/docs/diffusers/api/pipelines/wan#diffusers.WanVACEPipeline),
[NVIDIA shared-memory explanation](https://docs.nvidia.com/cuda/cuda-for-tegra-appnote/index.html).
