"""Geometric regression checks for terrain interpolation and exported surfaces."""
import tempfile
from pathlib import Path
import numpy as np
from .complete_terrain import interpolate, export_mesh, grid_cloud
from .geometry import camera, rectification


def main():
    x,y=np.meshgrid(np.arange(-1,1.01,.05),np.arange(-1,1.01,.05),indexing='ij')
    xy=np.stack([x,y],-1);height=.08*x-.03*y+.2
    removed=x*x+y*y<.35**2
    recovered,distance,inside=interpolate(xy[~removed],height[~removed],xy[removed])
    assert inside.all() and np.max(abs(recovered-height[removed]))<1e-12
    outside,_,inside=interpolate(xy[~removed],height[~removed],np.array([[2.,2.]]))
    assert not inside[0] and np.isnan(outside[0])
    # Verify inverse camera transform and mm -> m conversion with a known plane.
    _,r,_,_=rectification();cl,_=camera('left')
    source=np.array([[1.01,.01,.12],[1.02,.02,.12],[1.01,.06,.12],[1.02,.07,.12]])
    rect=((source*1000-cl)@r.T).reshape(2,2,3)
    cfg=dict(grid_m=.05,forward_bounds_m=[1.,1.1],lateral_bounds_m=[0,.1],minimum_points_per_cell=2)
    h,n,_=grid_cloud(rect,dict(R_rectified_from_source=r.tolist()),cfg)
    assert np.isfinite(h).sum()==2 and np.allclose(h[np.isfinite(h)],.12)
    with tempfile.TemporaryDirectory() as tmp:
        result=export_mesh(Path(tmp)/'plane.obj',height,xy,np.ones(height.shape,np.uint8))
        assert abs(result['projected_surface_area_m2']-4)<1e-10
        assert abs(result['slopes_deg']['maximum']-np.degrees(np.arctan(np.hypot(.08,.03))))<1e-10
    print('PASS: planar hole recovery, outside-hull rejection, CAHV metre transform, OBJ readback, winding and area.')


if __name__=='__main__':
    main()
