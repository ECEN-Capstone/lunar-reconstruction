"""Collect experiment evidence and slide copy without rerunning reconstruction."""
import json
import shutil
import zipfile
import cv2

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from .geometry import ROOT


def main():
    out = ROOT/'output/generated_stereo_slide_pack'
    out.mkdir(exist_ok=True)
    copies = {
        '01_input_trial_1.png': 'output/generated_stereo_trial/stereo_trial_1/original_canvas.png',
        '01_input_trial_2.png': 'output/generated_stereo_trial/stereo_trial_2/original_canvas.png',
        '02_mesh_comparison_trial_1.png': 'output/uber_relaxed/stereo_trial_1/mesh_comparison.png',
        'backup_all_seven_meshes.png': 'output/uber_relaxed/stereo_trial_1/renders/all_seven_meshes.png',
        'backup_all_seven_matching_results.png': 'output/uber_relaxed/stereo_trial_1/comparison.png',
        'backup_real_obs034_completion.png': 'artifacts/runs/r15_terrain_completion/obs_034/mesh_comparison.png',
        'source_generated_stereo_report.md': 'output/generated_stereo_trial/REPORT.md',
        'source_uber_relaxed_report.md': 'output/uber_relaxed/REPORT.md',
    }
    for name, source in copies.items():
        shutil.copy2(ROOT/source, out/name)

    comparison_sources = {}
    for trial in (1, 2):
        folder = ROOT/f'output/generated_stereo_trial/stereo_trial_{trial}'
        fig, axes = plt.subplots(1, 3, figsize=(15, 6.5))
        fig.subplots_adjust(left=.01, right=.99, bottom=.16, top=.80, wspace=.04)
        scene = cv2.imread(str(folder/'diagnostic_strict/rectified_left.png'), 0)
        axes[0].imshow(scene, cmap='gray', vmin=0, vmax=255)
        axes[0].set_title('Generated scene\nRectified left image', fontsize=15, pad=14)
        for ax, profile in zip(axes[1:], ('strict', 'relaxed')):
            diagnostic = folder/f'diagnostic_{profile}'
            mask = cv2.imread(str(diagnostic/'validity_mask.png'), 0)
            metric = json.loads((diagnostic/'metrics.json').read_text())
            assert int(np.count_nonzero(mask)) == metric['valid_pixels']
            ax.imshow(mask, cmap='gray', vmin=0, vmax=255, interpolation='nearest')
            ax.set_title(f"{profile.capitalize()} settings\n{metric['whole_image_valid_fraction']:.2%} of pixels retained", fontsize=15, pad=14)
            backup = f'backup_trial_{trial}_{profile}_diagnostic.png'
            source = f'output/generated_stereo_trial/stereo_trial_{trial}/diagnostic_{profile}/dense_diagnostic.png'
            shutil.copy2(ROOT/source, out/backup)
            copies[backup] = source
        for ax in axes:
            ax.axis('off')
        fig.suptitle(f'Trial {trial}: strict and relaxed matching retained little depth', fontsize=19, y=.97)
        fig.supxlabel('White in the masks: accepted depth estimate. Black: rejected. Percentages include the whole image.\n'
                      'Diagnostic runs bypassed the failed camera check. Accepted pixels do not establish correct 3D geometry.',
                      fontsize=11, y=.035, linespacing=1.6)
        filename = f'01_strict_vs_relaxed_trial_{trial}.png'
        fig.savefig(out/filename, dpi=180)
        plt.close(fig)
        comparison_sources[filename] = {
            'folder': str(folder.relative_to(ROOT)),
            'files': ['diagnostic_strict/rectified_left.png', 'diagnostic_strict/validity_mask.png',
                      'diagnostic_relaxed/validity_mask.png', 'diagnostic_strict/metrics.json',
                      'diagnostic_relaxed/metrics.json'],
            'note': 'Scientific comparison of saved pixel masks. No matching rerun or changes to estimates.'}

    names = ['uber_relaxed', 'uber_relaxed_row_adjusted', 'row_adjusted_tighter']
    labels = ['Uber relaxed', 'Uber + vertical alignment correction', 'Corrected alignment + tighter filters']
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.5))
    fig.subplots_adjust(left=.01, right=.99, bottom=.12, top=.80, wspace=.04)
    for ax, name, label in zip(axes, names, labels):
        folder = ROOT/'output/uber_relaxed/stereo_trial_1'/name
        with np.load(folder/'arrays.npz') as data:
            mask = data['validity']
        metric = json.loads((folder/'metrics.json').read_text())
        assert int(mask.sum()) == metric['accepted_pixels']
        ax.imshow(mask, cmap='gray', vmin=0, vmax=1, interpolation='nearest')
        ax.set_title(f"{label}\n{metric['whole_image_fraction']:.1%} of the whole image", fontsize=14, pad=14)
        ax.axis('off')
    fig.suptitle('Trial 1: vertical alignment correction improves foreground matching', fontsize=19, y=.97)
    fig.supxlabel('White: accepted depth estimate. Black: rejected. Coverage includes sky and does not measure 3D accuracy.', fontsize=12, y=.04)
    fig.savefig(out/'03_alignment_and_filtering_trial_1.png', dpi=180)
    plt.close(fig)
    (out/'figure_sources.json').write_text(json.dumps({**copies, **comparison_sources,
        '03_alignment_and_filtering_trial_1.png': {
            'source': 'output/uber_relaxed/stereo_trial_1/<profile>/arrays.npz',
            'profiles': names,
            'field': 'validity',
            'note': 'New scientific plot of saved masks. No matching rerun or changes to estimates.'}}, indent=2))

    notes = '''# Generated stereo experiment: three-slide progress update

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
'''
    (out/'SLIDE_COPY_AND_FIGURE_GUIDE.md').write_text(notes, encoding='utf-8')
    archive = out.parent/'generated_stereo_slide_pack.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(out.iterdir()):
            if file.is_file():
                z.write(file, file.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(out)
    print(archive)


if __name__ == '__main__':
    main()
