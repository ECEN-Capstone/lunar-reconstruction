"""CAHV projection without silently changing its scale, skew, or orientation."""
from pathlib import Path
import re
import numpy as np
import cv2

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / 'chandrayaan-3-documentation/nav/calibration'


def camera(side, interpretation='literal'):
    """Return center and 3x3 ray-to-pixel matrix in source calibration units."""
    text = (CAL / f'ch3_nav_{side}_cahv.txt').read_text()
    vectors = {k: np.fromstring(re.search(rf'^{k}\s*=([^\n]+)', text, re.M)[1], sep=' ')
               for k in 'CAHV'}
    if interpretation == 'normalize_axis_only':
        vectors['A'] /= np.linalg.norm(vectors['A'])
    elif interpretation != 'literal':
        raise ValueError(interpretation)
    return vectors['C'], np.stack([vectors['H'], vectors['V'], vectors['A']])


def decompose(matrix):
    """RQ decomposition preserves skew; normalize the entire projective matrix."""
    _, K, R, *_ = cv2.RQDecomp3x3(matrix)
    K = K / K[2, 2]
    assert np.linalg.det(R) > 0.999
    return K, R


def rectification(size=(1024, 1024), interpretation='literal'):
    """Construct shared virtual camera with x along the measured rig baseline.

    Virtual intrinsics define only the output canvas. Homographies preserve all
    original rays, including nonzero skew in the supplied CAHV model.
    """
    cl, ml = camera('left', interpretation)
    cr, mr = camera('right', interpretation)
    kl, _ = decompose(ml)
    kr, _ = decompose(mr)
    x = cr-cl
    baseline = np.linalg.norm(x)
    x /= baseline
    z = ml[2]/np.linalg.norm(ml[2]) + mr[2]/np.linalg.norm(mr[2])
    z -= x * np.dot(x, z)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    R = np.stack([x, y, z])
    f = float(np.mean([kl[0, 0], kl[1, 1], kr[0, 0], kr[1, 1]]))
    K = np.array([[f, 0, (size[0]-1)/2], [0, f, (size[1]-1)/2], [0, 0, 1.]])
    homographies = [K @ R @ np.linalg.inv(m) for m in (ml, mr)]
    return K, R, baseline, homographies


def warp(image, H):
    return cv2.warpPerspective(image, H, (image.shape[1], image.shape[0]), flags=cv2.INTER_LINEAR)


def transform_pixels(points, H):
    return cv2.perspectiveTransform(np.asarray(points, np.float64).reshape(-1, 1, 2), H).reshape(-1, 2)


def write_ply(path, points, colors, faces=None):
    """Binary PLY, explicitly labelled calibration units; no invented metre scale."""
    points = np.asarray(points, np.float32)
    colors = np.asarray(colors, np.uint8)
    if colors.ndim == 1:
        colors = np.repeat(colors[:, None], 3, axis=1)
    header = ('ply\nformat binary_little_endian 1.0\n'
              'comment coordinates in source CAHV calibration units; metre conversion unverified\n'
              f'element vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\n'
              'property uchar red\nproperty uchar green\nproperty uchar blue\n')
    if faces is not None:
        header += f'element face {len(faces)}\nproperty list uchar int vertex_indices\n'
    vertices = np.empty(len(points), dtype=[('p','<f4',(3,)), ('c','u1',(3,))])
    vertices['p'], vertices['c'] = points, colors
    with open(path, 'wb') as out:
        out.write((header+'end_header\n').encode('ascii'))
        vertices.tofile(out)
        if faces is not None:
            records = np.empty(len(faces), dtype=[('n','u1'), ('v','<i4',(3,))])
            records['n'], records['v'] = 3, faces
            records.tofile(out)
