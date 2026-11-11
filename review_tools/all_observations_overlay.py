"""Illustrative full traverse: documented commands + timestamp-associated views.

Visualization only. Does not update the reconstruction pose graph or adopt global
poses for reconstruction. Every placement is conditional on the documented path.
"""
from pathlib import Path
from datetime import datetime, timedelta
import csv
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from scipy.spatial.transform import Rotation

from reconstruction.video_bridge import local_camera, read, transform

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/all_observations_overlay'

# Transcribed from revised SIS Appendix I, pages 52-54. T: positive CCW degrees;
# D: signed drive metres; N: an explicit NavCam checkpoint. No duration inferred.
COMMANDS=[
 (1,'235:19:06:36',[('D',2.3*np.cos(np.deg2rad(12))),('D',.7)]),
 (2,'236:21:03:52',[('D',2.499),('T',-1),('D',1.587),('T',45.138)]),
 (3,'237:18:59:06',[('D',2.76),('T',-12.713),('D',2.283),('T',24.465)]),
 (4,'238:17:43:00',[('T',30)]),
 (5,'239:03:40:00',[('T',25),('T',-25)]),
 (6,'239:16:00:50',[('T',-30)]),
 (7,'239:16:20:54',[('T',24.465),('D',-2.283),('T',12.713),('D',-2.76)]),
 (8,'239:21:04:11',[('T',36)]),
 (9,'240:05:39:13',[('D',2.754),('T',12.168),('D',1.258),('T',-12.168)]),
 (12,'240:17:15:00',[('D',-2.754),('T',12.168),('D',1.758),('T',-12.168)]),
 (13,'240:20:20:09',[('D',-.5)]),
 (14,'241:05:20:00',[('T',-180),('D',.5),('T',-90),('T',-90)]),
 (15,'241:08:39:30',[('T',35)]),
 (16,'241:15:43:00',[('D',-1)]),(17,'241:16:37:00',[('D',-1)]),
 (18,'241:16:45:00',[('D',-1)]),(19,'241:16:58:30',[('D',-1)]),
 (20,'241:18:46:03',[('T',-180),('N',0),('D',.5),('T',180)]),
 (21,'241:21:51:00',[('D',-2.587),('T',-16.361),('D',-3.557),('T',16.361)]),
 (22,'241:23:18:00',[('T',-180),('N',0),('D',.5),('T',180)]),
 (23,'242:01:58:00',[('T',-30),('N',0),('T',30)]),
 (24,'242:03:14:00',[('D',-2.933),('T',-2.231),('D',-2.568),('T',2.231)]),
 (25,'242:04:06:00',[('T',-180),('D',.5),('T',180),('N',0)]),
 (26,'242:04:59:00',[('T',20),('T',-20)]),
 (27,'242:10:43:00',[('D',-2.456),('T',8.031),('D',-3.579),('T',8.031)]),
 (28,'242:11:38:30',[('T',-170),('D',.5),('T',170),('N',0)]),
 (29,'242:14:09:00',[('D',-2.591),('T',16.604),('D',-2.379),('T',39.812),('D',-2.382),('T',10.975)]),
 (30,'242:14:37:00',[('T',-180),('D',-.5),('T',180)]),
 (31,'242:18:36:00',[('D',-2.545),('T',-8.381),('D',-2.037),('T',-23.724),('D',-1.699),('T',32.105)]),
 (32,'242:19:23:07',[('T',-180),('D',.5),('T',180)]),
 (33,'243:00:52:00',[('T',-10),('D',-1)]),
 (34,'243:05:00:00',[('T',150),('N',0),('D',.5),('T',-150)]),
 (35,'243:08:07:30',[('D',-.5),('T',40),('N',0)]),
 (36,'243:12:20:00',[('T',10),('D',4)]),
 (37,'243:16:39:00',[('D',-4),('T',-40),('N',0),('T',40)]),
 (38,'243:21:28:00',[('T',-40),('D',1),('T',-50),('D',2),('N',0),('T',20),('N',0),('T',20),('N',0),('T',50)]),
 (39,'244:01:20:00',[('T',-70),('D',2),('T',25),('N',0),('T',20),('N',0),('T',25),('N',0)]),
 (40,'244:05:40:00',[('T',-35),('D',3),('T',70),('N',0),('T',20),('N',0),('T',20),('N',0),('T',-30)]),
 (41,'244:12:55:00',[('T',-20),('D',2),('N',0),('T',20),('N',0)]),
 (42,'244:18:30:31',[('T',-40),('D',1),('N',0),('T',20),('N',0),('T',20),('N',0)]),
 (43,'244:22:13:00',[('T',-44.5),('D',6.02),('N',0),('T',-20),('N',0),('T',64.5)]),
 (44,'245:01:47:00',[('T',-50.2),('D',5.02),('N',0),('T',-20),('N',0),('T',40),('N',0),('T',30.2)]),
 (45,'245:05:51:00',[('T',-50.2),('D',5),('T',-50),('T',100.2)]),
 (47,'245:08:42:00',[('T',-50.2),('D',-1),('T',-50),('N',0),('T',-80),('N',0),('T',-20),('N',0),('T',10),('N',0)])]


def event_time(value):
    d,h,m,s=map(int,value.split(':'))
    return datetime(2023,1,1)+timedelta(days=d-1,hours=h,minutes=m,seconds=s)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pairs=ROOT/'chandrayaan-3-navcam-sorted/stereo_pairs.csv'
    rows=sorted(list(csv.DictReader(pairs.open())),key=lambda r:(r['left_timestamp'],r['observation_id']))
    state=np.array([0.,0.,0.]);path=[state[:2].copy()];events=[]
    for mid,stamp,commands in COMMANDS:
        start=state.copy();checkpoints=[]
        for kind,value in commands:
            if kind=='T':state[2]+=value
            elif kind=='D':
                state[:2]+=value*np.array([np.cos(np.deg2rad(state[2])),np.sin(np.deg2rad(state[2]))])
                path.append(state[:2].copy())
            else:checkpoints.append(state.copy().tolist())
        events.append(dict(mid=mid,time=event_time(stamp),start=start.tolist(),end=state.copy().tolist(),navcam_checkpoints=checkpoints,commands=commands))
    records=[]
    for row in rows:
        t=datetime.strptime(row['left_timestamp'][:15],'%Y%m%dT%H%M%S')
        prior=[e for e in events if e['time']<=t]
        event=prior[-1] if prior else None
        records.append(dict(observation=row['observation_id'],timestamp=row['left_timestamp'],file_sequence=row['sequence_id'],
            associated_mid=event['mid'] if event else None, row=row))
    bymid={}
    for r in records:bymid.setdefault(r['associated_mid'],[]).append(r)
    for mid,group in bymid.items():
        if mid is None:
            for r in group:r.update(command_state=[0,0,0],association='Before first maneuver; arbitrary local origin')
            continue
        e=next(e for e in events if e['mid']==mid)
        checkpoints=e['navcam_checkpoints']
        times=sorted(set(r['timestamp'] for r in group))
        for r in group:
            index=times.index(r['timestamp'])
            if checkpoints:
                k=0 if len(times)==1 else round(index*(len(checkpoints)-1)/(len(times)-1))
                label='NavCam stages assigned in timestamp order' if len(times)==len(checkpoints) else 'AMBIGUOUS: imaging stages sampled in order; counts differ'
                r.update(command_state=checkpoints[k],association=label,navcam_checkpoint_index=k)
            else:r.update(command_state=e['end'],association='Assumed end of latest maneuver; no sub-maneuver pose timestamp')
    byname={r['observation']:r for r in records}
    matrices={};metadata={};sources=[pairs]
    for r in records:
        name=r['observation'];folder=ROOT/'artifacts/runs/r11_filtered_batch'/name
        xyz=folder/'xyz_rectified_calibration_units.npy'
        r['has_reconstruction']=xyz.exists()
        R=Rotation.from_euler('z',r['command_state'][2],degrees=True).as_matrix()
        G=np.eye(4);G[:3,:3]=R;G[:2,3]=r['command_state'][:2]
        if r['has_reconstruction']:
            meta=json.loads((folder/'provenance.json').read_text());metadata[name]=meta
            frame=dict(R=np.array(meta['R_rectified_from_source']))
            matrices[name]=G@local_camera(frame)
            sources.extend([folder/'provenance.json',xyz])
        r['pose_source']='Command-based illustrative placement'
    components=ROOT/'artifacts/runs/r12_registration/components.json';sources.append(components)
    for comp in json.loads(components.read_text()):
        if len(comp['frames'])<2:continue
        file=ROOT/'artifacts/runs/r12_registration'/('component_'+comp['frames'][0])/'camera_trajectory.json'
        poses=json.loads(file.read_text())['T_component_from_camera'];sources.append(file)
        anchor=min(poses,key=lambda n:byname[n]['timestamp'])
        local={n:np.array(T,dtype=float) for n,T in poses.items()}
        for T in local.values():T[:3,3]*=.001
        base=matrices[anchor]@np.linalg.inv(local[anchor])
        for name,T in local.items():
            matrices[name]=base@T
            byname[name]['pose_source']='Registered relative pose within component; command-anchored globally'
            byname[name]['component_anchor']=anchor
    # Preserve records and transforms before rendering. Never writes production poses.
    for r in records:
        name=r['observation']
        r['camera_xy_m']=matrices[name][:2,3].tolist() if name in matrices else r['command_state'][:2]
        r.pop('row')
    points=[];colors=[]
    cmap=plt.get_cmap('turbo')
    for i,r in enumerate(records):
        name=r['observation']
        if name not in matrices:continue
        xyz=np.load(ROOT/'artifacts/runs/r11_filtered_batch'/name/'xyz_rectified_calibration_units.npy')*.001
        valid=np.isfinite(xyz).all(2)&(xyz[:,:,2]>.4)&(xyz[:,:,2]<11)
        p=xyz[valid];step=max(1,int(np.ceil(len(p)/3500)))
        p=transform(p[::step],matrices[name]);points.append(p[:,:2]);colors.append(np.tile(cmap(i/(len(records)-1)),(len(p),1)))
    points=np.concatenate(points);colors=np.concatenate(colors)
    positions=np.array([r['camera_xy_m'] for r in records]);path=np.array(path)
    np.savetxt(OUT/'command_route_xy_m.csv',path,delimiter=',',header='x_m,y_m',comments='')
    np.savez_compressed(OUT/'illustrative_camera_poses.npz',**matrices)
    fields=['observation','timestamp','file_sequence','associated_mid','has_reconstruction','pose_source','association','navcam_checkpoint_index','component_anchor','command_state','camera_xy_m']
    with (OUT/'observation_placements.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
    interpretations=[
      'All positions are illustrative global placements, not solved rover telemetry or a surveyed lunar map.',
      'MID001 date conflicts with DOY: use calendar 23 Aug, 19:06:36 (DOY235), not printed DOY236.',
      'Other events use DOY/time; inconsistent calendar dates in MID038/042/043 are not used.',
      'MID009 2..754m read as 2.754m; MID039 superscript-degree typography read as 70 degrees CW.',
      'MID004 uses 30 degrees from Path; conflicting 40-degree slip formula and 31.5-degree VO are not substituted.',
      'MID012 uses positive 1.758m as printed despite the retrace description; this is a known direction ambiguity.',
      'MID010/011/046 have no executed path/time entries and add no separate motion; MID046 refers to MID047.',
      'No extra final 90-degree parking turn is added beyond the listed MID047 imaging turns.',
      'All motion planar, initial heading arbitrary +X, no slip; ramp projected horizontally. No global north or elevation is inferred.',
      'Each image is associated with latest prior mobility timestamp; suffix IDs are not used as pose identifiers.',
      'Within an event, distinct image times are associated in order with explicit NavCam checkpoints. If counts differ, a single time uses first checkpoint; multiple times evenly sample checkpoint indices. This is an acknowledged illustrative assignment.',
      'Events without imaging checkpoints use assumed final pose; event times do not provide maneuver durations.',
      'Existing registered components retain their internal relative transforms, but their global anchors inherit command uncertainty.',
      'Only finite source stereo points 0.4-11m camera depth are displayed, up to 3500 points per reconstruction; six failed/absent reconstructions appear as hollow site markers.',
      'This scenario is not installed as a reconstruction pose graph and must not be used as metric ground truth.'
    ]
    sourcepdf=ROOT/'chandrayaan-3-documentation/nav/document/ch3_nav_pds_dp_archive_sis.pdf';sources.append(sourcepdf)
    record=dict(observations=len(records),reconstructions=len(matrices),registered_component_count=6,
        date_range=[records[0]['timestamp'],records[-1]['timestamp']],interpretations=interpretations,
        events=[{**e,'time':e['time'].isoformat()} for e in events],observations_detail=records,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'overlay_provenance.json').write_text(json.dumps(record,indent=2))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'svg.fonttype':'none'})
    fig=plt.figure(figsize=(19,13),facecolor='#f8fafc')
    ax=fig.add_axes([.055,.14,.70,.75],facecolor='white')
    ax.scatter(points[:,0],points[:,1],c=colors,s=.8,alpha=.38,linewidths=0,rasterized=True,zorder=1)
    ax.plot(path[:,0],path[:,1],color='white',lw=5,zorder=2)
    ax.plot(path[:,0],path[:,1],color='#263548',lw=2,ls='--',zorder=3)
    for i,r in enumerate(records):
        ax.scatter(*positions[i],s=38,facecolor=cmap(i/(len(records)-1)) if r['has_reconstruction'] else 'white',
            edgecolor='#263548',linewidth=.65,zorder=5)
    # Group nearby sites for readable labels; grouping changes no plotted positions.
    groups=[];remaining=set(range(len(records)))
    while remaining:
        seed=min(remaining);group={seed};front=[seed];remaining.remove(seed)
        while front:
            k=front.pop();near={j for j in remaining if np.linalg.norm(positions[j]-positions[k])<.30}
            group|=near;remaining-=near;front.extend(near)
        groups.append(sorted(group))
    allxy=np.vstack([points,path,positions]);lo=allxy.min(0)-3;hi=allxy.max(0)+3
    ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),aspect='equal',xlabel='Arbitrary local X (m)',ylabel='Arbitrary local Y (m)')
    ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.12)
    fig.text(.055,.958,'All observations on an approximate rover traverse',fontsize=27,fontweight='bold',color='#203449')
    fig.text(.055,.921,'56 observations • 50 stereo reconstructions superimposed • 23 Aug–2 Sep 2023',fontsize=17,color='#596b7c')
    fig.canvas.draw();occupied=[]
    offsets=[(10,12),(10,-18),(-10,12),(-10,-18),(22,30),(22,-36),(-22,30),(-22,-36),(0,48),(0,-54),(48,0),(-48,0),(65,25),(-65,25),(65,-30),(-65,-30)]
    for group in groups:
        xy=positions[group].mean(0)
        label=','.join(records[j]['observation'][4:]+('*' if 'AMBIGUOUS' in records[j]['association'] else '') for j in group)
        best=None
        for dx,dy in offsets:
            ann=ax.annotate(label,xy,xytext=(dx,dy),textcoords='offset points',fontsize=9,ha='left' if dx>=0 else 'right',va='center',
                color='#203449',bbox=dict(boxstyle='round,pad=.18',fc='white',ec='#d6dee5',alpha=.94),
                arrowprops=dict(arrowstyle='-',color='#758493',lw=.6),zorder=6)
            bbox=ann.get_bbox_patch().get_window_extent(fig.canvas.get_renderer()) if False else ann.get_window_extent(fig.canvas.get_renderer())
            overlap=sum(bbox.overlaps(b) for b in occupied)
            # Annotation window bounds include leader; use approximate text box for collisions.
            center=ax.transData.transform(xy)+np.array([dx,dy])*fig.dpi/72
            width=len(label)*5.5*fig.dpi/72;height=14*fig.dpi/72
            from matplotlib.transforms import Bbox
            box=Bbox.from_bounds(center[0] if dx>=0 else center[0]-width,center[1]-height/2,width,height)
            score=sum(box.overlaps(b) for b in occupied)
            inbounds=ax.bbox.contains(box.x0,box.y0) and ax.bbox.contains(box.x1,box.y1)
            score+=0 if inbounds else 10
            ann.remove()
            if best is None or score<best[0]:best=(score,dx,dy,box)
            if score==0:break
        _,dx,dy,box=best;occupied.append(box)
        ax.annotate(label,xy,xytext=(dx,dy),textcoords='offset points',fontsize=9,ha='left' if dx>=0 else 'right',va='center',
            color='#203449',bbox=dict(boxstyle='round,pad=.18',fc='white',ec='#d6dee5',alpha=.94),arrowprops=dict(arrowstyle='-',color='#758493',lw=.6),zorder=6)
    for start,end in zip(path[::5],path[1::5]):
        if np.linalg.norm(end-start)>.3:ax.annotate('',end,xytext=start,arrowprops=dict(arrowstyle='->',color='#263548',lw=1.3),zorder=4)
    side=fig.add_axes([.79,.20,.19,.65]);side.axis('off')
    side.text(0,.98,'HOW TO READ IT',fontsize=16,fontweight='bold',color='#203449',va='top')
    side.text(0,.88,'Colored terrain\nReal stereo points, positioned\nusing an approximate pose.\n\nDashed route\nIntegrated turn/drive commands\nfrom the archive mobility table.\n\nLabels 001–056\nProject observation IDs.\nGrouped labels share a site.\n* = ambiguous imaging stage.\n\nHollow markers\nObservation exists; no accepted\nstereo reconstruction available.',fontsize=12,color='#4d6174',linespacing=1.5,va='top')
    side.text(0,.29,'ILLUSTRATIVE, NOT SURVEYED',fontsize=12,fontweight='bold',color='#a34935',va='top')
    side.text(0,.23,'No measured global pose track.\nHeading, timing, slip and some\ncommand entries are uncertain.\nOverlaps or offsets here are\nnot evidence of correct alignment.',fontsize=12,color='#4d6174',linespacing=1.5,va='top')
    cax=fig.add_axes([.80,.13,.17,.018]);sm=plt.cm.ScalarMappable(cmap=cmap,norm=plt.Normalize(1,56))
    fig.colorbar(sm,cax=cax,orientation='horizontal',ticks=[1,14,28,42,56],label='Observation sequence (early → late)')
    fig.text(.055,.072,'Local image-registered groups preserve their internal relative poses; their position on this full-traverse map remains command-based.',fontsize=12,color='#4d6174')
    fig.text(.055,.041,'Source: revised NavCam SIS, Appendix I, pp. 52–54; archive image timestamps; existing stereo point clouds. Full assumptions and coordinates are included.',fontsize=11,color='#4d6174')
    fig.savefig(OUT/'all_observations_and_path.png',dpi=240,facecolor=fig.get_facecolor())
    # A plot-only scientific export permits a larger map beside editable slide captions.
    fig.canvas.draw()
    plot_bounds = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted()).expanded(1.02, 1.02)
    fig.savefig(OUT/'traverse_plot_for_slides.png',dpi=240,bbox_inches=plot_bounds,facecolor=fig.get_facecolor())
    fig.savefig(OUT/'all_observations_and_path.svg',facecolor=fig.get_facecolor());plt.close(fig)
    print(json.dumps(dict(observations=len(records),reconstructions=len(matrices),label_groups=len(groups),command_segments=len(path)-1,
        route_end_xy_m=path[-1].tolist(),ambiguous_imaging_assignments=sum('AMBIGUOUS' in r['association'] for r in records)),indent=2))


if __name__=='__main__':main()
