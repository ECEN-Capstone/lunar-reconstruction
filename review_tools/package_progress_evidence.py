"""Package existing figures and result records without changing their contents."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/progress_presentation'
FIGURES = json.loads((OUT / 'figure_sources.json').read_text(encoding='utf-8'))
EXPORTS = Path('C:/Users/rhunt/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Roaming/Codex/web/Codex/artifact-sessions/exports/latest/eb383c220925d7582755e9116ead7eb07efba0b16bf76971c77fa6c7688e4149')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    items = {}
    figure_index = []
    for index, fig in enumerate(FIGURES, 1):
        src = Path(fig['source'])
        name = f"figures/slide_{fig['slide']:02d}_{index:02d}_{src.name}"
        items[name] = src.read_bytes()
        figure_index.append({**fig, 'packaged_path': name, 'sha256': digest(items[name])})
    for n in range(1, 33):
        items[f'slide_previews/slide_{n:02d}.png'] = (EXPORTS / f'slide-{n}.png').read_bytes()
    for name in ['DETAILED_REPORT_AND_SPEAKER_NOTES.md', 'slide_evidence.json']:
        items[name] = (OUT / name).read_bytes()
    items['figure_index.json'] = json.dumps(figure_index, indent=2).encode()
    sources = [
        'output/collaboration_review/2026-11-09/baseline_comparison/comparison.csv',
        'output/collaboration_review/2026-11-09/baseline_comparison/comparison.json',
        'output/collaboration_review/2026-11-09/COMPARISON_FINDINGS.md',
        'output/collaboration_review/negative_controls_2026-11-09/FINDINGS.md',
        'output/collaboration_review/negative_controls_2026-11-09/negative_control_review.json',
        'output/collaboration_review/pose_sensitivity_2026-11-09/pose_sensitivity.csv',
        'output/collaboration_review/pose_sensitivity_2026-11-09/FINDINGS.md',
        'output/collaboration_review/v2_control_2026-11-09/evaluation/metrics.json',
        'output/generated_stereo_trial/REPORT.md',
        'output/uber_relaxed/REPORT.md',
        'output/chronological_video/REPORT.md',
        'output/chronological_video/mid036_model/metrics.json',
        'output/largest_terrain/component_obs_044/metrics.json',
        'output/closed_terrain/obs_034/validation.json',
        'artifacts/runs/r15_terrain_completion/obs_034/completion_metrics.json',
        'TERRAIN_COMPLETION.md',
        'report_evidence/sam2_inventory.json',
        'report_evidence/sam2_output_checks.json',
    ]
    for rel in sources:
        items['evidence/' + rel] = (ROOT / rel).read_bytes()
    for src in (ROOT / 'output/all_observations_overlay').iterdir():
        if src.is_file():
            items['all_observations_overlay/' + src.name] = src.read_bytes()
    readme = '''# Reconstruction and video progress — 9 November 2026

The editable 32-slide presentation is in the live Codex presentation artifact:
artifact_DVCU5iyih2QXVXO5k70flhvAj9qwuYuR

Use slides 1–13 for a roughly 14-minute update plus questions. Slides 14–32
provide technical details and backup evidence. This ZIP contains the original
high-resolution figures, 32 slide previews, detailed speaker notes and supporting
numeric records. The PNG slide previews are not editable slide objects.

## Evidence status

- Real stereo: 50 accepted local reconstructions from 56 candidate observations.
- Largest completed footprint: 77.20 m²; 31.0% of grid cells have observed support.
- Tested procedural video additions do not beat the fixed-region interpolation baseline.
- Cross-frame reprojection is implemented; negative controls expose missing acceptance gates.
- No learned-generator output ZIP has been received in this workspace.
- The 12-family method list is a proposed screening slate, not 12 completed tests.
- Blender import, sim-to-real comparison and the traversability root cause remain unverified here.
- SAM2 proposals exist; semantic review and integration as 3D priors remain outstanding.

## Full-traverse overlay

Open all_observations_overlay/all_observations_and_path.png for the full-size
figure. The folder includes SVG, coordinates and documented assumptions.
All 56 observation IDs appear; 50 reconstructed point clouds are superimposed.
This is an approximate command-derived scenario, not a measured global pose map.

## Reuse

figure_index.json maps each high-resolution figure to its slide and source.
slide_evidence.json maps claims and speaker notes to their supporting records.
SHA256SUMS.json records every other packaged payload. Historical source reports
are preserved verbatim; the slide notes explain later updates and limitations.
'''
    items['README.md'] = readme.encode()
    items['SHA256SUMS.json'] = json.dumps({k:digest(v) for k,v in sorted(items.items())},indent=2).encode()
    dst = OUT / 'reconstruction_update_figures_and_evidence.zip'
    with zipfile.ZipFile(dst, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, data in items.items():
            z.writestr(name, data)
    with zipfile.ZipFile(dst) as z:
        assert z.testzip() is None
        manifest = json.loads(z.read('SHA256SUMS.json'))
        assert all(digest(z.read(k)) == v for k,v in manifest.items())
    (OUT / 'README.md').write_text(readme, encoding='utf-8')
    print(json.dumps({'path':str(dst),'files':len(items),'figures':len(FIGURES),'size_mb':round(dst.stat().st_size/1024**2,2),'sha256':digest(dst.read_bytes())},indent=2))

if __name__ == '__main__':
    main()
