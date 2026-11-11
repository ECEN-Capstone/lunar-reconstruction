# Where the paths and poses come from

The project has **two ways to place reconstructions relative to each other**:
image-based registration when common features exist, and a conditional movement
prior when registration fails. Neither provides a complete measured rover trajectory.

## Recommended figures

| Figure | Purpose | Suggested explanation |
|---|---|---|
| `01_documentation_to_pose.png` | Show the evidence chain and original archive row | “Image timestamps bracket a documented maneuver. We use that maneuver to propose a relative placement.” |
| `02_pose_evidence_routes.png` | Separate image estimates from documentary assumptions | “Overlapping images support a fitted pose; an unregistered gap depends on a movement prior.” |
| `03_reconstructions_with_rover_path.png` | Large spatial figure of the two real reconstructions | “Blue and orange are reconstructed stereo observations. The dashed route shows the assumed rover motion linking the viewing positions.” |
| `04_spatial_plan_view.png` | Read distances and footprint overlap clearly | “The rover travels between viewing sites. The terrain patches lie ahead of those sites, so their footprints need not be separated.” |
| `05_completed_terrain_with_rover_path.png` | Show the existing completed surface as context | “Gray triangles contain non-strict/inferred vertices from the existing completion. They are not additional observations.” |

Use figure 03 for the requested main spatial illustration. Use figure 05 only when
also explaining hole filling. PNGs are high resolution; SVG versions are supplied
for figures 01, 02 and 04. Source imagery in the insets is real rectified imagery.

## Worked example: observations 033 and 034

The relevant document is the **revised** NavCam archive SIS at
`chandrayaan-3-documentation/nav/document/ch3_nav_pds_dp_archive_sis.pdf`.
Appendix I, **page 53**, lists MID 036 at `31.08.2023 / 243:12:20:00` with the
path **“10deg CCW, 4m.”** Its description also lists 1 m at 0.5 cm/s and 3 m at
1 cm/s. This is a mobility summary, not a frame-by-frame achieved pose log.

The image provenance records give:

| Project observation | Left-image timestamp | Archive sequence suffix |
|---|---|---|
| obs_033 | 31 August 2023, 08:13:01.9172 | 036 |
| obs_034 | 31 August 2023, 13:04:31.6922 | 037 |

The maneuver timestamp lies between the images under the pipeline's common-time
interpretation. The implementation assumes these endpoints bracket the complete
turn-then-drive event. Project observation numbers, file sequence suffixes and
mobility IDs are distinct identifiers; matching their numbers alone is insufficient.
The mobility table itself does not supply synchronized camera poses or resolve all
timing/achieved-motion uncertainty.

We choose the first rover-local frame as the coordinate reference and assume
initial forward direction +X. A positive 10 degree turn is counterclockwise in
the nominal XY plane. The ideal horizontal endpoint is therefore:

```
x = 4 cos(10 degrees) = 3.939 m
y = 4 sin(10 degrees) = 0.695 m
```

The endpoint stereo data then constrain a **conditional height/tilt adjustment**.
The saved fit applies +0.409 m elevation and a two-axis tilt rotation vector of
approximately (-2.87, -0.91) degrees. These are fit parameters, not measured rover
pitch and roll. The nominal fit's median residual is 4.39 cm over 27 spatially
withheld shared cells; the elevation reaches its permitted lower bound. Horizontal
translation and yaw were assumed, not solved by this height agreement.

The camera's fixed position and orientation relative to the rover are handled
using the calibration and rectification transforms. Thus the endpoint camera
centers are slightly offset from the idealized rover reference positions. In the
large figures, the dashed route is explicitly the **idealized rover reference
path**, with Z interpolated from the fitted elevation change. It is not a measured
wheel track, camera-center trajectory or surveyed ground profile.

## When images overlap: the 044-to-047 example

The accepted direct registration uses 135 feature matches, 55 depth correspondences
and 44 PnP inliers. Eleven held-out image matches have 0.489 px median and 0.761 px
90th-percentile reprojection error. The saved endpoint camera displacement is
approximately 0.890 m. These are image-based relative-pose checks, not absolute
lunar position measurements. The exact record is in
`artifacts/runs/r12_registration/registration_edges.json`.

The registration graph can combine accepted relative transforms when a direct edge
is unavailable; the current path selection minimizes summed held-out pixel residual.
For the 044-to-047 experiment, the accepted edge is direct. The held-out observation
046 is excluded from the input endpoint pose path and used later for terrain evaluation.

## What is modeled between the endpoints

The pipeline samples 33 intermediate camera poses. Registered endpoints use linear
position interpolation and rotation interpolation. The conditional mobility case
uses a turn-then-drive schedule, allocating the first 20% of synthetic progress
to the turn. This timing is a modeling choice; it does not reproduce the real
speeds listed in the archive row or the hours between camera timestamps.

Generated-video camera motion must subsequently be estimated and checked from
the generated frames. The prescribed path is not evidence that the generator
actually followed it. The figures here show the existing pose hypothesis and
real stereo reconstructions, not results from the colleague's learned-video run.

## Limitations to mention aloud

- The 033-to-034 spatial arrangement is conditional on the documented maneuver
  being associated correctly with these images and approximately achieved.
- Wheel slip, achieved heading, and global gravity alignment remain unverified.
- Camera calibration describes the viewing geometry; it is not a rover pose history.
- The figures retain the project's existing calibration-unit-to-metre factor of
  0.001. Appendix H explains CAHV; it does not independently certify that scale here.
- In a separate illustrative sensitivity study, changing assumed distance/turn
  can move terrain by about a metre even when conditional height fits pass. Those
  scenario ranges are not measured uncertainty bounds.
- Closed or visually complete terrain is not proof of accurate unseen geometry.

## Source and reproducibility record

- Revised SIS: Appendix H, p. 51 (camera model); Appendix I, p. 53 (MID 036).
- `artifacts/runs/r11_filtered_batch/obs_033/provenance.json` and the corresponding
  obs_034 file: image IDs, timestamps, camera/rectification data.
- `configs/video_mobility_priors.json`: selected maneuver and ordering assumptions.
- `reconstruction/video_bridge.py`: endpoint transform composition and trajectory.
- `reconstruction/video_pose.py`: conditional height/tilt fit.
- `output/chronological_video/mid036_7/trajectory.npz` and `metrics.json`: displayed poses.
- Original observed meshes and depth arrays under `r11_filtered_batch`: blue/orange geometry.
- `output/chronological_video/mid036_model/terrain_top_m.obj` and `integrated_grid.npz`:
  existing completed surface and provenance, used only in figure 05.

`figure_provenance.json` records input SHA256 values, endpoint camera transforms
and display details. `assumed_rover_reference_path_m.csv` contains the plotted route.
Reproduce with `python -m review_tools.pose_explanation_figures` in the existing
reconstruction environment. No source meshes, poses or pipeline settings were changed.
