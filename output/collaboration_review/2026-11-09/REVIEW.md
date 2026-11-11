# Independent review for the learned-video experiment

Reviewed 2026-11-09 against the local files whose SHA256 values appear in
`audit_results.json`. This is an addendum to `ASTRA_HANDOFF.md`, not a report on
the colleague's current remote work. Jarvis was not contacted. No implementation
files, experiment inputs, original outputs, or original handoff ZIP were changed.
The user has resumed this assistant's review role. Updated allocation: Astra owns
implementation and learned generation on the colleague's own GPU. Jarvis is
available to the user and this assistant for complementary work; its setup is no
longer a prerequisite for the colleague's experiment. Source-code ownership stays
separate to avoid concurrent edits. This supersedes the original ZIP's allocation.

## Decision

The saved procedural results are numerically reproducible and still show no
advantage over interpolation. Proceed with the controlled learned-video trial,
but resolve the comparison and provenance issues below before claiming success.
There are no learned outputs in this local result set to review yet.

## Verified from saved arrays and actual mesh files

| Result | Eligible/scored cells | Video RMSE | Linear RMSE | IDW RMSE |
|---|---:|---:|---:|---:|
| Procedural three-seed consensus, 044 to 047 | 561 / 85 | 8.450 cm | 1.250 cm | 3.518 cm |
| Procedural control with estimated poses and unconditioned frames | 561 / 21 | 4.900 cm | 0.854 cm | 0.766 cm |

Each row uses the same scored cells for its three methods. Rows use different
protocols and cell sets, so their errors must not be presented as a before/after
improvement. Coverage is 15.2% and 3.7%, respectively. In the second protocol,
the error before the 20 cm envelope filter is 60.295 cm across 47 cells. That raw
error is on a different set than the 21 retained cells and is already after
tracking/matching and disagreement rejection; it is not all unfiltered predictions.

- Integrated 044/047: all 8,385 strict stereo cell heights are exactly preserved.
- Integrated 033/034: all 9,872 strict stereo cell heights are exactly preserved.
  The source counts reproduce: 9,872 strict, 253 relaxed, 994 video, 8,888 linear.
  Video supports 250 of 2,375 cells outside both endpoint footprint hulls:
  0.625 square metres, or 10.5% of that grid region. This is a conditional footprint,
  not an independently surveyed area.
- Both closed OBJ files preserve the top OBJ vertices and faces exactly. The
  existing full topology validator passes on the on-disk geometry; an additional
  independent edge count confirms exactly two incident faces on every edge.
  These checks do not validate physical accuracy, self-intersection, or simulator
  collision behaviour. STL was not independently rechecked in this review.
- All listed files in the three schema-2 bundles match their manifest hashes.
  Every white-mask pixel is neutral RGB 128. The actual conditioned frame indices
  match the manifests: endpoints-only has 31 unconditioned frames; pose-anchors
  has 24. The 256-pixel smoke bundle also passes these input checks.
- Code inspection confirms that `pose_pair` excludes the heldout observation from
  the endpoint registration graph. `video_bridge.run` first loads heldout imagery
  after reconstruction/filtering. External evaluation reads the withheld terrain
  only after finalizing geometry. This is a code/data-flow review, not an instrumented
  replay proving that no external dependency can access heldout data.

## Recovered handoff evidence

The original ZIP includes `baseline_pose_check/metrics.json`, which lacks the
movie/bundle hashes recorded by the later evaluator. Its SHA256 does not match
the evaluation record. This was an evidence-packaging omission, not a reproduced
numerical failure.

The matching record was found at `tmp/baseline_pose_check_hashed`. Its exact metric
hash matches the evaluation, its movie and bundle hashes agree, and its selected
poses exactly equal the saved evaluation trajectory. Copies of its metrics and
pose array are now preserved under `evidence/baseline_pose_check_hashed/` in this
review package. They support the historical control only. Rerun pose checking for
each new video/bundle; do not reuse these poses to certify a learned output.

## Actions for Astra before interpreting learned results

### 1. Match the evaluated frame opportunity between conditioning modes

`evaluate_video.py:35-40` removes each bundle's own conditioned frames. Consequently
the endpoints-only run can use 31 frames while pose-anchor conditioning can use
24. Comparing their native pipelines alone mixes the effect of conditioning with
different frame selections and triangulation windows.

Keep the native results as an operational comparison, but add a controlled
comparison excluding the union of conditioned indices from both runs: for these
bundles, exclude 0,4,8,...,32. Report acceptance on the same remaining 24 frame
opportunities. For a geometry-only comparison, reconstruct both from their common
accepted indices and separately report lost coverage; do not hide failures by
reporting only the intersection. Compare terrain errors on an explicitly shared
cell set, alongside each method's full eligible/scored counts. If fewer than
eight usable frames remain, report insufficient pose support rather than relaxing
the gate silently.

### 2. Prevent mixed configurations and duplicate votes during integration

`video_integrate.py:20-25` checks at least three distinct seeds, generator name,
endpoints and pose metadata. It does not reject repeated seeds/paths or distinguish
learned modes, model revisions, resolutions and inference settings. The external
evaluator currently records only `generator='learned'` plus hashes, not a complete
experiment identity. Checking a hash exists is different from validating matching
settings behind that hash.

For example, seeds [7,7,17,27] pass the distinct-seed guard. A cell present only in
seed 7 then gets two votes when samples are counted at lines 65-72. Existing saved
results use exactly 7/17/27 and are not affected. This is a future integration risk.

Reject duplicate run paths, movie identities and seed identifiers; require exactly
three unique seeds for the current two-of-three policy, or explicitly redesign
and report the rule for larger ensembles. Record and enforce common conditioning
mode, model revision, steps, resolution/frame count, source data hashes and
evaluation settings. Allow the expected per-seed variation in videos, input anchor
renders and estimated intermediate poses. Never combine endpoints-only and
pose-anchor runs as seed replicates. Add meaningful rejection tests for these cases.

### 3. Complete the provenance chain before accepting external evaluation

`learned_video.generate` validates bundle payload hashes, but `video_pose_check`
reads the trajectory without checking those payload hashes. The evaluator checks
the movie and manifest hashes, but does not verify that the current trajectory
and source terrain arrays are the exact payloads referenced by that manifest.
The manifest's source hashes omit `surfaces.npz`, which determines the stereo
anchors, support envelope and baseline used by external evaluation. Nor does the
pose-check JSON bind its output `anchor_poses.npz` by hash. `--seed` and `--kind`
in evaluation are caller-supplied and not checked against `inference.json`.

Accidental file substitution can therefore pass parts of the existing checks.
Centralize bundle verification in preparation/generation/pose checking/evaluation;
hash the source surfaces and relevant endpoint data, and bind output pose arrays
and generated video to their metadata. Verify seed, generation method, model and
settings against inference metadata. Give procedural controls an explicit separate
route. Preserve old records as legacy rather than rewriting them to appear freshly
validated. New runs should carry the complete chain; rerun affected controls if
evaluation criteria change.

### 4. Treat missing anchor matches as a limitation of this evaluator

The current checker requires each accepted frame to match real endpoint stereo.
Frames fully inside an unseen gap may legitimately match neither endpoint. A
rejected frame means no accepted pose evidence under this method; it does not by
itself prove the generator produced impossible terrain. If this becomes the main
failure, an explicitly separate sequential SfM/visual-odometry experiment with
endpoint alignment and drift checks is the next method to test. Do not substitute
commanded poses or interpolate rejected poses in the current acceptance route.

## Return contract and review gates

Return a compact directory per conditioning mode and seed, containing:

1. Code revision or patch, exact commands and configuration, dependency/model
   versions, input manifest and hashes. Include hardware runtime, memory and failures.
2. Original generated frames/video and inference metadata; no endpoint replacement.
3. Pose-check metrics and poses bound to that video and input bundle, with conditioned
   and unconditioned counts and explicit rejection reasons.
4. Reconstruction arrays, raw-before-envelope and accepted errors, paired baseline
   errors, exact scored masks and eligible coverage. Report the 20 cm gate and any
   changes. A comparison against an IDW-based gate is conditioned on that prior.
5. If integrating: three unique matched-config seeds; exact strict-cell preservation;
   per-source labels; video support inside versus outside both endpoint footprints;
   actual mesh topology checks. Synthetic repeatability is not accuracy evidence.

Gate sequence: successful GPU execution -> accepted output poses -> usable terrain
coverage -> same-cell comparison with interpolation -> preserved stereo/provenance
and valid mesh export. Passing an earlier gate does not imply passing later ones.
No universal centimetre threshold is established here. Record worse results and
coverage losses; require evidence of benefit before promoting synthetic geometry.

The independent reviewer can review a first single-seed result before Astra spends
time on the three-seed batch. The nonregistered 033/034 case should retain explicit
XY/yaw uncertainty; current height refinement reaches its bound and does not solve
that uncertainty. No claim of unseen terrain accuracy can be validated there with
the current reference data alone.

## Reproduce this review

From the repository root:

```powershell
.\.venv\Scripts\python.exe output/collaboration_review/2026-11-09/audit_saved_results.py
```

The audit reads original data and writes only the review directory. Its saved
JSON contains source fingerprints and detailed checks. If Astra changes source
files, this report describes the earlier fingerprint, not the modified implementation.
