"""Render all exported experimental meshes without changing their geometry."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from .close_terrain import read_obj
from .geometry import ROOT


def panel(ax, vertices, faces, title):
    display = vertices[:, [0, 2, 1]].copy()
    display[:, 2] *= -1
    triangles = display[faces]
    normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    light = np.array([-.35, -.45, .82])
    light /= np.linalg.norm(light)
    # Two-sided shading makes disconnected and back-facing fragments visible.
    shade = .35 + .65 * np.abs(normals @ light)
    colors = shade[:, None] * np.array([.40, .72, .88])
    ax.add_collection3d(Poly3DCollection(triangles, facecolors=colors,
                                       edgecolors='none', rasterized=True))
    lo, hi = display.min(axis=0), display.max(axis=0)
    extent = np.maximum(hi-lo, .01)
    pad = extent * .025
    ax.set(xlim=(lo[0]-pad[0], hi[0]+pad[0]),
           ylim=(lo[1]-pad[1], hi[1]+pad[1]),
           zlim=(lo[2]-pad[2], hi[2]+pad[2]),
           xlabel='X', ylabel='Forward', zlabel='Up', title=title)
    ax.set_box_aspect(extent)
    ax.view_init(elev=24, azim=-65)
    ax.tick_params(labelsize=7, pad=0)
    ax.xaxis.label.set_size(8)
    ax.yaxis.label.set_size(8)
    ax.zaxis.label.set_size(8)
    ax.title.set_fontsize(11)


def main():
    root = ROOT/'output/uber_relaxed/stereo_trial_1'
    out = root/'renders'
    out.mkdir(exist_ok=True)
    results = json.loads((root/'results.json').read_text())
    overview = plt.figure(figsize=(20, 11), layout='constrained')
    for i, record in enumerate(results['profiles']):
        name = record['profile']['name']
        vertices, faces = read_obj(root/name/'uber_relaxed.obj')
        title = name.replace('uber_relaxed', 'uber').replace('_', ' ')
        title += f'\n{len(faces):,} triangles'
        panel(overview.add_subplot(2, 4, i+1, projection='3d'), vertices, faces, title)
        fig = plt.figure(figsize=(10, 8), layout='constrained')
        panel(fig.add_subplot(projection='3d'), vertices, faces, title)
        fig.suptitle('Trial 1 | complete exported geometry | arbitrary units', fontsize=12)
        fig.savefig(out/f'{name}.png', dpi=160)
        plt.close(fig)
        print(name, flush=True)
    key = overview.add_subplot(2, 4, 8)
    key.axis('off')
    key.text(.05, .85, 'Trial 1: all seven meshes', fontsize=18, weight='bold')
    key.text(.05, .66, 'Same viewing angle; each panel fits its full mesh.\n'
             'Axis scales differ between panels.\n\n'
             'All exported triangles are shown.\n'
             'No smoothing, filling, or outlier removal.\n\n'
             'Blue is shaded geometry, not image texture.\n'
             'Coordinates use an arbitrary baseline of 1.',
             fontsize=12, va='top', linespacing=1.6)
    overview.suptitle('Uber relaxed — rendered mesh comparison', fontsize=22)
    overview.savefig(out/'all_seven_meshes.png', dpi=160)
    plt.close(overview)


if __name__ == '__main__':
    main()
