"""Plot output pose progression for the refreshed positive and negative controls."""
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = ROOT/'output/collaboration_review'
    out = base/'negative_controls_2026-11-09'
    camera = np.load(ROOT/'output/chronological_video/learned_inputs/holdout046_endpoints_v2/commanded_trajectory.npz')
    commands = camera['T_world_from_camera'][:, :3, 3]
    origin = commands[0]
    displacement = commands[-1]-origin
    unit = displacement/np.linalg.norm(displacement)
    fig, ax = plt.subplots(figsize=(10, 5.5), layout='constrained')
    ax.plot(np.arange(33), (commands-origin)@unit, '--', color='#777777', label='Commanded path (hypothesis)')
    for label, folder, color in [
        ('Procedural control', base/'v2_control_2026-11-09', '#3879a8'),
        ('Frozen endpoint', out/'frozen_first_endpoint', '#a87927'),
        ('Endpoint crossfade', out/'linear_endpoint_crossfade', '#b64848')]:
        poses = np.load(folder/'pose_check/anchor_poses.npz')
        xyz = poses['T_world_from_camera'][:, :3, 3]
        progress = (xyz-origin)@unit
        ax.plot(np.arange(len(progress)), progress, 'o-', color=color, markersize=3.5, label=label)
    ax.set(xlabel='Video frame index', ylabel='Estimated position along endpoint baseline (m)',
           title='Pose checks can pass a stationary view or a crossfade\nMissing pose estimates remain gaps; points are not measured terrain')
    ax.legend(loc='upper left')
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(alpha=.2)
    fig.savefig(out/'pose_progression.png', dpi=180)
    plt.close(fig)
    print(out/'pose_progression.png')


if __name__ == '__main__':
    main()
