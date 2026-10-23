# Generated stereo experiment: three-slide progress update

## Slide 1: Generated stereo failed the original camera checks

Slide text:
- Tested two generated stereo pairs after splitting each canvas into left and right images.
- Both pairs failed the original Navcam camera-geometry checks.
- Diagnostic matching retained only 0.55-0.61% of pixels with strict settings and about 4% with relaxed settings.

Figure: `01_strict_vs_relaxed_trial_1.png`. Use across the slide to show the generated scene alongside strict and relaxed acceptance masks. White in the masks means a retained depth estimate. `01_strict_vs_relaxed_trial_2.png` shows the corresponding Trial 2 result. The original inputs remain available as `01_input_trial_1.png` and `01_input_trial_2.png`.

Say: "The images look like plausible stereo, but corresponding features do not line up as the original camera model expects. The normal pipeline rejects both pairs. We ran separate diagnostic experiments to see what the matcher would produce anyway."

Small caption: "Diagnostic matching after bypassing the failed camera check. Coverage measures retained image pixels, not 3D accuracy."

## Slide 2: Relaxing the rules increased coverage but introduced severe artifacts

Slide text:
- Uber relaxed settings retained 30.1% of Trial 1 and 24.5% of Trial 2.
- Removing almost all checks raised coverage to about 85% for both pairs.
- The extra geometry included sky estimates, long spikes and stretched triangles.

Figure: `02_mesh_comparison_trial_1.png`. Use it across most of the slide. Left: uber relaxed. Middle: almost no checks. Right: uber relaxed with vertical alignment correction.

Say: "We could force many more triangles, but the rendered meshes showed why the filters rejected them. The middle panel is the most complete numerically and the most visibly distorted. The right panel shows the alignment correction explored next."

Required caption: "Trial 1. Full exported meshes, with different axis scales. Arbitrary units. Coverage counts accepted pixels across the whole image, including sky."

Optional numerical comparison:

| Configuration | Trial 1 coverage | Trial 2 coverage |
|---|---:|---:|
| Previous relaxed diagnostic | 4.1% | 4.0% |
| Uber relaxed | 30.1% | 24.5% |
| Almost all checks removed | 85.5% | 85.2% |
| Uber with vertical alignment correction | 45.0% | 28.7% |

## Slide 3: Alignment correction helped Trial 1, but terrain accuracy remains unverified

Slide text:
- Correcting vertical alignment reduced Trial 1's median held-out row mismatch from 8.48 to 0.67 pixels.
- With tighter filters, Trial 1 retained 25.1% coverage, but the exported mesh still broke into fragments.
- Neither trial produced validated, correctly scaled terrain. Trial 2 had only seven held-out feature matches.
- Next: test stereo rendered from one shared 3D scene with known camera poses and depth.

Figure: `03_alignment_and_filtering_trial_1.png`. White pixels show accepted estimates. The corrected, tighter result retains a foreground patch while rejecting much of the upper image.

Say: "Trial 1 contains recoverable image correspondences after an empirical vertical correction. That improves matching, but does not prove the inferred 3D shape is correct. A controlled stereo rendering would let us measure actual depth error. We could then test whether image generation preserves that geometry."

Small caption: "Image agreement is not a 3D accuracy measurement. The correction changes the assumed camera model."

## Backup evidence and presentation notes

- `backup_all_seven_meshes.png`: use for detailed questions about all seven variants. Too crowded for the main slides.
- `backup_all_seven_matching_results.png`: masks and disparities for every variant. White in the upper masks means accepted; white in the lower disparity plots means missing.
- `backup_real_obs034_completion.png`: optional comparison with a previous real-image reconstruction. Left is gridded observations; right includes inferred hole filling. It uses metres and a nominal terrain frame, unlike the generated-image experiments, so do not compare axis extents directly or call the completed side ground truth.
- The seven-profile sweep produced 14 textured OBJ meshes across two image pairs. These remain open experimental surfaces, not closed collision assets.
- No hole filling or smoothing created the generated-image results. Original camera rejection and production defaults remain unchanged.
- Trial 1's correction used 1,564 feature matches for fitting and 392 for evaluation. Of those 392, the corrected uber run accepted 279 with median disparity disagreement 0.29 pixels. These are image correspondences, not measured 3D reference points.
- Trial 2's correction used 27 fitting matches and seven evaluation matches. Do not present its small-sample median as strong accuracy evidence.

Sources: the two included source reports. `figure_sources.json` maps every figure to the original saved experiment output.
