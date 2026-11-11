"""Bounded reviewer sensitivity study; does not update the adopted mobility prior."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from reconstruction.video_bridge import read, pose_pair, transform, relative

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(values):
    return dict(median=float(np.median(values)), p90=float(np.percentile(values, 90)), maximum=float(values.max()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    base = ROOT/'output/chronological_video/mid036_7'
    cfg = json.loads((ROOT/'configs/video_mobility_priors.json').read_text())['obs_033:obs_034']
    files = list((ROOT/'reconstruction').glob('*.py')) + [ROOT/'configs/video_mobility_priors.json', base/'trajectory.npz', base/'metrics.json']
    for name in ['obs_033', 'obs_034']:
        files += list((ROOT/'artifacts/runs/r11_filtered_batch'/name).glob('provenance.json'))
        files += list((ROOT/'artifacts/runs/r11_filtered_batch'/name).glob('xyz_rectified_calibration_units.npy'))
    files += [ROOT/'artifacts/runs/r12_registration/registration_edges.json']
    hashes = {str(f.relative_to(ROOT)):sha(f) for f in files}
    a,b = read('obs_033'),read('obs_034')
    rel,path = relative(a['name'],b['name'])
    if rel is not None:
        raise ValueError('A registered relative pose is now available; reevaluate the study design')
    nominal = np.load(base/'trajectory.npz')['T_world_from_camera'][[0,-1]]
    valid = np.isfinite(b['xyz']).all(2) & (b['xyz'][:,:,2] < 11.)
    # The exact same B measurements are transformed in every scenario. These
    # displacement statistics do not compare different overlap samples.
    sample = b['xyz'][valid][::50]
    nominal_points = transform(sample,nominal[-1])
    rows = []
    transforms = []
    distances = [cfg['distance_m']-.5,cfg['distance_m'],cfg['distance_m']+.5]
    turns = [cfg['turn_deg_ccw']-5,cfg['turn_deg_ccw'],cfg['turn_deg_ccw']+5]
    for distance in distances:
        for turn in turns:
            print(f'Reviewing distance={distance:.1f} m, turn={turn:.1f} degrees',flush=True)
            A,B,info = pose_pair(a,b,None,distance/cfg['distance_m'],turn-cfg['turn_deg_ccw'])
            if info['source'] != 'conditional mobility prior':
                raise ValueError('Unexpected pose source')
            refinement = info['height_refinement']
            delta = transform(sample,B)-nominal_points
            at_bound = None
            if 'allowed_dz_m' in refinement:
                at_bound = bool(min(abs(refinement['elevation_change_m']-x) for x in refinement['allowed_dz_m']) < 1e-6)
            row = dict(distance_m=distance, turn_deg=turn, refinement=refinement,
                vertical_fit_at_bound=at_bound, camera_position_change_m=float(np.linalg.norm(B[:3,3]-nominal[-1,:3,3])),
                same_points_displacement_3d_m=stats(np.linalg.norm(delta,axis=1)),
                same_points_displacement_xy_m=stats(np.linalg.norm(delta[:,:2],axis=1)),
                same_points_abs_height_change_m=stats(abs(delta[:,2])))
            if distance==cfg['distance_m'] and turn==cfg['turn_deg_ccw']:
                if not np.allclose(np.stack([A,B]),nominal,rtol=0,atol=1e-10):
                    raise ValueError('Nominal pose no longer reproduces saved geometry')
                row['nominal_saved_pose_reproduced'] = True
            rows.append(row)
            transforms.append(B)
    if any(sha(ROOT/name)!=expected for name,expected in hashes.items()):
        raise ValueError('Evidence changed during sensitivity review')
    result = dict(status='completed sensitivity review; adopted prior unchanged',
        source_sha256=hashes, reviewer_sha256=sha(Path(__file__)), endpoints=[a['name'],b['name']],
        nominal_distance_m=cfg['distance_m'], nominal_turn_deg=cfg['turn_deg_ccw'],
        scenario_definition='Illustrative distance +/-0.5 m and yaw +/-5 degrees; not measured errors, confidence bounds or probabilities',
        sample_points=len(sample), sampling='Every 50th finite endpoint B stereo point with rectified-camera Z below 11 m',
        reference='Saved conditional nominal pose, not true rover placement',
        limitations=['Each height fit has different overlap correspondences and validation cells; residuals cannot rank XY/yaw hypotheses fairly.',
                    'Displacement uses identical B stereo points in every scenario and is relative to the nominal model, not ground-truth error.',
                    'Failed refinement keeps the unrefined assumed pose, as the existing pipeline does; separate these from accepted fits.',
                    'No scenario is selected to replace the documented maneuver; no synthetic terrain is regenerated.'], scenarios=rows)
    out.mkdir(parents=True,exist_ok=False)
    (out/'pose_sensitivity.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    np.savez_compressed(out/'scenario_poses.npz', T_world_from_camera=np.asarray(transforms), nominal_endpoints=nominal,
                        same_B_points_camera_m=sample, distances_m=np.repeat(distances,len(turns)), turns_deg=np.tile(turns,len(distances)))
    with (out/'pose_sensitivity.csv').open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['distance_m','turn_deg','height_refinement_accepted','validation_cells','height_median_residual_cm','vertical_fit_at_bound','terrain_displacement_p90_m','height_change_p90_cm'])
        for r in rows:
            h=r['refinement']; residual=h.get('adjusted_median_height_residual_m')
            w.writerow([r['distance_m'],r['turn_deg'],h['accepted'],h.get('validation_cells'),None if residual is None else 100*residual,
                        r['vertical_fit_at_bound'],r['same_points_displacement_3d_m']['p90'],100*r['same_points_abs_height_change_m']['p90']])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,5.7),layout='constrained')
    values=np.array([r['same_points_displacement_3d_m']['p90'] for r in rows]).reshape(3,3)
    im=ax.imshow(values,cmap='YlOrRd',vmin=0)
    ax.set_xticks(range(3),[f'{v:g}' for v in turns]);ax.set_yticks(range(3),[f'{v:g}' for v in distances])
    ax.set(xlabel='Assumed turn (degrees CCW)',ylabel='Assumed drive distance (m)',title='Terrain placement sensitivity around the 4 m / 10 degree prior\nIllustrative scenarios; not confidence bounds or measured error')
    for i,r in enumerate(rows):
        text=f"{values.flat[i]:.2f} m\n"+('height fit accepted' if r['refinement']['accepted'] else 'height fit rejected')
        ax.text(i%3,i//3,text,ha='center',va='center',fontsize=9,color='white' if values.flat[i]>.7*values.max() else 'black')
    fig.colorbar(im,ax=ax,label='90th-percentile displacement of the same terrain points (m)')
    fig.savefig(out/'pose_sensitivity.png',dpi=180);plt.close(fig)
    print(json.dumps(dict(scenarios=len(rows),accepted_height_fits=sum(r['refinement']['accepted'] for r in rows),sample_points=len(sample)),indent=2))


if __name__ == '__main__':
    main()
