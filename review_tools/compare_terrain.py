"""Independent read-only comparison of returned terrain arrays and fixed baselines.

Does not generate images, estimate poses, alter reconstruction gates, or fuse meshes.
All outputs are written to a new review directory. Requires numpy/scipy/matplotlib.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import LinearNDInterpolator


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def equal(a, b, name):
    if not np.array_equal(a, b, equal_nan=True):
        raise ValueError(f'{name} differs; register/regrid explicitly before comparing')


def errors(prediction, truth, mask):
    delta = prediction[mask] - truth[mask]
    if not np.isfinite(delta).all():
        raise ValueError('Nonfinite value on an evaluated cell')
    if not len(delta):
        return dict(count=0, rmse_m=None, bias_m=None, median_absolute_m=None,
                    p95_absolute_m=None, maximum_absolute_m=None)
    return dict(count=len(delta), rmse_m=float(np.sqrt(np.mean(delta**2))),
                bias_m=float(delta.mean()), median_absolute_m=float(np.median(abs(delta))),
                p95_absolute_m=float(np.percentile(abs(delta), 95)), maximum_absolute_m=float(abs(delta).max()))


def compare(reference_run, run_paths):
    reference_run = Path(reference_run).resolve()
    run_paths = [Path(p).resolve() for p in run_paths]
    if len(set(run_paths)) != len(run_paths):
        raise ValueError('Duplicate candidate directory')
    if len({p.name for p in run_paths}) != len(run_paths):
        raise ValueError('Candidate directory names must be distinct for unambiguous output labels')
    refmeta = read_json(reference_run / 'metrics.json')
    with np.load(reference_run / 'surfaces.npz', allow_pickle=False) as f:
        source = {k: f[k] for k in f.files}
    with np.load(reference_run / 'validation.npz', allow_pickle=False) as f:
        truth = f['heldout_m']
    xy = np.stack(np.meshgrid(source['x'], source['y'], indexing='ij'), -1)
    strict = np.isfinite(source['stereo_m'])
    if truth.shape != strict.shape:
        raise ValueError('Reference grid shape mismatch')
    fixed_idw = source['baseline_idw_m']
    fixed_linear = LinearNDInterpolator(xy[strict], source['stereo_m'][strict])(xy)
    eligible = np.isfinite(truth) & np.isfinite(fixed_idw) & ~strict
    hashes = {}

    def record(path):
        hashes[str(path)] = digest(path)

    for file in ['metrics.json', 'surfaces.npz', 'validation.npz']:
        record(reference_run / file)
    candidates = []
    for path in run_paths:
        meta = read_json(path / 'metrics.json')
        if meta['endpoints'] != refmeta['endpoints'] or meta['pose'] != refmeta['pose']:
            raise ValueError(f'{path.name}: different endpoint pose scenario')
        if meta['grid_m'] != refmeta['grid_m']:
            raise ValueError(f'{path.name}: different grid spacing')
        integrated = (path / 'integrated_grid.npz').exists()
        file = path / ('integrated_grid.npz' if integrated else 'surfaces.npz')
        with np.load(file, allow_pickle=False) as f:
            data = {k: f[k] for k in f.files}
        if integrated:
            candidate_xy = data['xy_m']
            height = data['height_m']
        else:
            candidate_xy = np.stack(np.meshgrid(data['x'], data['y'], indexing='ij'), -1)
            height = data['merged_m']
            equal(data['stereo_m'], source['stereo_m'], f'{path.name}: strict source heights')
            equal(data['baseline_idw_m'], fixed_idw, f'{path.name}: IDW prior')
        equal(candidate_xy, xy, f'{path.name}: grid coordinates')
        labels = data['labels']
        if height.shape != truth.shape or labels.shape != truth.shape:
            raise ValueError(f'{path.name}: grid shape mismatch')
        if not np.isin(labels, [0, 1, 2, 3, 4]).all():
            raise ValueError(f'{path.name}: unknown source labels')
        equal(height[strict], source['stereo_m'][strict], f'{path.name}: preserved strict heights')
        if not np.array_equal(labels == 1, strict):
            raise ValueError(f'{path.name}: strict source labels changed')
        if not np.isfinite(height[labels > 0]).all():
            raise ValueError(f'{path.name}: labelled cells contain nonfinite heights')
        if np.isfinite(height[labels == 0]).any():
            raise ValueError(f'{path.name}: finite geometry has no provenance label')
        # Every candidate's supplied reference must match. Integrated products
        # may omit the array, in which case only the explicitly supplied common
        # reference is used and this omission is recorded below.
        validation = path / 'validation.npz'
        if validation.exists():
            with np.load(validation, allow_pickle=False) as f:
                equal(f['heldout_m'], truth, f'{path.name}: withheld reference')
            record(validation)
        holdout = meta.get('validation', {}).get('holdout', meta.get('holdout', {}).get('name'))
        if holdout and holdout != refmeta['validation']['holdout']:
            raise ValueError(f'{path.name}: different withheld observation')
        record(path / 'metrics.json')
        record(file)
        candidates.append(dict(path=path, meta=meta, height=height, labels=labels,
            video=(labels == 3) & np.isfinite(height), supplied_reference=validation.exists(), integrated=integrated))

    if not candidates:
        raise ValueError('At least one candidate is required')
    # Exclude any relaxed observed cells across all candidates for fair common
    # comparisons; those observations are not synthetic video recovery.
    relaxed_union = np.logical_or.reduce([r['labels'] == 2 for r in candidates])
    paired_eligible = eligible & ~relaxed_union & np.isfinite(fixed_linear)
    common = paired_eligible & np.logical_and.reduce([r['video'] for r in candidates])
    result = dict(reference_run=str(reference_run), endpoints=refmeta['endpoints'],
        holdout=refmeta['validation']['holdout'], grid_m=refmeta['grid_m'],
        reference='Registered withheld stereo; not surveyed ground truth',
        eligible_reference_cells=int(eligible.sum()), fixed_completion_cells=int(paired_eligible.sum()),
        common_video_cells=int(common.sum()), excluded_relaxed_union_cells=int((eligible & relaxed_union).sum()),
        baseline_origin='Strict endpoint stereo only, fixed across candidates',
        baselines_on_common=dict(linear=errors(fixed_linear, truth, common), idw=errors(fixed_idw, truth, common)),
        baselines_on_fixed_region=dict(linear=errors(fixed_linear, truth, paired_eligible), idw=errors(fixed_idw, truth, paired_eligible)),
        runs=[], input_sha256=hashes,
        limitations=['Read-only terrain audit does not certify inference provenance or output camera poses.',
                    'Common terrain cells do not make different frame/conditioning protocols equivalent.',
                    'Fixed-region hybrid is a diagnostic: accepted video where available, otherwise strict-only linear interpolation.',
                    'Cells are spatially correlated; no independence assumption or statistical significance claim.',
                    'Missing or failed reconstruction attempts must also be reported; this tool only sees supplied arrays.'])
    masks = dict(eligible_reference=eligible, fixed_completion=paired_eligible, common_video=common,
                 x=source['x'], y=source['y'])
    for index, r in enumerate(candidates):
        native = eligible & r['video']
        native_linear = native & np.isfinite(fixed_linear)
        hybrid = np.where(r['video'], r['height'], fixed_linear)
        diff = abs(hybrid[paired_eligible] - truth[paired_eligible]) - abs(fixed_linear[paired_eligible] - truth[paired_eligible])
        item = dict(name=r['path'].name, path=str(r['path']), generator=r['meta'].get('generator', 'integrated seed consensus'),
            seed=r['meta'].get('seed'), seeds=r['meta'].get('seeds'), integrated=r['integrated'],
            supplied_reference_array=r['supplied_reference'], used_frame_indices=r['meta'].get('used_frame_indices'),
            strict_cells_preserved=int(strict.sum()), video_cells_total=int(r['video'].sum()),
            native_reference_coverage=float(native.sum()/max(1, eligible.sum())),
            native_video=errors(r['height'], truth, native), native_idw=errors(fixed_idw, truth, native),
            native_linear=errors(fixed_linear, truth, native_linear), native_video_on_linear=errors(r['height'], truth, native_linear),
            common_video=errors(r['height'], truth, common),
            fixed_region_video_plus_linear=errors(hybrid, truth, paired_eligible),
            fixed_region_video_cells=int((paired_eligible & r['video']).sum()),
            improved_cells_vs_linear=int((diff < -1e-12).sum()), worsened_cells_vs_linear=int((diff > 1e-12).sum()),
            unchanged_cells_vs_linear=int((abs(diff) <= 1e-12).sum()))
        result['runs'].append(item)
        masks[f'run_{index}_native_video'] = native
    # Fail if another writer changed the evidence during the audit.
    if any(digest(Path(path)) != value for path, value in hashes.items()):
        raise ValueError('Inputs changed during review; rerun against a fixed snapshot')
    return result, masks


def render(result, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names = [r.get('display_name', r['name']) for r in result['runs']]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), layout='constrained')
    colors = ['#5379a5'] * len(names)
    axes[0].barh(names, [100*r['native_reference_coverage'] for r in result['runs']], color=colors)
    axes[0].set(xlim=(0, 100), xlabel='Eligible reference cells covered (%)', title='Accepted video coverage')
    for ax, field, baseline, title in [
        (axes[1], 'common_video', 'baselines_on_common', f"Shared video cells (n={result['common_video_cells']})"),
        (axes[2], 'fixed_region_video_plus_linear', 'baselines_on_fixed_region', f"Video + linear fallback (n={result['fixed_completion_cells']})")]:
        values = [r[field]['rmse_m'] for r in result['runs']]
        ax.barh(names, [np.nan if v is None else v*100 for v in values], color=colors)
        for method, color in [('linear', '#c26a26'), ('idw', '#658c40')]:
            v = result[baseline][method]['rmse_m']
            if v is not None:
                ax.axvline(v*100, color=color, linestyle='--', label=method.upper())
        if all(v is None for v in values):
            ax.text(.5, .5, 'No common support', ha='center', transform=ax.transAxes)
        else:
            ax.legend(fontsize=8)
        ax.set(xlabel='Height RMSE (cm)', title=title)
        ax.set_yticks([])
    for ax in axes:
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='x', alpha=.2)
        ax.invert_yaxis()
    fig.suptitle('Terrain review against withheld stereo\nCoverage and accuracy are separate; different protocols are not a controlled ablation', fontsize=12)
    fig.savefig(output / 'comparison.png', dpi=170)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference-run', required=True, type=Path)
    p.add_argument('--runs', nargs='+', required=True, type=Path)
    p.add_argument('--labels', nargs='+', help='Optional readable figure labels, one per run')
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    if args.out.exists():
        p.error('Output must be a new directory')
    if args.labels and len(args.labels) != len(args.runs):
        p.error('Provide exactly one label per candidate run')
    result, masks = compare(args.reference_run, args.runs)
    if args.labels:
        for run, label in zip(result['runs'], args.labels):
            run['display_name'] = label
    args.out.mkdir(parents=True, exist_ok=False)
    result['reviewer_sha256'] = digest(Path(__file__))
    (args.out / 'comparison.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    np.savez_compressed(args.out / 'scored_masks.npz', **masks)
    with (args.out / 'comparison.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['run', 'native_scored_cells', 'eligible_cells', 'native_video_rmse_cm',
                         'common_scored_cells', 'common_video_rmse_cm', 'fixed_region_cells', 'hybrid_rmse_cm'])
        cm = lambda x: None if x is None else x*100
        for r in result['runs']:
            writer.writerow([r['name'], r['native_video']['count'], result['eligible_reference_cells'], cm(r['native_video']['rmse_m']),
                             result['common_video_cells'], cm(r['common_video']['rmse_m']), result['fixed_completion_cells'], cm(r['fixed_region_video_plus_linear']['rmse_m'])])
    render(result, args.out)
    print(json.dumps(dict(output=str(args.out), common_video_cells=result['common_video_cells'],
                         fixed_completion_cells=result['fixed_completion_cells']), indent=2))


if __name__ == '__main__':
    main()
