"""Read exported binary PLYs back, verify topology, and render actual exported faces."""
import argparse
import json
import hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from .geometry import ROOT


def read_ply(path):
    """Read this project's deliberately simple binary vertex/color/triangle format."""
    with path.open('rb') as f:
        header=[]
        while True:
            line=f.readline().decode('ascii').strip();header.append(line)
            if line=='end_header':break
            if not line:raise ValueError('Invalid PLY header')
        nv=int(next(s.split()[-1] for s in header if s.startswith('element vertex')))
        nf=int(next((s.split()[-1] for s in header if s.startswith('element face')),'0'))
        verts=np.fromfile(f,dtype=[('p','<f4',(3,)),('c','u1',(3,))],count=nv)
        faces=np.fromfile(f,dtype=[('n','u1'),('v','<i4',(3,))],count=nf)
        assert len(verts)==nv and len(faces)==nf and not f.read(1)
        assert np.isfinite(verts['p']).all()
        if nf:assert (faces['n']==3).all() and faces['v'].min()>=0 and faces['v'].max()<nv
    return verts['p'],verts['c'],faces['v']


def render_mesh(path,out):
    v,c,f=read_ply(path);tri=v[f]
    area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
    assert (area>0).all()
    fig=plt.figure(figsize=(13,6));ax=fig.add_subplot(121,projection='3d')
    # Reorder axes for display only: right / forward / up. Export remains x/y/z.
    display=tri[:,:,[0,2,1]].copy();display[:,:,2]*=-1
    gray=c[f].mean(axis=1)/255.
    poly=Poly3DCollection(display,facecolors=gray,edgecolors='none',rasterized=True)
    ax.add_collection3d(poly)
    lo=np.min(display.reshape(-1,3),axis=0);hi=np.max(display.reshape(-1,3),axis=0)
    ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),zlim=(lo[2],hi[2]),xlabel='X right',ylabel='Z forward',zlabel='-Y (not gravity up)')
    ax.set_box_aspect(np.maximum(hi-lo,1));ax.view_init(30,-65)
    ax.set_title(f'Exported mesh: {len(f):,} observed triangles')
    ax=fig.add_subplot(122);ax.tripcolor(v[:,0],v[:,2],f,facecolors=c[f].mean(axis=(1,2)),cmap='gray',vmin=0,vmax=255)
    ax.set_aspect('equal');ax.set(xlabel='X (calibration units)',ylabel='Z (calibration units)',title='Mesh top projection; holes preserved')
    fig.suptitle(path.parent.name+' | CAHV source units; scale and gravity unresolved')
    fig.tight_layout();fig.savefig(out,dpi=150);plt.close(fig)
    return dict(vertices=len(v),triangles=len(f),minimum_triangle_area_calibration_units_squared=float(area.min()))


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',default='r11_filtered_batch');p.add_argument('--registration',default='r12_registration');args=p.parse_args()
    checks=[]
    for root in [ROOT/'artifacts/runs'/args.batch,ROOT/'artifacts/runs'/args.registration]:
        for path in root.rglob('*.ply'):
            v,c,f=read_ply(path);checks.append(dict(path=path.relative_to(ROOT).as_posix(),vertices=len(v),faces=len(f),finite=True))
    source=json.loads((ROOT/'artifacts/investigation/inventory.json').read_text())
    changed=[r['path'] for r in source if hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()!=r['sha256']]
    assert not changed,changed
    result=dict(ply_checks=checks,source_files_rehashed=len(source),changed_source_files=changed)
    for obs in ['obs_003','obs_029','obs_034','obs_040']:
        path=ROOT/'artifacts/runs'/args.batch/obs/'local_mesh_calibration_units.ply'
        if path.exists():result[obs]=render_mesh(path,path.parent/'mesh_views.png')
    (ROOT/'artifacts/investigation/output_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(validated_ply_files=len(checks),source_files_unchanged=len(source))))


if __name__=='__main__':main()
