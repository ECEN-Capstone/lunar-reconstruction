# Independent terrain review tools

Owned by the independent reviewer. These tools read saved arrays and write new
review outputs; they do not modify Astra's reconstruction or GPU implementation.

## Compare returned results

Use a source experiment with `surfaces.npz`, `validation.npz` and `metrics.json` as
the fixed reference. Supply candidates with `surfaces.npz` (external evaluation or
procedural run) or `integrated_grid.npz` (fused terrain), plus `metrics.json`.
Coordinates, strict heights, source labels and endpoint pose scenarios must agree.
The original 044/047 reference is `output/chronological_video/holdout046_7`.

```powershell
.\.venv\Scripts\python.exe -m review_tools.compare_terrain `
  --reference-run output/chronological_video/holdout046_7 `
  --runs output/chronological_video/holdout046_model output/chronological_video/baseline_unconditioned_eval `
  --labels "Three-seed procedural consensus" "Estimated-pose procedural control" `
  --out output/collaboration_review/new_comparison
```

The output directory must not already exist. Outputs: `comparison.json`,
`comparison.csv`, `comparison.png`, and exact `scored_masks.npz` arrays. JSON
contains input and reviewer SHA256 fingerprints. Directory names must be unique.

The report distinguishes:

- Native accepted-video coverage and video/baseline errors on each candidate's cells.
- Video errors on the intersection of all candidates' support, alongside baselines
  on exactly those cells. Empty overlap produces null errors, not a zero error.
- A fixed-region diagnostic that uses each candidate's accepted video and ordinary
  linear interpolation everywhere else. This scores completion quality across all
  comparable reference cells and avoids rewarding omission of difficult terrain.
  It is a computed diagnostic, not a newly exported or simulator-tested mesh.

All baselines come from the same strict endpoint stereo. Any relaxed observed
cells across the candidates are excluded from the common/fixed comparison so
they cannot be counted as video recovery. This may differ from an integrated
run's original baseline, which can use relaxed observations.

These are terrain checks, not an inference-certification tool. Check the ZIP's
generation, pose and source metadata separately. A same-cell comparison does not
remove differences in frame selection, resolution or reconstruction protocol.
Failed/missing runs must be listed explicitly rather than omitted. See the review
addendum for matched-frame and hash-chain requirements.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest review_tools.test_compare_terrain -v
```

Tests use analytic terrain with known errors, disjoint/empty coverage and malformed
inputs. They require no mission imagery, GPU or reconstruction code imports.

## Incoming ZIP review

The user will supply the colleague's results as a ZIP. Preserve its original bytes
and record its SHA256. Inspect its names and contents before extracting into a new
directory; do not overwrite existing runs or execute bundled scripts automatically.
Confirm which code revision/settings produced the outputs and record missing or
failed jobs. Apply the requirements in
`output/collaboration_review/2026-11-09/REVIEW.md` before treating a result as a
learned reconstruction. Review a first seed before requesting the larger batch.
