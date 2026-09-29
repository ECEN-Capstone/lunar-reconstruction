"""Transform accepted component meshes into one frame without inventing surfaces.

This is an observed triangle union, not a watertight collision mesh. Overlapping
triangles are retained, not welded or surface-fitted across uncertain samples.
"""
import argparse
import json
import numpy as np
from .geometry import ROOT,write_ply
from .inspect_outputs import read_ply,render_mesh


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',default='r11_filtered_batch');p.add_argument('--registration',default='r12_registration');args=p.parse_args()
    base=ROOT/'artifacts/runs'/args.batch;reg=ROOT/'artifacts/runs'/args.registration;summary=[]
    for component in sorted(reg.glob('component_*')):
        poses=json.loads((component/'camera_trajectory.json').read_text())['T_component_from_camera']
        vertices=[];colors=[];faces=[];offset=0;ranges=[]
        for obs,matrix in poses.items():
            v,c,f=read_ply(base/obs/'local_mesh_calibration_units.ply');T=np.array(matrix)
            vertices.append(v@T[:3,:3].T+T[:3,3]);colors.append(c);faces.append(f+offset)
            ranges.append(dict(observation=obs,vertex_start=offset,vertex_count=len(v),face_count=len(f)));offset+=len(v)
        v,c,f=np.concatenate(vertices),np.concatenate(colors),np.concatenate(faces)
        ply=component/'mesh_observed_union_calibration_units.ply'
        if ply.exists():raise FileExistsError(ply)
        write_ply(ply,v,c,f)
        with (component/'mesh_observed_union_calibration_units.obj').open('w') as out:
            out.write('# Observed triangle union; overlaps and holes preserved. CAHV source units, unknown gravity.\n')
            for point in v:out.write('v %.6f %.6f %.6f\n'%tuple(point))
            for face in f:out.write('f %d %d %d\n'%tuple(face+1))
        record=dict(component=component.name,vertices=len(v),triangles=len(f),sources=ranges,
            limitations=['overlapping triangles retained','holes unfilled','not watertight','not metric certified','not collision ready'])
        (component/'mesh_provenance.json').write_text(json.dumps(record,indent=2));summary.append(record)
    (reg/'mesh_assemblies.json').write_text(json.dumps(summary,indent=2))
    if summary:
        best=max(summary,key=lambda r:r['triangles']);d=reg/best['component'];render_mesh(d/'mesh_observed_union_calibration_units.ply',d/'mesh_views.png')
    print(json.dumps([dict(component=r['component'],triangles=r['triangles']) for r in summary]))


if __name__=='__main__':main()
