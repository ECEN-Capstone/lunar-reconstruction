"""Sparse native-image stereo points using the repository's literal CAHV model."""
import cv2
import numpy as np
from .geometry import camera, rectification, transform_pixels


def triangulate(left, right, max_error_px=2.0):
    a, b = np.asarray(left, float), np.asarray(right, float)
    if a.shape != (2,) or b.shape != (2,) or not np.isfinite([a, b]).all():
        raise ValueError('Expected two finite native-image (x, y) points')
    cl, ml = camera('left'); cr, mr = camera('right')
    pl = ml @ np.column_stack((np.eye(3), -cl))
    pr = mr @ np.column_stack((np.eye(3), -cr))
    q = cv2.triangulatePoints(pl, pr, a[:, None], b[:, None])[:, 0]
    if abs(q[3]) < 1e-12:
        return dict(status='rejected', reason='Parallel rays')
    xyz = q[:3] / q[3]
    errors, forward = [], []
    for c, m, uv in [(cl, ml, a), (cr, mr, b)]:
        p = m @ (xyz-c)
        forward.append(p[2] > 0)
        errors.append(float(np.linalg.norm(p[:2]/p[2]-uv)))
    _, r, _, h = rectification()
    epipolar = float(abs(transform_pixels([a], h[0])[0, 1]-transform_pixels([b], h[1])[0, 1]))
    accepted = all(forward) and max(errors) <= max_error_px and epipolar <= max_error_px
    return dict(status='accepted' if accepted else 'rejected',
                reason='' if accepted else 'Behind camera or stereo residual exceeds threshold',
                xyz_rectified_left_m=((xyz-cl) @ r.T / 1000).tolist() if accepted else None,
                reprojection_error_px=errors, epipolar_error_px=epipolar,
                frame='rectified left camera: x right, y down, z forward',
                scale='CAHV millimetres converted to metres; absolute accuracy unverified')
