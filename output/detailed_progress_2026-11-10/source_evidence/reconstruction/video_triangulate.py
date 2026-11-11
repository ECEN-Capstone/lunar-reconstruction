"""Reconstruct a fixed-optics video using only decoded frames, intrinsics and poses.
Does not read generator depths, texture maps, stereo endpoint clouds, or holdouts.
"""
from pathlib import Path
import cv2
import numpy as np


def decode(path, mask_path=None):
    reader=cv2.VideoCapture(str(path))
    if not reader.isOpened():
        raise ValueError(f'Cannot decode {path}')
    frames=[]
    try:
        while True:
            ok,im=reader.read()
            if not ok: break
            frames.append(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY))
    finally:
        reader.release()
    if mask_path is not None:
        masks=np.load(mask_path)['valid']
        if len(masks)!=len(frames) or any(m.shape!=f.shape for m,f in zip(masks,frames)):
            raise ValueError('Invalid support mask shape')
        frames=[np.where(m,f,0).astype('B') for f,m in zip(frames,masks)]
    return frames


def tracks(frames, poses, K):
    """Three-view tracks; triangulate outer views and test the middle observation."""
    if len(frames)!=len(poses) or len(frames)<5:
        raise ValueError('Each decoded frame needs a camera pose; at least five are required')
    P=np.asarray([(K@np.linalg.inv(t)[:3]) for t in poses])
    kw=dict(winSize=(25,25),maxLevel=4,
            criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,40,.01))
    points=[]; errors=[]; windows=0
    for start in range(1,len(frames)-5,3):
        for span in [6,12]:
            end=start+span
            if end>=len(frames)-1: continue
            if np.linalg.norm(poses[start,:3,3]-poses[end,:3,3])<.045: continue
            windows+=1
            im=frames[start]
            mask=cv2.erode((im>9).astype('B'), np.ones((7,7),'B'))
            uv=cv2.goodFeaturesToTrack(im,6500,.002,2,mask=mask)
            if uv is None: continue
            uv=uv[:,0]
            initial=uv.copy()
            mid=None
            for j in range(start,end):
                if len(uv)<3: break
                v,ok,_=cv2.calcOpticalFlowPyrLK(frames[j],frames[j+1],uv,None,**kw)
                back,ok2,_=cv2.calcOpticalFlowPyrLK(frames[j+1],frames[j],v,None,**kw)
                keep=(ok.ravel()!=0)&(ok2.ravel()!=0)&(np.linalg.norm(back-uv,axis=1)<.6)
                keep&=(v.min(1)>4)&(v[:,0]<im.shape[1]-5)&(v[:,1]<im.shape[0]-5)
                vv=np.rint(v).astype(int).clip([0,0],[im.shape[1]-1,im.shape[0]-1])
                keep&=frames[j+1][vv[:,1],vv[:,0]]>9
                initial,uv=initial[keep],v[keep]
                if mid is not None: mid=mid[keep]
                if j+1==start+span//2: mid=uv.copy()
            if len(uv)<3 or mid is None:continue
            X=cv2.triangulatePoints(P[start],P[end],initial.T.astype(float),uv.T.astype(float)).T
            ok=abs(X[:,3])>1e-10
            X=X/np.where(ok,X[:,3],1)[:,None]
            rays=[X[:,:3]-poses[k,:3,3] for k in (start,end)]
            angle=np.cross(*rays)
            sine=np.linalg.norm(angle,axis=1)/np.maximum(np.linalg.norm(rays[0],axis=1)*np.linalg.norm(rays[1],axis=1),1e-10)
            ok &= sine>np.sin(np.deg2rad(.45))
            err=np.zeros(len(X))
            for k,pixels in [(start,initial),(end,uv),(start+span//2,mid)]:
                q=X@P[k].T
                ok&=(q[:,2]>.4)&(q[:,2]<11)
                err=np.maximum(err,np.linalg.norm(q[:,:2]/np.maximum(q[:,2:],1e-10)-pixels,axis=1))
            ok&=err<.85
            points.append(X[ok,:3]);errors.append(err[ok])
    return (np.concatenate(points) if points else np.empty((0,3)),
            np.concatenate(errors) if errors else np.empty(0), windows)


def reconstruct(movie, trajectory, output, mask_path=None):
    data=np.load(trajectory)
    frames=decode(movie,mask_path)
    if any(f.shape!=tuple(data['frame_shape']) for f in frames):
        raise ValueError('Video resolution differs from camera calibration')
    p,err,windows=tracks(frames,data['T_world_from_camera'],data['K'])
    np.savez_compressed(output,xyz_m=p,reprojection_px=err)
    return p,err,windows


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['movie','trajectory','output']:parser.add_argument(key,type=Path)
    parser.add_argument("--mask",type=Path)
    args=parser.parse_args()
    print(len(reconstruct(args.movie,args.trajectory,args.output,args.mask)[0]),'video points')


def sweep(frames, poses, K, xy, z_limits):
    """Photometric height sweep, independent of generated height/texture.

    Each plane warps the same world grid into multiple decoded images. Reject
    untextured patches, bracket-edge minima, poor matches and ambiguous minima.
    A second competing height must be at least 8 cm away to count as distinct.
    """
    chosen=np.unique(np.linspace(1,len(frames)-2,7).round().astype(int))
    xy=xy.astype('f')
    maps=[]
    for i in chosen:
        im=frames[i].astype('f')
        mean=cv2.GaussianBlur(im,(0,0),4)
        std=np.sqrt(np.maximum(cv2.GaussianBlur(im**2,(0,0),4)-mean**2,1))
        norm=np.clip((im-mean)/np.maximum(std,5),-3,3)
        valid=cv2.erode((im>7).astype('B'),np.ones((7,7),'B')).astype('f')
        valid*=std>4
        P=(K@np.linalg.inv(poses[i])[:3]).astype('f')
        maps.append((norm,valid,xy@P[:,:2].T+P[:,3],P[:,2]))
    levels=np.arange(z_limits[0],z_limits[1]+.01,.01,dtype='f')
    costs=[]
    for z in levels:
        count=np.zeros(xy.shape[:2],'f')
        total=count.copy()
        squares=count.copy()
        for norm,valid,uv0,delta in maps:
            q=uv0+delta*z
            pix=q[:,:,:2]/np.maximum(q[:,:,2:],.01)
            use=(cv2.remap(valid,pix,None,cv2.INTER_NEAREST)>.5)&(q[:,:,2]>.4)&(q[:,:,2]<11)
            value=cv2.remap(norm,pix,None,cv2.INTER_LINEAR)
            count+=use
            total+=value*use
            squares+=value**2*use
        var=np.maximum(0,squares/np.maximum(count,1)-(total/np.maximum(count,1))**2)
        ok=(count>=4).astype('f')
        wt=cv2.GaussianBlur(ok,(3,3),.7)
        var=cv2.GaussianBlur(ok*var,(3,3),.7)/np.maximum(wt,.001)
        costs.append(np.where((ok>0)&(wt>.7),var,100))
    costs=np.stack(costs)
    k=costs.argmin(axis=0)
    x,y=np.indices(k.shape)
    best=costs[k,x,y]
    alt=np.where(abs(np.arange(len(levels))[:,None,None]-k)>=8,costs,100).min(axis=0)
    accept=(k>0)&(k<len(levels)-1)&(best<.18)&(alt<100)&(alt>best*1.45+.012)
    return np.where(accept,levels[k],np.nan)


