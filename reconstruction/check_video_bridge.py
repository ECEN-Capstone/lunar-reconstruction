"""Independent analytic scene tests for the renderer and inverse geometry."""
import cv2
import numpy as np
from .video_bridge import ray_hits,DX,trajectory
from .video_triangulate import tracks,sweep


def main():
    cv2.setNumThreads(3)
    y,x=np.indices((80,100),dtype='f')
    height=.13*x*DX+.09*y*DX
    v,u=np.indices((60,80),dtype='f')
    ray=np.stack([(u-40)/150,(v-30)/150,-np.ones_like(u)],-1)
    for sign in [-1,1]:
        origin=np.array([2,2,.44+sign*1.5])
        ray[:,:,2]=-sign
        t,mask=ray_hits(ray,origin,np.zeros(2,'f'),height,np.ones_like(height))
        truth=(.13*origin[0]+.09*origin[1]-origin[2])/(ray[:,:,2]-.13*ray[:,:,0]-.09*ray[:,:,1])
        assert mask.mean()>.98 and np.max(abs(t[mask]-truth[mask]))<.005
    n=256;f=260;zc=2.;K=np.array([[f,0,127.5],[0,f,127.5],[0,0,1]])
    poses=np.repeat(np.eye(4)[None],25,axis=0);poses[:,0,3]=np.linspace(-.18,.18,25)
    rng=np.random.default_rng(441)
    tex=cv2.GaussianBlur(rng.normal(115,45,(600,600)).astype('f'),(3,3),.6)
    v,u=np.indices((n,n),dtype='f')
    images=[]
    for T in poses:
        X=zc*(u-127.5)/f+T[0,3];Y=zc*(v-127.5)/f
        images.append(np.clip(cv2.remap(tex,(300+180*X).astype('f'),(300+180*Y).astype('f'),cv2.INTER_LINEAR),0,255).astype('B'))
    p,e,_=tracks(images,poses,K)
    assert len(p)>500 and np.percentile(abs(p[:,2]-zc),90)<.025
    xy=np.stack(np.meshgrid(np.arange(-.65,.66,.025),np.arange(-.65,.66,.025),indexing='ij'),-1)
    dense=sweep(images,poses,K,xy,[1.65,2.35])
    assert np.isfinite(dense).mean()>.7 and np.nanpercentile(abs(dense-zc),90)<.03
    A,B=poses[[0,-1]]
    out=trajectory(A,B,False)
    np.testing.assert_allclose(out[[0,-1]],[A,B],atol=1e-12)
    print(f'Analytic uphill/downhill ray hits passed; {len(p)} tracks, triangulation p90 {np.percentile(abs(p[:,2]-zc),90):.4f} m; dense p90 {np.nanpercentile(abs(dense-zc),90):.4f} m.')


if __name__=='__main__':main()

