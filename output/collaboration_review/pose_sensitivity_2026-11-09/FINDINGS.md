# Pose sensitivity of the conditional 033-to-034 bridge

2026-11-09. This reviewer study leaves the adopted pose and pipeline unchanged.
It uses the existing height/tilt refinement under nine illustrative horizontal
motion assumptions. No learned video was generated and no geometry was fused.

## Result

The nominal 4 m drive / 10 degree turn reproduces the saved endpoint poses within
1e-10 absolute matrix tolerance. No accepted feature-registration path connects
033 and 034 in the current graph, so the bridge remains based on the documented
movement assumption and conditional height refinement.

For the study, drive distance was varied over 3.5, 4.0 and 4.5 m, and turn over
5, 10 and 15 degrees. These ranges are illustrative perturbations, not estimated
odometry errors, confidence intervals or probability distributions.

- Six of nine height refinements pass their existing checks.
- Five of those six reach a permitted vertical-fit bound, including the nominal.
- A 4 m / 5 degree scenario passes with a 1.13 cm median height residual, but
  its 90th-percentile displacement of the same B terrain points is 1.00 m relative
  to nominal placement. Its 90th-percentile absolute height change is 17.4 cm.
- A 4.5 m / 5 degree scenario passes with a 0.71 cm median height residual, yet
  shifts the same points by 1.19 m at the 90th percentile relative to nominal.
- Holding the turn at 10 degrees and varying distance by +/-0.5 m gives about
  0.52 m 90th-percentile terrain displacement; both height fits pass.
- All 15 degree scenarios fail the refinement's shared-footprint requirement.
  Their returned poses retain the unrefined assumed placement; their displacements
  include that missing vertical correction and should not be compared as accepted fits.

The displacement calculation uses the same 5,152 sampled real B stereo points
under every transform. It measures model sensitivity, not ground-truth error.
By contrast, each fit's residual uses a different overlap subset (27 to 83
validation cells among accepted fits). Smaller residuals must not be used to rank
these motion hypotheses as if they shared independent correspondences.

## Implication for the learned bridge

The proposed imagery and generated terrain must retain the conditional 4 m / 10
degree placement unless independent pose evidence changes it. The smaller residual
of an alternative assumption is not sufficient evidence to adopt that assumption.
Height agreement can coexist with substantially different horizontal placement.

Evaluate learned generation first on the registered 044-to-047 control with 046
withheld. If the 033-to-034 demonstration is later generated, label it a conditional
spatial completion and distinguish local stereo fidelity, synthetic terrain error,
and uncertain relative placement. Neither video consistency nor a closed mesh
resolves missing real-world XY/yaw evidence.

Artifacts: `pose_sensitivity.json` contains complete records and source hashes;
`pose_sensitivity.csv` is the compact table; `scenario_poses.npz` preserves the
transforms and identical point sample; `pose_sensitivity.png` is the summary figure.
Reproduce with `python -m review_tools.review_pose_sensitivity --out <new-directory>`
from the repository root in the reconstruction environment.
