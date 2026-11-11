# All observations superimposed on an approximate traverse

Open **all_observations_and_path.png** for the high-resolution figure. An SVG
version is also supplied. This is the requested approximate full-traverse scenario,
not a verified global reconstruction or a new production pose solution.

## What is shown

- All **56 project observations** appear as labelled positions. Nearby positions
  share one callout so the figure stays readable; their actual markers are retained.
- Colored terrain samples come from all **50 available accepted stereo reconstructions**.
  Up to 3,500 finite points per reconstruction are displayed at 0.4–11 m camera depth.
  Colors progress from early to late observations. The overlay shows observed
  stereo points, not filled meshes or newly inferred terrain.
- Hollow markers identify observations **015, 032, 036, 037, 043 and 050**, which have
  no accepted reconstruction in the current filtered batch.
- The dashed route integrates the documented turns and signed drives in SIS
  Appendix I, pp. 52–54, in an arbitrary planar coordinate frame.
- The six existing registered components retain their internal camera transforms.
  Their earliest observation anchors each component to the command-based map.
  This preserves local evidence without claiming globally registered groups.
- Asterisks identify **042, 043, 051, 052, 053 and 056**: their image-time counts do
  not match the number of NavCam checkpoints in the associated maneuver. All global
  placements are approximate; an asterisk identifies this additional ambiguity.

## How the full-traverse scenario was constructed

1. Transcribe the motion rows into signed rotations and translations: CCW positive,
   CW negative, reverse drives negative. Start at local origin with heading +X.
   This frame is not lunar north/east. Slope, slip and achieved motion are unknown.
2. Integrate movements in listed order. The initial ramp is projected horizontally;
   later motion is treated as planar. Rows with commanding issues and no executed
   movement do not create a separate maneuver.
3. Associate each image timestamp with the latest preceding mobility timestamp,
   under a common-time assumption. Archive filename suffixes are not treated as
   reliable pose IDs. An event without explicit imaging stages uses its final pose.
4. Where NavCam checkpoints are listed, assign distinct image times to checkpoints
   in order. When counts differ, this illustrative scenario uses the first checkpoint
   for one time, or evenly samples checkpoint indices for multiple times. These are
   explicit assumptions, not recovered synchronization or measured camera headings.
5. For registered groups, compose their saved relative transforms with the global
   anchor pose. Otherwise use the assumed rover pose and fixed camera calibration.
   Transform the real stereo samples into the illustrative frame and plot them.

## Document ambiguities preserved in the record

- MID 001 prints 23 August alongside DOY 236 (24 August). This scenario uses the
  calendar date, 23 August, at 19:06:36, to keep the first rollout between observations
  001 and 002. This is a documented interpretation, not a correction to the source.
- Later events use their day-of-year/time stamps. Inconsistent calendar dates for
  MID 038, 042 and 043 are not substituted for those stamps.
- MID 009's `2..754m` is interpreted as 2.754 m. MID 039's degree typography is
  interpreted as 70 degrees CW, not 700 degrees.
- MID 004 uses the Path column's 30 degree turn; the conflicting slip calculation
  mentioning 40 degrees and the 31.5 degree VO remark are not silently substituted.
- MID 012's second 1.758 m segment remains forward, as printed, even though the
  description says retrace. This is a material command-direction ambiguity that
  can affect the remainder of the integrated route.
- No extra 90 degree parking turn is added beyond the listed final imaging turns.

Because errors accumulate, the geometry may overlap incorrectly or appear offset.
Neither those overlaps nor the route shape validate the physical placement. This
figure should not be used for navigation, collision geometry, metric evaluation or
as ground truth for training. No global poses were installed into the main pipeline.

## Suggested caption

“Illustrative full-traverse overlay of all 56 observations, including 50 stereo
reconstructions. The route is integrated from documented rover commands, and views
are associated by timestamp. Image-registered groups retain their local alignment,
but global placement and some imaging stages remain uncertain.”

## Files and reproducibility

- `observation_placements.csv`: all 56 timestamps, associated mobility IDs, pose
  sources, ambiguity notes, assumed body poses and plotted camera positions.
- `command_route_xy_m.csv`: each segment endpoint of the plotted command route.
- `illustrative_camera_poses.npz`: 50 plotting transforms, explicitly separate from
  production reconstruction poses.
- `overlay_provenance.json`: complete command transcription, interpretation notes,
  per-observation records and source hashes.
- Source PDF: `chandrayaan-3-documentation/nav/document/ch3_nav_pds_dp_archive_sis.pdf`.
- Source observations: `chandrayaan-3-navcam-sorted/stereo_pairs.csv`.
- Source geometry and local registration: `artifacts/runs/r11_filtered_batch` and
  `artifacts/runs/r12_registration`.

Reproduce from the repository root using
`python -m review_tools.all_observations_overlay` in the reconstruction environment.
