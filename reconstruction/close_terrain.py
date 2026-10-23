"""Close a terrain height surface with walls and a flat base for mesh viewers.

Preserves all top vertices and faces. Added walls/base are artificial packaging,
not reconstructed lunar geometry. Exports metres to OBJ and binary STL.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct

import numpy as np

from .geometry import ROOT


def read_obj(path):
    vertices,faces=[],[]
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields:
            continue
        if fields[0]=='v':
            vertices.append([float(x) for x in fields[1:4]])
        elif fields[0]=='f':
            if len(fields)!=4:
                raise ValueError('Expected triangulated OBJ')
            faces.append([int(x.split('/')[0])-1 for x in fields[1:]])
    return np.asarray(vertices),np.asarray(faces,dtype=np.int64)


def edges_of(faces):
    directed=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    edges,first,counts=np.unique(np.sort(directed,axis=1),axis=0,return_index=True,return_counts=True)
    return edges,counts,directed[first[counts==1]]


def validate(vertices,faces):
    assert vertices.ndim==2 and vertices.shape[1]==3 and np.isfinite(vertices).all()
    assert faces.ndim==2 and faces.shape[1]==3 and faces.min()>=0 and faces.max()<len(vertices)
    assert len(np.unique(vertices,axis=0))==len(vertices), 'Duplicate positions'
    assert len(np.unique(np.sort(faces,axis=1),axis=0))==len(faces), 'Duplicate triangles'
    assert len(np.unique(faces))==len(vertices), 'Unused vertices'
    tri=vertices[faces]
    normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    assert (np.linalg.norm(normal,axis=1)>1e-12).all(), 'Degenerate triangles'
    edges,counts,_=edges_of(faces)
    assert (counts==2).all(), 'Open or nonmanifold edges'
    directed=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    # Each undirected edge must occur once in each direction.
    assert len(np.unique(directed,axis=0))==len(directed), 'Inconsistent winding'
    adjacency=defaultdict(set)
    for a,b in edges:
        adjacency[int(a)].add(int(b));adjacency[int(b)].add(int(a))
    visited={0};pending=[0]
    while pending:
        for b in adjacency[pending.pop()]:
            if b not in visited:
                visited.add(b);pending.append(b)
    assert len(visited)==len(vertices), 'Disconnected solid'
    # A two-manifold vertex has a single cycle of incident neighbor links.
    links=defaultdict(list)
    for a,b,c in faces:
        links[int(a)].append((int(b),int(c)))
        links[int(b)].append((int(c),int(a)))
        links[int(c)].append((int(a),int(b)))
    for pairs in links.values():
        ring=defaultdict(set)
        for a,b in pairs:
            ring[a].add(b);ring[b].add(a)
        assert all(len(n)==2 for n in ring.values()), 'Nonmanifold vertex'
        start=next(iter(ring));seen={start};pending=[start]
        while pending:
            for b in ring[pending.pop()]:
                if b not in seen:
                    seen.add(b);pending.append(b)
        assert len(seen)==len(ring), 'Pinched vertex'
    volume=float(np.einsum('ij,ij->i',tri[:,0],np.cross(tri[:,1],tri[:,2])).sum()/6)
    assert volume>0, 'Negative or zero enclosed volume'
    euler=len(vertices)-len(edges)+len(faces)
    assert euler==2, 'Expected a single closed terrain block without tunnels'
    return dict(vertices=len(vertices),triangles=len(faces),boundary_edges=0,
                nonmanifold_edges=0,nonmanifold_vertices=0,connected_components=1,
                euler_characteristic=euler,consistent_outward_winding=True,
                enclosed_volume_m3=volume,dimensions_m=np.ptp(vertices,axis=0).tolist())


def close_surface(vertices,faces,base_clearance):
    if base_clearance<=0:
        raise ValueError('Base clearance must be positive')
    # Discard isolated unused input vertices; retain exact face geometry.
    used=np.unique(faces);index=np.full(len(vertices),-1);index[used]=np.arange(len(used))
    vertices=vertices[used];faces=index[faces]
    top=vertices[faces]
    assert (np.cross(top[:,1]-top[:,0],top[:,2]-top[:,0])[:,2]>0).all(), 'Expected upward height surface'
    _,counts,boundary=edges_of(faces)
    assert counts.max()<=2 and len(boundary)>0
    n=len(vertices);bottom=vertices.copy();bottom[:,2]=vertices[:,2].min()-base_clearance
    walls=[]
    for a,b in boundary:
        walls.extend([[a,a+n,b+n],[a,b+n,b]])
    result_v=np.concatenate([vertices,bottom])
    result_f=np.concatenate([faces,faces[:,::-1]+n,np.asarray(walls)])
    return result_v,result_f,len(boundary),float(bottom[0,2])


def write_obj(path,vertices,faces):
    with path.open('w',newline='\n') as out:
        out.write('# Units: metres. Scale 1. Nominal rover-local Z up.\n')
        out.write('# Original completed top; artificial closure walls and base.\n')
        out.write('o closed_lunar_terrain\n')
        for v in vertices:
            out.write('v %.9f %.9f %.9f\n'%tuple(v))
        for face in faces:
            out.write('f %d %d %d\n'%tuple(face+1))


def write_stl(path,vertices,faces):
    tri=vertices[faces]
    normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    normal/=np.linalg.norm(normal,axis=1)[:,None]
    records=np.zeros(len(faces),dtype=[('normal','<f4',(3,)),('triangle','<f4',(3,3)),('attribute','<u2')])
    records['normal']=normal;records['triangle']=tri
    with path.open('wb') as out:
        out.write(b'Closed lunar terrain; coordinates in metres; artificial walls/base'.ljust(80,b' '))
        out.write(struct.pack('<I',len(faces)));records.tofile(out)
    with path.open('rb') as src:
        src.read(80);count=struct.unpack('<I',src.read(4))[0]
        reread=np.fromfile(src,dtype=records.dtype,count=count)
        assert count==len(faces) and not src.read(1)
    points,ids=np.unique(reread['triangle'].reshape(-1,3),axis=0,return_inverse=True)
    return validate(points.astype(float),ids.reshape(-1,3))


def export(source,out,clearance):
    original_v,original_f=read_obj(source)
    v,f,boundary,base=close_surface(original_v,original_f,clearance)
    checks=validate(v,f)
    out.mkdir(parents=True,exist_ok=False)
    obj=out/'terrain_closed_m.obj';stl=out/'terrain_closed_m.stl'
    write_obj(obj,v,f)
    rv,rf=read_obj(obj);validate(rv,rf)
    assert np.array_equal(rv[rf[:len(original_f)]],original_v[original_f]), 'Changed top geometry'
    stl_checks=write_stl(stl,v,f)
    report=dict(source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                original_boundary_edges=boundary,artificial_base_z_m=base,base_clearance_m=clearance,
                original_top_geometry_unchanged=True,obj=checks,stl=stl_checks,
                added_geometry='Vertical walls on every perimeter edge and planar underside',
                limitations=['Top still includes previously inferred terrain',
                  'Units are metres; STL format itself has no standard unit field',
                  'Nominal rover-local frame, gravity unverified',
                  'No validation in the user viewer or Gazebo'])
    (out/'validation.json').write_text(json.dumps(report,indent=2))
    (out/'README.txt').write_text(
        'Open terrain_closed_m.obj first. Binary STL is an alternative.\n'
        'Coordinates are in METRES. Import scale = 1.\n'
        'Closed, consistently oriented terrain block with no open edges.\n'
        'The terrain top is unchanged. Side walls and the flat bottom are artificial.\n'
        f'The bottom is {clearance:g} m below the lowest top vertex.\n'
        'Mesh topology verified after reading both exported formats back.\n'
        'Viewer compatibility and physics behavior have not been tested.\n')
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='output/closed_terrain')
    parser.add_argument('--base-clearance',type=float,default=.15)
    args=parser.parse_args()
    for obs,variant in [('obs_034','extended'),('obs_029','simulation')]:
        source=ROOT/'artifacts/runs/r15_terrain_completion'/obs/f'terrain_{variant}_m.obj'
        report=export(source,ROOT/args.output/obs,args.base_clearance)
        print(json.dumps(dict(observation=obs,**report)),flush=True)


if __name__=='__main__':
    main()
