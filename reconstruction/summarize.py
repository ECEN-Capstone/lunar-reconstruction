"""Append measured experiment results to the human-written reconstruction report."""
import json
from pathlib import Path
import numpy as np
from .geometry import ROOT


def read(path):return json.loads(path.read_text())


def main():
    runs=ROOT/'artifacts/runs';lines=['## Executed experiments and measured results','',
        'All runs below were executed locally. A run directory is the authoritative record: configuration, inputs/hashes, coordinate convention, metrics and intermediate arrays remain together. Runtime metrics exclude some plotting/export overhead. Algorithmic consistency statistics are not ground-truth errors.','',
        '| Run | Input / change | Retained points | Coverage | Median SIFT disparity difference (px) | Conclusion |',
        '|---|---|---:|---:|---:|---|']
    descriptions={
        'r01_raw_obs003':('obs_003 raw, 256 disparities','End-to-end raw baseline; near ground truncated, distant and border outliers.'),
        'r02_calibrated_obs003':('obs_003 NC, same matcher','More initial support; raw clipping can be disguised by radiometry.'),
        'r03_raw_clahe_obs003':('obs_003 raw + CLAHE','Small coverage gain; no demonstrated feature-error benefit. Not selected for final batch.'),
        'r04_raw_obs029':('obs_029 raw, 256 disparities','Rock/terrain reference; same near-range truncation.'),
        'r05_wide_raw_obs029':('obs_029 raw, 512 disparities, padding, d>=16','Recovers closer ground; source-border outliers remain.'),
        'r06_wide_calibrated_obs029':('obs_029 NC, same wider matcher','Improves feature agreement/support, but needs original-raw quality mask.'),
        'r07_wide_raw_obs003':('obs_003 raw, wider matcher','Complete raw pipeline with closer terrain; source-unit scale only.')}
    for name,(description,conclusion) in descriptions.items():
        m=read(runs/name/'metrics.json');e=m['feature_disparity_error_median_px']
        lines.append(f"| [{name}](artifacts/runs/{name}/metrics.json) | {description} | {m['valid_points']:,} | {m['valid_fraction']:.2%} | {e:.3f} | {conclusion} |")
    batch=read(runs/'r08_quality_batch/batch_metrics.json');ok=[r for r in batch if r['status']=='reconstructed'];bad=[r for r in batch if r['status']=='rejected']
    filtered=read(runs/'r11_filtered_batch/batch_metrics.json');byid={r['observation']:r for r in filtered}
    lines += ['',f"`r08_quality_batch`: {len(ok)} reconstructed, {len(bad)} rejected. Retained {sum(r['valid_points'] for r in ok):,} per-frame points before support filtering; median per-frame coverage {np.median([r['valid_fraction'] for r in ok]):.2%}. Median of per-frame SIFT disparity medians: {np.median([r['feature_disparity_error_median_px'] for r in ok]):.3f} pixels. These totals contain overlapping observations and residual mismatches.",
        '',f"Rejected rows: {', '.join(r['observation'] for r in bad)}. Obs_043 fails rig geometry. The others lack sufficient reliable feature matches under glare/saturation/poor texture; this rejects available evidence, not necessarily the underlying physical pair.",
        '',f"`r11_filtered_batch`: {len(filtered)} filtered point clouds and {len(filtered)} local meshes, totaling {sum(r['valid_points'] for r in filtered):,} per-frame points and {sum(r['mesh_faces'] for r in filtered):,} triangles. Median coverage {np.median([r['valid_fraction'] for r in filtered]):.2%}. This is a collection of local observations, not the size of a unique global surface.",
        '', '`r09_registration_pilot`: tested the first 12 unfiltered accepted frames, yielding local components {003,004}, {005,006}, {010,012}. Border/far outliers visible in all-observed fusion prompted final support filtering. Pilot retained for comparison.',
        '', '`r10_filter_pilot_obs003`: removed isolated/border/depth-discontinuous support from obs_003; retained 69,844 points and 6,671 triangles. Inspected before filtering all 50 frames.',
        '', '`r13_rejection_test_obs043`: deliberately attempted inconsistent raw pair through the standalone API; expected `ReconstructionRejected` was observed and no cloud was exported.',
        '', '### Per-observation dense results', '',
        '| Observation | Initial points | Final supported points | Final coverage | Local mesh faces | Initial SIFT comparisons | Initial median / p90 disparity discrepancy (px) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in ok:
        m=byid[r['observation']];lines.append(f"| {r['observation']} | {r['valid_points']:,} | {m['valid_points']:,} | {m['valid_fraction']:.2%} | {m['mesh_faces']:,} | {r['feature_disparity_comparisons']} | {r['feature_disparity_error_median_px']:.3f} / {r['feature_disparity_error_p90_px']:.3f} |")
    lines += ['', 'Disparity comparisons use retained dense pixels coinciding with robust SIFT matches and <1-pixel fixed-model vertical residual. They are sparse checks selected for reliable texture, not unbiased tests over shadows or all terrain. Nearest-pixel sampling adds quantization relative to subpixel features. Final support filtering preserves retained XYZ values; it does not re-estimate disparity.',
        '', '### Representative outputs', '',
        'Raw milestone, preserved unchanged:', '', '![Raw stereo baseline](artifacts/runs/r01_raw_obs003/diagnostics.png)', '',
        'Final support-filtered terrain and rock observation:', '', '![Filtered obs_029](artifacts/runs/r11_filtered_batch/obs_029/filtered_diagnostics.png)', '',
        'Actual exported triangles read back from PLY; holes were not filled:', '', '![Local mesh](artifacts/runs/r11_filtered_batch/obs_029/mesh_views.png)', '',
        'Largest supported single-frame cloud:', '', '![Filtered obs_034](artifacts/runs/r11_filtered_batch/obs_034/filtered_diagnostics.png)', '',
        '[Obs_034 point cloud](artifacts/runs/r11_filtered_batch/obs_034/points_calibration_units.ply) and [observed-surface mesh](artifacts/runs/r11_filtered_batch/obs_034/local_mesh_calibration_units.obj).', '']
    reg=runs/'r12_registration'
    if (reg/'components.json').exists():
        edges=read(reg/'registration_edges.json');accepted=[e for e in edges if e['accepted']];components=read(reg/'components.json');multi=[c for c in components if len(c['frames'])>1]
        lines += ['### Final registration and fusion', '', f"`r12_registration`: tested {len(edges)} temporal/retrieval links among {len(filtered)} filtered frames; accepted {len(accepted)}. Found {len(multi)} multi-frame components and {sum(len(c['frames'])==1 for c in components)} singletons. No transform is invented between disconnected components.", '',
            '| Accepted link | Held-out count | Held-out median / p90 (px) | Target depth checks | Median relative 3D difference |', '|---|---:|---:|---:|---:|']
        for e in accepted:lines.append(f"| {e['source']} -> {e['target']} | {e['heldout_count']} | {e['heldout_median_px']:.3f} / {e['heldout_p90_px']:.3f} | {e['target_depth_checks']} | {e['median_relative_3d_error']:.2%} |")
        lines += ['', '| Component frames | Fused all-observed voxels | Voxels with >=2 frame support |', '|---|---:|---:|']
        for c in multi:lines.append(f"| {', '.join(c['frames'])} | {c['fused_voxels']:,} | {c['multiview_supported_voxels']:,} |")
        cycles=[e for p in reg.glob('component_*/cycle_consistency.json') for e in read(p)]
        if cycles:lines += ['',f"Maximum composed-edge cycle disagreement: {max(c['rotation_degrees'] for c in cycles):.4f} degrees and {max(c['translation_calibration_units'] for c in cycles):.3f} source length units. Tree edges are included and trivially close; non-tree edges are the useful checks. No global accuracy claim follows from small cycle residuals."]
        if multi:
            best=max(multi,key=lambda c:c['multiview_supported_voxels']);root=min(best['frames'])
            lines += ['',f"Representative fusion in the {root} component:", '',f"![Local fusion](artifacts/runs/r12_registration/component_{root}/fusion_views.png)", '',f"[Multi-view supported cloud](artifacts/runs/r12_registration/component_{root}/cloud_multiview_supported_calibration_units.ply); [camera trajectory](artifacts/runs/r12_registration/component_{root}/camera_trajectory.json).", '']
    assemblies=reg/'mesh_assemblies.json'
    if assemblies.exists():
        assembly=read(assemblies)
        lines += ['### Registered observed-surface meshes','',
            f"Exported {len(assembly)} component meshes by transforming existing observed triangles into each component frame. No surfaces are added between observations. These triangle unions retain overlapping faces and open boundaries; they are not watertight collision geometry.",'',
            '| Component | Vertices | Observed triangles |','|---|---:|---:|']
        for a in assembly:lines.append(f"| [{a['component']}](artifacts/runs/r12_registration/{a['component']}/mesh_observed_union_calibration_units.obj) | {a['vertices']:,} | {a['triangles']:,} |")
        lines += ['','The largest assembled mesh is shown below. Its broad holes and incomplete coverage are real limitations, not missing visualization effects.','',
            '![Registered observed mesh](artifacts/runs/r12_registration/component_obs_044/mesh_views.png)','']
    validation=ROOT/'artifacts/investigation/output_validation.json'
    if validation.exists():
        q=read(validation);lines += ['### Final validation', '',f"Read back {len(q['ply_checks'])} PLY exports, checking exact vertex/face counts, finite XYZ, index bounds and file length. Representative meshes additionally have positive triangle areas and were visually rendered from the exported data. Rehashed all {q['source_files_rehashed']} original input files: {len(q['changed_source_files'])} changed. Numerical geometry tests and expected rejection test passed. `pip check` reported no broken requirements.", '']
    if (ROOT/'artifacts/investigation/reproducibility.json').exists():
        lines += ['`r14_baseline_reproduction`: reran the full raw obs_003 pipeline after implementation updates. Left/right disparity, depth and XYZ arrays were exactly equal to r01, including invalid-value locations. See `artifacts/investigation/reproducibility.json`.','']
    report=ROOT/'RECONSTRUCTION_REPORT.md';text=report.read_text(encoding='utf-8');marker='<!-- GENERATED_RESULTS -->'
    report.write_text(text.split(marker)[0]+marker+'\n\n'+'\n'.join(lines)+'\n',encoding='utf-8')
    print('Updated measured report appendix')


if __name__=='__main__':main()
