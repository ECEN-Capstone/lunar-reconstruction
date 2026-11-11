"""Test tilt/elevation refinements to a planar mobility hypothesis.
The patch correspondence is conditional on commanded XY/yaw; it cannot prove them.
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation


def refine_height(pa, pb, B):
    # Spatially distinct 10 cm bins; use cell medians, not individual pixels as votes.
    def cells(p):
        ids,rev=np.unique(np.floor(p[:,:2]/.1).astype(int),axis=0,return_inverse=True)
        sums=np.bincount(rev)
        order=np.lexsort((p[:,2],rev))
        median=order[np.cumsum(sums)-1-sums//2]
        return p[median][sums>=3]
    a,b=cells(pa),cells(pb)
    if len(a)<80 or len(b)<80:return B,dict(accepted=False,reason='too few stereo cells')
    tree=cKDTree(a[:,:2])
    d,ix=tree.query(b[:,:2])
    pairs=b[d<.085]
    if len(pairs)<80:return B,dict(accepted=False,reason='insufficient shared footprint',cells=len(pairs))
    blocks=np.floor(pairs[:,:2]/.45).astype(int)
    test=(blocks[:,0]+2*blocks[:,1])%4==0
    if test.sum()<20 or (~test).sum()<50:return B,dict(accepted=False,reason='insufficient spatial holdout')
    center=B[:3,3]
    # Each current correspondence gets a local tangent fit; then minimize its
    # point-to-plane residual, so a vertical tilt can also shift points in XY.
    near=tree.query(pairs[:,:2],k=10)[1]
    neighbors=a[near]
    design=np.concatenate([neighbors[:,:,:2]-pairs[:,None,:2],np.ones((*near.shape,1))],axis=-1)
    planes=np.array([np.linalg.lstsq(x,n[:,2],rcond=None)[0] for x,n in zip(design,neighbors)])
    def shifted(params):
        rot=Rotation.from_rotvec([*params[:2],0]).as_matrix()
        return (pairs-center)@rot.T+center+[0,0,params[2]]
    def diff(params):
        q=shifted(params)
        return q[:,2]-planes[:,2]-((q[:,:2]-pairs[:,:2])*planes[:,:2]).sum(1)
    # Overlap may be several metres ahead of the camera; tilt and elevation
    # can trade off there and put the camera underground. Estimate the ground
    # below B independently from A and from the near field of B. Use a wide
    # clearance interval rather than treating either plane as surveyed.
    def ground_at(p):
        order=np.argsort(np.linalg.norm(p[:,:2]-center[:2],axis=1))[:50]
        local=p[order]
        M=np.column_stack([local[:,:2]-center[:2],np.ones(len(local))])
        coeff=least_squares(lambda c:M@c-local[:,2],np.zeros(3),loss='soft_l1',f_scale=.03).x
        return float(coeff[2]),float(np.linalg.norm(local[:,:2]-center[:2],axis=1).min())
    ha,da=ground_at(a);hb,db=ground_at(b)
    prior=ha-hb
    lo,hi=-1.5,1.5
    if da<.8 and db<1.5 and abs(prior)<1.35:
        lo,hi=prior-.1,prior+.1
    sol=least_squares(lambda v:diff(v)[~test],[0,0,(lo+hi)/2],bounds=([-.35,-.35,lo],[.35,.35,hi]),loss='soft_l1',f_scale=.03)
    before=np.abs(diff([0,0,0])[test])
    # Re-evaluate using actual neighboring A measurements at shifted positions.
    q=shifted(sol.x)[test]
    dist,idx=tree.query(q[:,:2])
    valid=dist<.085
    after=np.abs(q[valid,2]-a[idx[valid],2])
    ok=len(after)>=20 and valid.mean()>.65 and np.median(after)<.65*np.median(before[valid]) and np.percentile(after,90)<.15
    rec=dict(accepted=bool(ok),shared_cells=len(pairs),validation_cells=len(after),reference='stereo A vs B under assumed XY/yaw, spatial block holdout',
        prior_median_height_residual_m=float(np.median(before[valid])) if valid.any() else None,
        adjusted_median_height_residual_m=float(np.median(after)) if len(after) else None,
        adjusted_p90_m=float(np.percentile(after,90)) if len(after) else None,
        clearance_prior_dz_m=prior, allowed_dz_m=[lo,hi], nearest_anchor_to_B_m=[da,db],
        tilt_rotvec_deg=np.rad2deg(sol.x[:2]).tolist(),elevation_change_m=float(sol.x[2]))
    result=B.copy()
    if ok:
        result[:3,:3]=Rotation.from_rotvec([*sol.x[:2],0]).as_matrix()@B[:3,:3]
        result[2,3]+=sol.x[2]
    return result,rec


