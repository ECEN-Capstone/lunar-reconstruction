"""Conservative support filtering; original disparity and failed regions are retained."""
import argparse
import json
import shutil
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .geometry import ROOT,warp,write_ply
from .stereo import local_mesh


def filter_frame(src,out,cfg):
    out.mkdir(parents=True,exist_ok=False)
    prov=json.loads((src/'provenance.json').read_text());basecfg=prov['config'];B=prov['baseline_calibration_units']
    d=np.load(src/'disparity_left_px.npy');xyz=np.load(src/'xyz_rectified_calibration_units.npy')
    old=np.isfinite(xyz).all(axis=2);im=cv2.imread(str(src/'rectified_left.png'),0)
    border=cfg['source_border_px'];source_mask=np.zeros(old.shape,np.uint8);source_mask[border:-border,border:-border]=255
    hl,hr=map(np.array,prov['homographies']);gl=warp(source_mask,hl)==255;gr=warp(source_mask,hr)==255
    yy,xx=np.indices(d.shape,dtype=np.float32);right_ok=cv2.remap(gr.astype(np.uint8),xx-d,yy,cv2.INTER_NEAREST)>0
    w=cfg['median_window'];med=cv2.medianBlur(d,w)
    neighbors=cv2.boxFilter(old.astype(np.float32),-1,(w,w),normalize=False)
    valid=old & gl & right_ok & (d>=cfg['minimum_disparity_px']) & (abs(d-med)<=cfg['maximum_median_disparity_difference_px']) & (neighbors>=cfg['minimum_valid_neighbors'])
    n,labels,stats,_=cv2.connectedComponentsWithStats(valid.astype(np.uint8),8)
    keep=stats[:,cv2.CC_STAT_AREA]>=cfg['minimum_component_pixels'];keep[0]=False
    valid &= keep[labels]
    xyz[~valid]=np.nan
    np.save(out/'xyz_rectified_calibration_units.npy',xyz);np.save(out/'depth_calibration_units.npy',xyz[:,:,2])
    cv2.imwrite(str(out/'validity_mask.png'),valid.astype(np.uint8)*255)
    cv2.imwrite(str(out/'support_filter_rejected.png'),(old&~valid).astype(np.uint8)*255)
    shutil.copyfile(src/'rectified_left.png',out/'rectified_left.png')
    prov.update(parent_run=src.relative_to(ROOT).as_posix(),support_filter=cfg)
    (out/'provenance.json').write_text(json.dumps(prov,indent=2))
    write_ply(out/'points_calibration_units.ply',xyz[valid],im[valid])
    vertices,colors,faces=local_mesh(xyz,valid,im,{**basecfg,'baseline':B})
    write_ply(out/'local_mesh_calibration_units.ply',vertices,colors,faces)
    with (out/'local_mesh_calibration_units.obj').open('w') as f:
        f.write('# CAHV source units. x right, y down, z forward. Unknown metre scale and gravity.\n')
        for v in vertices:f.write('v %.6f %.6f %.6f\n'%tuple(v))
        for face in faces:f.write('f %d %d %d\n'%tuple(face+1))
    metrics=dict(observation=src.name,input_points=int(old.sum()),valid_points=int(valid.sum()),valid_fraction=float(valid.mean()),mesh_vertices=len(vertices),mesh_faces=len(faces),
        depth_percentiles_calibration_units=np.percentile(xyz[:,:,2][valid],[5,50,95]).tolist() if valid.any() else [])
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2))
    fig,axs=plt.subplots(1,3,figsize=(15,5))
    axs[0].imshow(im,cmap='gray');axs[0].contour(valid,levels=[.5],colors=['lime'],linewidths=.2);axs[0].set_title(f"{src.name}: retained {valid.mean():.1%}")
    p=axs[1].imshow(xyz[:,:,2],cmap='viridis');fig.colorbar(p,ax=axs[1],shrink=.7,label='Axial depth (calibration units)');axs[1].set_title('Support-filtered depth')
    if len(vertices):
        axs[2].scatter(vertices[:,0],vertices[:,2],s=.2,c=colors,cmap='gray',vmin=0,vmax=255);axs[2].set_aspect('equal');axs[2].set(xlabel='X',ylabel='Z',title='Point cloud top projection; source units')
    fig.tight_layout();fig.savefig(out/'filtered_diagnostics.png',dpi=120);plt.close(fig)
    return metrics


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',default='r08_quality_batch');p.add_argument('--run',required=True);args=p.parse_args()
    source=ROOT/'artifacts/runs'/args.batch;out=ROOT/'artifacts/runs'/args.run;out.mkdir(parents=True,exist_ok=False)
    cfg=json.loads((ROOT/'configs/filtering.json').read_text());records=[]
    for src in sorted(source.glob('obs_*')):
        if not (src/'metrics.json').exists():continue
        records.append(filter_frame(src,out/src.name,cfg));print(json.dumps(records[-1]),flush=True)
        (out/'batch_metrics.json').write_text(json.dumps(records,indent=2))
    (out/'config.json').write_text(json.dumps(cfg,indent=2))


if __name__=='__main__':main()
