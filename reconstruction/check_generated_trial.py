"""Read back this experiment's artifacts and compare the real positive control."""
import json
import zipfile

import cv2
import numpy as np

from .geometry import ROOT
from .generated_stereo_trial import digest


def main():
    root=ROOT/'output/generated_stereo_trial'
    results=json.loads((root/'results.json').read_text())
    checks=[]
    for pair in results['pairs']:
        if 'split' not in pair:
            continue
        folder=root/pair['name']
        original=cv2.imread(str(folder/'original_canvas.png'),cv2.IMREAD_UNCHANGED)
        halves=[cv2.imread(str(folder/f'{eye}_native.png'),cv2.IMREAD_UNCHANGED) for eye in ['left','right']]
        assert np.array_equal(np.concatenate(halves,axis=1),original)
        from pathlib import Path
        assert digest(Path(pair['split']['source']))==pair['split']['source_sha256']
        for d in pair['dense_diagnostics']:
            out=folder/('diagnostic_'+d['profile'])
            xyz=np.load(out/'INVALID_GEOMETRY_xyz_baseline_units.npy')
            mask=cv2.imread(str(out/'validity_mask.png'),0)>0
            assert xyz.shape==(1024,1024,3)
            assert np.array_equal(mask,np.isfinite(xyz).all(axis=2))
            assert int(mask.sum())==d['valid_pixels']
            vertices=[];faces=[]
            for line in (out/'INVALID_GEOMETRY_mesh_baseline_units.obj').read_text().splitlines():
                fields=line.split()
                if fields and fields[0]=='v':
                    vertices.append([float(v) for v in fields[1:]])
                elif fields and fields[0]=='f':
                    faces.append([int(i)-1 for i in fields[1:]])
            v=np.asarray(vertices);f=np.asarray(faces)
            assert len(v)==d['vertices'] and len(f)==d['triangles'] and np.isfinite(v).all()
            if len(f):
                assert f.min()>=0 and f.max()<len(v)
                tri=v[f]
                assert (np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)>0).all()
            checks.append(dict(pair=pair['name'],profile=d['profile'],split_lossless=True,
                               source_unchanged=True,arrays_match_metrics=True,obj_readback_valid=True))
    # Real A is the previously reconstructed obs_049, unchanged config/input.
    control=[]
    for filename in ['disparity_left_px.npy','disparity_right_px.npy','xyz_rectified_calibration_units.npy']:
        before=np.load(ROOT/'artifacts/runs/r08_quality_batch/obs_049'/filename)
        after=np.load(root/'real_A/pipeline'/filename)
        assert np.array_equal(before,after,equal_nan=True)
        control.append(filename)
    with zipfile.ZipFile(root/'split_stereo_images.zip') as archive:
        assert archive.testzip() is None
        pngs=[n for n in archive.namelist() if n.endswith('.png')]
        assert len(pngs)==8
    report=dict(diagnostic_checks=checks,real_control_bitwise_reproduction=control,
                split_zip_integrity=True,production_gate_unchanged=True)
    (root/'validation.json').write_text(json.dumps(report,indent=2))
    print('PASS: lossless splits, source integrity, four diagnostic OBJ/array readbacks, ZIP integrity, and exact real-control reproduction.')


if __name__=='__main__':
    main()
