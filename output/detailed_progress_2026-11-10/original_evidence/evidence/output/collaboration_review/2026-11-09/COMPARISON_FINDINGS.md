# Fixed-region completion comparison

2026-11-09. This is independent review of existing procedural outputs, not a new
learned-video result. No changes were made to the generation or reconstruction
implementation. The colleague's learned results will arrive as a ZIP.

## New finding

Using video where it is accepted and linear interpolation elsewhere does not
improve the current completed terrain on the 561 reference cells. The fixed
strict-stereo linear baseline has 1.052 cm RMSE; IDW has 2.494 cm RMSE.

| Procedural result | Accepted video reference cells | Video + linear fallback RMSE, all 561 cells | Cells improved / worsened versus linear |
|---|---:|---:|---:|
| Seed 7, original rendered-pose protocol | 143 (25.5%) | 3.710 cm | 20 / 123 |
| Three-seed consensus | 85 (15.2%) | 3.419 cm | 12 / 73 |
| Estimated-pose, unconditioned-frame control | 21 (3.7%) | 1.407 cm | 4 / 17 |

Remaining cells retain the linear baseline exactly. This diagnostic does not
export a new mesh. Its reference is registered withheld observation 046, not
survey ground truth. It evaluates holes visible in that observation and cannot
establish accuracy in regions unobserved by all real imagery.

Only 12 cells have video support in all three candidates. On those cells, video
RMSE is 5.105, 5.060 and 2.757 cm, respectively. These are matched terrain cells,
but the runs use different protocols and resolutions; this is not evidence that
one generation method is superior. Do not interpret the smaller control error
as a learned-generation improvement.

The practical baseline for the forthcoming experiment is now explicit: compare
native video coverage and error, but also report how the entire fixed reference
region changes when video is inserted into a completed terrain. A plausible
video, a smaller accepted subset, or a closed mesh alone does not establish benefit.

## Artifacts and checks

- `baseline_comparison/comparison.png`: readable three-panel figure.
- `baseline_comparison/comparison.csv`: compact numeric table.
- `baseline_comparison/comparison.json`: detailed metrics and input SHA256 values.
- `baseline_comparison/scored_masks.npz`: exact eligible and comparison masks.
- `review_tools/compare_terrain.py`: independent read-only comparison tool.
- Nine analytic/adversarial tests passed, including changed stereo, shifted grids,
  false measured labels, different references/poses, duplicate inputs, and empty
  or disjoint coverage. Same-cell errors reproduce the previously audited arrays.

The original acceptance rules have not been altered. Code and output ownership
remain as designated in the handoff; Jarvis was not used for this review.
