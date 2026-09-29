"""Numerical camera round-trip and synthetic stereo tests, no scene ground truth."""
import json
import numpy as np
import cv2
from .geometry import ROOT, camera, decompose, rectification, transform_pixels
from .stereo import disparity


def main():
    K,R,B,H=rectification(); cl,_=camera('left')
    rng=np.random.default_rng(42)
    xyz=np.column_stack([rng.uniform(-200,200,500),rng.uniform(-100,100,500),rng.uniform(1000,5000,500)])
    world=xyz@R+cl
    images=[]; max_reconstruction=0
    for side,h in zip(['left','right'],H):
        c,m=camera(side);k,r=decompose(m)
        assert np.max(abs(m/m[2].dot(m[2])**.5-k@r))<1e-8
        q=(world-c)@m.T;uv=q[:,:2]/q[:,2,None]
        rect=transform_pixels(uv,h);images.append(rect)
    a,b=images;z=K[0,0]*B/(a[:,0]-b[:,0])
    recovered=np.column_stack([(a[:,0]-K[0,2])*z/K[0,0],(a[:,1]-K[1,2])*z/K[1,1],z])
    assert abs(a[:,1]-b[:,1]).max()<1e-8
    assert abs(recovered-xyz).max()<1e-8
    cfg=json.loads((ROOT/'configs/terrain.json').read_text());cfg['num_disparities']=64;cfg['speckle_window_size']=0
    left=rng.integers(0,256,(128,320),dtype=np.uint8);right=np.zeros_like(left);right[:,:-24]=left[:,24:]
    dl=disparity(left,right,cfg);dr=disparity(right,left,cfg,True)
    assert np.median(dl[10:-10,80:-80])==24
    assert np.median(dr[10:-10,80:-80])==-24
    results=dict(max_vertical_roundtrip_error_px=float(abs(a[:,1]-b[:,1]).max()),max_3d_roundtrip_error_calibration_units=float(abs(recovered-xyz).max()),synthetic_disparity_left_px=24,synthetic_disparity_right_px=-24)
    (ROOT/'artifacts/investigation/geometry_tests.json').write_text(json.dumps(results,indent=2));print(results)


if __name__=='__main__':main()
