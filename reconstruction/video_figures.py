"""Regenerate figures from saved chronological-video experiments; no model reruns."""
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / 'output/chronological_video'
COLORS = ['#ffffff', '#236b8e', '#61b7ba', '#d98928', '#c8cbd1']


def main():
    out = ROOT / 'figures'
    out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 12, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 5, figsize=(15, 6), layout='constrained')
    for row, name in enumerate(['holdout046_7', 'mid036_7']):
        cap = cv2.VideoCapture(str(ROOT / name / 'transition.mp4'))
        frames = []
        while True:
            ok, im = cap.read()
            if not ok:
                break
            frames.append(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
        cap.release()
        for ax, index in zip(axes[row], [0, 8, 16, 24, 32]):
            ax.imshow(frames[index]); ax.axis('off')
            ax.set_title(('Real endpoint' if index in [0, 32] else 'Procedural frame') + f' / {index}')
        axes[row, 0].text(-.08, .5, '044 → 047' if row == 0 else '033 → 034',
                          rotation=90, va='center', ha='right', transform=axes[row, 0].transAxes)
    fig.suptitle('Completed baseline: real endpoint images + procedurally rendered intermediate views\nThese are not learned diffusion outputs', fontsize=16)
    fig.savefig(out / 'video_contact_sheet.png', dpi=170); plt.close(fig)

    data = np.load(ROOT / 'mid036_model/integrated_grid.npz')
    xy, z, labels = data['xy_m'], data['height_m'], data['labels']
    cmap = ListedColormap(COLORS)
    norm = BoundaryNorm(np.arange(-.5, 5), len(COLORS))
    fig, ax = plt.subplots(figsize=(10, 7), layout='constrained')
    ax.pcolormesh(xy[:, :, 0], xy[:, :, 1], labels, cmap=cmap, norm=norm, shading='nearest')
    for name in ['endpoint_A_footprint', 'endpoint_B_footprint']:
        ax.contour(xy[:, :, 0], xy[:, :, 1], data[name], levels=[.5], colors=['#333333'], linewidths=.7)
    ax.set(xlabel='Start-rover local X (m)', ylabel='Start-rover local Y (m)', aspect='equal',
           title='033 → 034: source of completed terrain\n~50 m² envelope; pose is conditional on mobility assumptions')
    names = ['Strict stereo', 'Gated relaxed stereo', 'Synthetic video consensus', 'Linear interpolation']
    ax.legend(handles=[Patch(color=COLORS[i], label=names[i-1]) for i in range(1, 5)], loc='upper left')
    fig.savefig(out / 'terrain_provenance.png', dpi=180); plt.close(fig)

    fig = plt.figure(figsize=(11, 7), layout='constrained')
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(xy[:, :, 0], xy[:, :, 1], z, facecolors=cmap(norm(labels)),
                    rstride=2, cstride=2, shade=True, linewidth=0, antialiased=False)
    ax.set(xlabel='X (m)', ylabel='Y (m)', zlabel='Z (m)',
           title='Integrated upper surface: 033 → 034\nBlue = stereo; orange = video; gray = interpolated')
    ax.set_box_aspect([np.ptp(xy[:, :, 0]), np.ptp(xy[:, :, 1]), np.nanmax(z)-np.nanmin(z)])
    ax.set_zticks([0, .6, 1.2])
    ax.view_init(elev=38, azim=-65)
    fig.savefig(out / 'terrain_surface.png', dpi=180); plt.close(fig)

    metrics = json.loads((ROOT / 'holdout046_model/metrics.json').read_text())['holdout']
    keys = ['consensus_video_m', 'same_cell_idw_m', 'same_cell_linear_m']
    values = [100 * metrics[k]['rmse'] for k in keys]
    fig, ax = plt.subplots(figsize=(9, 5), layout='constrained')
    bars = ax.bar(['Procedural video\nreconstruction', 'Inverse-distance\ninterpolation', 'Linear\ninterpolation'],
                  values, color=[COLORS[3], '#858a94', '#236b8e'], width=.6)
    ax.bar_label(bars, labels=[f'{v:.2f} cm' for v in values], padding=6, fontsize=14)
    ax.set(ylim=(0, max(values)*1.22), ylabel='Height RMSE vs withheld stereo (cm)',
           title=f'044 → 047, with observation 046 withheld\nSame {metrics[keys[0]]["count"]} cells compared; lower is better')
    fig.text(.5, .015, 'Reference is registered stereo, not surveyed ground truth. Only 85 of 561 eligible gap cells scored.',
             ha='center', fontsize=10)
    fig.get_layout_engine().set(rect=(0, .07, 1, .93))
    fig.savefig(out / 'heldout_error.png', dpi=180); plt.close(fig)
    print(out)


if __name__ == '__main__':
    main()
