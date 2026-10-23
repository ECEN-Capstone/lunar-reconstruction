# Joint stereo-generation pilot

Date: October 18, 2026 (America/Chicago).

## Setup

Two identical built-in image-generation calls each received four real NavCam images: earlier left/right and later left/right. Each call requested a joint intermediate stereo pair from one virtual rover pose, retaining the original rig's baseline, relative camera orientation, and unrectified image geometry. See prompts/stereo_prompt.txt for the exact prompt.

The real source pairs are the September 1 endpoint observations used for the temporal pilot. The right-camera starts occur approximately 40 seconds after the corresponding left-camera starts. Real-image controls were evaluated with the same calibration and matcher used for generated pairs.

Both generated canvases were 1774 x 887 RGB, rather than the requested 2048 x 1024 grayscale. Each canvas was split at its exact midpoint into two 887 x 887 views and normalized to 1024 x 1024 for analysis. This is an evaluation coordinate convention, not verification that the generator preserved field of view or intrinsics. Original outputs are unchanged.

## Fixed-calibration result

| Pair | Reciprocal ratio-test matches | Median epipolar error | 90th percentile | Matches within 2 px |
| --- | ---: | ---: | ---: | ---: |
| Real A | 73 | 0.45 px | 0.90 px | 98.6% |
| Real C | 40 | 0.70 px | 1.46 px | 92.5% |
| Synthetic trial 1 | 1,956 | 8.46 px | 11.08 px | 0% |
| Synthetic trial 2 | 34 | 25.93 px | 48.92 px | 0% |

Errors are symmetric point-to-epipolar-line distances against the supplied CAHV stereo model, not distances against a newly fitted model. No calibration-based filtering was applied before computing these distributions. Matching used SIFT capped at 10,000 features per image and a reciprocal nearest-neighbor ratio of 0.75.

The generated samples did not preserve the requested camera calibration. Trial 1 is particularly informative: many image features matched between eyes, yet none of those matches lay within 2 pixels of the expected stereo geometry. Feature abundance therefore cannot serve as a stereo-validity test.

This is a two-sample result on one scene. It does not establish universal failure of image generation or rule out fitting a different camera model to generated views. It does establish that these outputs should not enter the original calibrated stereo pipeline as ordinary captures. Stereo disparity accuracy, metric depth, dense reconstruction, and navigation performance were not evaluated after this failed initial screen.

## Reproducibility boundary

The measurement procedure is configurable and reproducible from the saved inputs and outputs. The built-in generation stage exposed neither a model version nor a generation seed, so this package cannot promise identical regeneration. Repeating a documented stochastic experiment and exactly reproducing its saved-image measurements are separate claims.

The earlier 84.4-pixel temporal repeat difference measures output-to-output landmark variation for the same requested virtual viewpoint. It is not the stereo epipolar error reported in this table and cannot be directly converted to a depth error.

Next work should introduce explicit geometric constraints, test multiple scenes with real-image controls, and validate any accepted generated views against unused real observations before making reconstruction-accuracy claims.
