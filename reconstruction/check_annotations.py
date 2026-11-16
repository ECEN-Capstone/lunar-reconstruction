"""Synthetic geometry and annotation persistence checks; no invented lunar labels."""
import copy
import tempfile
from pathlib import Path
import numpy as np
from .geometry import camera, rectification
from .annotation_geometry import triangulate
from . import annotate


def main():
    cl, _ = camera('left'); _, r, _, _ = rectification()
    expected = np.array([30., 25., 2500.]); world = expected @ r + cl
    pixels = []
    for side in ('left', 'right'):
        c, m = camera(side); q = m @ (world-c); pixels.append((q[:2]/q[2]).tolist())
    st = triangulate(*pixels)
    assert st['status'] == 'accepted', st
    np.testing.assert_allclose(st['xyz_rectified_left_m'], expected/1000, atol=1e-8)
    wrong = [pixels[1][0], pixels[1][1]+20]
    assert triangulate(pixels[0], wrong)['status'] == 'rejected'
    assert triangulate(pixels[1], pixels[0])['status'] == 'rejected'
    client = annotate.app.test_client()
    assert client.get('/').status_code == 200
    assert client.get('/api/pairs').status_code == 200
    assert client.get('/api/image/obs_034/NR/left').status_code == 200
    obj = dict(id=1, **{'class': 'rock'}, landmark='rock_contact',
               left=dict(base=pixels[0], prompts=[], runs=[[3, 4, 8]]),
               right=dict(base=pixels[1], prompts=[], runs=[]))
    d = dict(observation='obs_034', family='NR', objects=[obj])
    assert client.post('/api/preview', json=d).json['objects'][0]['stereo']['status'] == 'accepted'
    unpaired = copy.deepcopy(d); unpaired['objects'][0]['right']['base'] = None
    assert client.post('/api/preview', json=unpaired).json['objects'][0]['stereo']['status'] == 'unpaired'
    bad = copy.deepcopy(d); bad['objects'][0]['left']['base'] = [-1, 0]
    assert client.post('/api/preview', json=bad).status_code == 400
    original_output = annotate.OUTPUT
    try:
        with tempfile.TemporaryDirectory() as tmp:
            annotate.OUTPUT = Path(tmp)
            saved = client.post('/api/save', json=d)
            assert saved.status_code == 200, saved.data
            path = Path(saved.json['path'])
            assert (path/'landmarks.csv').exists() and (path/'overlay_left.png').exists()
            restored = client.get('/api/session/obs_034/NR').json
            assert restored['objects'][0]['left']['base'] == pixels[0]
            assert restored['source_images']['left']['sha256']
    finally:
        annotate.OUTPUT = original_output
    print('PASS: metric CAHV round trip, mismatch/negative-depth rejection, native pixel bounds, unpaired points, image API, export and resume')


if __name__ == '__main__':
    main()
