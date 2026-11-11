"""Publication-style pose provenance figures using existing source docs/meshes."""
from pathlib import Path
import hashlib
import json
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Arc, Patch
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from PIL import Image
import pymupdf as fitz

from reconstruction.close_terrain import read_obj
from reconstruction.video_bridge import transform

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/pose_explanation'
BLUE='#227b9d'; ORANGE='#d17b30'; PINK='#ac376c'; INK='#213347'; GRAY='#617181'


def save(fig, name, vector=False):
    fig.savefig(OUT/f'{name}.png',dpi=220,facecolor=fig.get_facecolor())
    if vector: fig.savefig(OUT/f'{name}.svg',facecolor=fig.get_facecolor())
    plt.close(fig)


def textbox(ax, xy, w, h, title, body, color, fontsize=13):
    x,y=xy
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012,rounding_size=0.018',
                              facecolor='white',edgecolor=color,lw=1.8))
    ax.text(x+.025,y+h-.04,title,fontsize=15,fontweight='bold',color=color,va='top')
    ax.text(x+.025,y+h-.105,body,fontsize=fontsize,color=INK,va='top',linespacing=1.55)


def evidence():
    fig=plt.figure(figsize=(16,9),facecolor='#f5f7fa')
    ax=fig.add_axes([.035,.05,.93,.86]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    fig.text(.04,.95,'How the documentation becomes a pose hypothesis',fontsize=25,fontweight='bold',color=INK)
    fig.text(.04,.905,'Worked example: obs_033 to obs_034 | Mobility ID 036 | 31 August 2023',fontsize=15,color=GRAY)
    textbox(ax,(.015,.54),.285,.28,'1  Image timestamps',
            'obs_033: 08:13:01.9172\nobs_034: 13:04:31.6922\n\nThese images bracket the event.',BLUE,14)
    textbox(ax,(.355,.54),.285,.28,'2  Mobility entry',
            'MID 036 at 243:12:20:00\n10° counterclockwise, then 4 m\n\nSIS Appendix I, page 53.',ORANGE,14)
    textbox(ax,(.695,.54),.285,.28,'3  Conditional placement',
            'Start at local (0, 0).\nTurn +10°, then advance 4 m.\n\nEnd XY ≈ (3.94, 0.69) m.',PINK,14)
    for x in [.315,.655]:
        ax.add_patch(FancyArrowPatch((x,.68),(x+.025,.68),arrowstyle='-|>',mutation_scale=22,color=GRAY,lw=2))
    ax.text(.02,.475,'Original archive row',color=INK,fontsize=14,fontweight='bold')
    crop=Image.open(OUT/'mobility_036_excerpt.png')
    ia=fig.add_axes([.055,.22,.55,.20]);ia.imshow(crop);ia.axis('off')
    ax.text(.665,.425,'What the entry does not provide',fontsize=15,fontweight='bold',color=INK)
    ax.text(.665,.365,'A measured 6-DoF pose at every image.\nActual wheel slip or achieved heading.\nA surveyed path between observations.',fontsize=13,color=GRAY,va='top',linespacing=1.7)
    fig.text(.055,.13,'Observation IDs are our reconstruction labels; they are not mobility IDs.',fontsize=14,fontweight='bold',color=INK)
    fig.text(.055,.085,'Timing supports the association. Complete maneuver coverage and a shared time basis remain implementation assumptions.',fontsize=12,color=GRAY)
    fig.text(.055,.045,'Source: revised NavCam SIS, nav/document/ch3_nav_pds_dp_archive_sis.pdf, p. 53; observation provenance files.',fontsize=10,color=GRAY)
    save(fig,'01_documentation_to_pose',True)


def routes():
    fig=plt.figure(figsize=(16,9),facecolor='#f5f7fa')
    ax=fig.add_axes([.04,.08,.92,.78]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    fig.text(.04,.94,'Two sources of relative pose — different levels of evidence',fontsize=24,fontweight='bold',color=INK)
    fig.text(.04,.89,'Camera calibration defines the viewing geometry. It does not supply the rover trajectory.',fontsize=15,color=GRAY)
    textbox(ax,(.015,.40),.45,.50,'Overlapping views: estimate from imagery',
            'Example: obs_044 → obs_047\n\nMatch image features + use stereo 3D points.\nFit a relative pose and test held-out features.\n\n135 feature matches; 44 PnP inliers.\n11 held-out matches: median 0.49 px.\nEndpoint camera displacement ≈ 0.89 m.',BLUE,14)
    textbox(ax,(.525,.40),.45,.50,'No accepted registration: use a prior',
            'Example: obs_033 → obs_034\n\nAssociate images with MID 036 by timing.\nAssume turn 10° CCW, then drive 4 m.\n\nFit height + tilt to shared terrain conditionally.\nNominal fit: +0.409 m elevation adjustment.\nActual horizontal motion remains unverified.',PINK,14)
    ax.add_patch(FancyBboxPatch((.015,.06),.96,.24,boxstyle='round,pad=.012',facecolor='#e8eef3',edgecolor='none'))
    ax.text(.04,.26,'Intermediate path: a model in both cases',fontsize=16,fontweight='bold',color=INK,va='top')
    ax.text(.04,.195,'Registered endpoints use position/orientation interpolation. The mobility prior uses turn-then-drive.\nThe video path is sampled at 33 poses; it is not recovered rover telemetry or real maneuver timing.\nGenerated video must have its own output poses checked before any terrain is accepted.',fontsize=14,color=INK,va='top',linespacing=1.6)
    fig.text(.055,.04,'Sources: registration_edges.json; video_bridge.py; video_pose.py; saved experiment metrics. No global lunar pose track is claimed.',fontsize=10,color=GRAY)
    save(fig,'02_pose_evidence_routes',True)


def mesh_scene():
    base=ROOT/'output/chronological_video/mid036_7'
    poses=np.load(base/'trajectory.npz')['T_world_from_camera']
    metrics=json.loads((base/'metrics.json').read_text())
    dz=metrics['pose']['height_refinement']['elevation_change_m']
    # Explicit idealized body-reference route from the documented prior.
    # It is not a camera-center path or a recovered contact track.
    f=np.linspace(0,1,33);drive=np.maximum(0,(f-.2)/.8)
    end=np.array([4*np.cos(np.deg2rad(10)),4*np.sin(np.deg2rad(10)),dz])
    route=drive[:,None]*end
    mesh=[]
    for name,T,color in zip(['obs_033','obs_034'],poses[[0,-1]],[BLUE,ORANGE]):
        path=ROOT/'artifacts/runs/r11_filtered_batch'/name/'local_mesh_calibration_units.obj'
        v,faces=read_obj(path);v*=.001
        faces=faces[(v[faces,:,][...,2]<11).all(1)]
        world=transform(v,T);tri=world[faces]
        normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12)
        light=np.array([-.4,-.4,1.]);light/=np.linalg.norm(light)
        shade=.64+.36*abs(normal@light)
        rgb=np.array(matplotlib.colors.to_rgb(color))
        colors=np.c_[np.clip(rgb[None]*shade[:,None],0,1),np.ones(len(shade))*.94]
        mesh.append((name,world,faces,colors))
    fig=plt.figure(figsize=(18,10),facecolor='white')
    fig.text(.035,.953,'Two reconstructions, one conditional spatial frame',fontsize=26,fontweight='bold',color=INK)
    fig.text(.035,.91,'obs_033 + obs_034  •  Relative placement uses MID 036: turn 10° CCW, then drive 4 m',fontsize=16,color=GRAY)
    ax=fig.add_axes([.02,.17,.70,.70],projection='3d',computed_zorder=False)
    for name,v,faces,colors in mesh:
        ax.add_collection3d(Poly3DCollection(v[faces],facecolors=colors,edgecolor='none',rasterized=True,zorder=2))
        folder=ROOT/'artifacts/runs/r11_filtered_batch'/name
        cloud=np.load(folder/'xyz_rectified_calibration_units.npy')*.001
        gray=np.array(Image.open(folder/'rectified_left.png'))
        mask=np.isfinite(cloud).all(2)&(cloud[:,:,2]<11)
        sample=cloud[mask][::4]
        intensity=gray[mask][::4]/255
        T=poses[0 if name=='obs_033' else -1]
        sample=transform(sample,T)
        rgb=np.array(matplotlib.colors.to_rgb(BLUE if name=='obs_033' else ORANGE))
        ax.scatter(*sample.T,s=.65,c=rgb[None]*(.55+.45*intensity[:,None]),depthshade=False,linewidths=0,rasterized=True,zorder=3)
    ax.plot(route[:,0],route[:,1],route[:,2],color='white',lw=7,zorder=10)
    ax.plot(route[:,0],route[:,1],route[:,2],color=PINK,lw=3.5,ls='--',zorder=11)
    for idx,label in [(0,'A  obs_033'),(-1,'B  obs_034')]:
        q=route[idx]
        ax.scatter(*q,s=90,color=PINK,edgecolor='white',linewidth=1.3,depthshade=False,zorder=12)
        ax.text(q[0],q[1]-.2,q[2]+.35,label,color=INK,fontsize=13,fontweight='bold',zorder=13)
    ax.quiver(0,0,0,1,0,0,color=INK,length=1.0,arrow_length_ratio=.18,zorder=12)
    ax.quiver(*route[-1],np.cos(np.deg2rad(10)),np.sin(np.deg2rad(10)),0,color=INK,length=1,arrow_length_ratio=.18,zorder=12)
    ax.set(xlim=(-.7,14),ylim=(-4.6,5),zlim=(-.1,2.1),xlabel='Local forward X (m)',ylabel='Local lateral Y (m)',zlabel='Nominal Z (m)')
    ax.set_box_aspect([14.7,9.6,2.2],zoom=1.2);ax.view_init(elev=38,azim=-65)
    ax.set_zticks([0,1,2])
    ax.set_yticks([-4,0,4])
    ax.set_proj_type('ortho');ax.tick_params(labelsize=10,pad=0)
    for axis in [ax.xaxis,ax.yaxis,ax.zaxis]: axis.pane.fill=False
    fig.legend(handles=[Patch(facecolor=BLUE,label='obs_033 stereo reconstruction'),Patch(facecolor=ORANGE,label='obs_034 stereo reconstruction'),
                        Line2D([],[],color=PINK,ls='--',lw=3,label='Assumed rover reference path')],loc='lower left',bbox_to_anchor=(.045,.125),ncol=3,frameon=False,fontsize=12)
    # Real input thumbnails, not rendered or generated intermediates.
    for name,title,box,color in [('obs_033','A  obs_033 • before maneuver',[.755,.66,.20,.20],BLUE),
                               ('obs_034','B  obs_034 • after maneuver',[.755,.405,.20,.20],ORANGE)]:
        ia=fig.add_axes(box);ia.imshow(Image.open(ROOT/'artifacts/runs/r11_filtered_batch'/name/'rectified_left.png'),cmap='gray');ia.axis('off')
        ia.set_title(title,color=color,fontsize=13,fontweight='bold',pad=7)
    plan=fig.add_axes([.77,.19,.19,.15]);plan.plot([0,end[0]],[0,end[1]],'--',color=PINK,lw=2)
    plan.scatter([0,end[0]],[0,end[1]],color=[BLUE,ORANGE],s=50)
    plan.arrow(0,0,1,0,width=.015,color=GRAY,length_includes_head=True)
    plan.add_patch(Arc((0,0),2.6,2.6,theta1=0,theta2=10,color=PINK,lw=2))
    plan.text(1.35,-.13,'10° CCW',fontsize=10,color=PINK)
    plan.text(1.7,.55,'4 m',fontsize=12,color=PINK,fontweight='bold')
    plan.set(xlim=(-.3,4.4),ylim=(-.4,1.25),aspect='equal');plan.set_xticks([]);plan.set_yticks([])
    for spine in plan.spines.values():spine.set_visible(False)
    plan.set_title('Idealized motion, plan view',fontsize=12,color=INK)
    fig.text(.045,.086,'The path connects viewing positions, not terrain-patch centers. Both cameras look forward, so their reconstructed areas can overlap.',fontsize=12,color=INK)
    limitation=fig.text(.045,.052,'Conditional pose, not surveyed placement. Observed points + source triangles; no gap-fill geometry. The path vertical profile is modeled.',fontsize=11,color=GRAY)
    fig.text(.045,.025,'Metres use the project’s existing calibration scale. Nominal rover-local axes; gravity alignment is unverified. Sources: SIS p. 53 + saved meshes/poses.',fontsize=10,color=GRAY)
    save(fig,'03_reconstructions_with_rover_path')
    # Companion view includes the existing inferred completion, clearly gray.
    # No new terrain is created by this plotting script.
    v,faces=read_obj(ROOT/'output/chronological_video/mid036_model/terrain_top_m.obj')
    grid=np.load(ROOT/'output/chronological_video/mid036_model/integrated_grid.npz')
    vertex_labels=grid['labels'][np.isfinite(grid['height_m'])]
    if len(vertex_labels)!=len(v): raise ValueError('Completed mesh provenance does not match vertex order')
    faces=faces[(vertex_labels[faces]>=2).any(1)]
    tri=v[faces]
    normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
    illumination=.70+.25*abs(normals@np.array([-.3,-.4,.866]))
    colors=np.c_[np.repeat(illumination[:,None],3,axis=1),np.ones(len(faces))]
    ax.add_collection3d(Poly3DCollection(tri,facecolors=colors,edgecolor='none',rasterized=True,zorder=1))
    limitation.set_text('Gray surface includes synthetic video and interpolation from the existing completed model. Its plausible appearance does not validate unseen terrain.')
    fig.text(.755,.365,'Gray = completion with inferred vertices',fontsize=11,color=GRAY)
    save(fig,'05_completed_terrain_with_rover_path')
    np.savetxt(OUT/'assumed_rover_reference_path_m.csv',np.c_[np.arange(33),route],delimiter=',',header='frame_index,x_m,y_m,z_m',comments='')
    # A second, true plan view makes overlap and camera positions easy to read.
    fig,ax=plt.subplots(figsize=(14,8),layout='constrained')
    for name,v,faces,colors in mesh:
        ax.tripcolor(v[:,0],v[:,1],faces,facecolors=np.ones(len(faces)),cmap=matplotlib.colors.ListedColormap([BLUE if name=='obs_033' else ORANGE]),alpha=.55,rasterized=True)
    ax.plot(route[:,0],route[:,1],'--',color=PINK,lw=3)
    for i,label in [(0,'A: obs_033'),(-1,'B: obs_034')]:
        ax.scatter(*route[i,:2],s=85,color=PINK,zorder=5)
        ax.annotate(label,route[i,:2],xytext=(0,-24),textcoords='offset points',ha='center',fontsize=12,fontweight='bold')
    ax.set(xlabel='Local forward X (m)',ylabel='Local lateral Y (m)',aspect='equal',xlim=(-.7,14),ylim=(-4.6,5),
           title='Plan view: observed stereo footprints and assumed rover motion\n033 → 034 | conditional placement; no inferred terrain included')
    ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.2)
    ax.legend(handles=[Patch(facecolor=BLUE,alpha=.6,label='obs_033'),Patch(facecolor=ORANGE,alpha=.6,label='obs_034'),Line2D([],[],color=PINK,ls='--',label='Assumed 4 m route')],loc='upper right')
    save(fig,'04_spatial_plan_view',True)
    return mesh,poses,route


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.labelcolor':INK,'text.color':INK,'svg.fonttype':'none'})
    source=ROOT/'chandrayaan-3-documentation/nav/document/ch3_nav_pds_dp_archive_sis.pdf'
    doc=fitz.open(source);page=doc[52]
    assert '10deg CCW, 4m' in page.get_text()
    # Preserve the full row including time, MID, path and the description.
    page.get_pixmap(matrix=fitz.Matrix(3,3),clip=fitz.Rect(91,455,502,495)).save(OUT/'mobility_036_excerpt.png')
    evidence();routes();mesh,poses,route=mesh_scene()
    paths=[source,ROOT/'configs/video_mobility_priors.json',ROOT/'output/chronological_video/mid036_model/terrain_top_m.obj',ROOT/'output/chronological_video/mid036_model/integrated_grid.npz',ROOT/'output/chronological_video/mid036_7/trajectory.npz',
           ROOT/'output/chronological_video/mid036_7/metrics.json',ROOT/'artifacts/runs/r12_registration/registration_edges.json']
    for name in ['obs_033','obs_034']:
        paths += [ROOT/'artifacts/runs/r11_filtered_batch'/name/f for f in ['local_mesh_calibration_units.obj','xyz_rectified_calibration_units.npy','provenance.json','rectified_left.png']]
    record=dict(source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_pdf_page_1based=53, endpoint_camera_poses=poses[[0,-1]].tolist(),
        route='Idealized body-reference turn-then-drive path; XY from documented maneuver; Z interpolated from fitted elevation adjustment',
        nominal_route_start_m=route[0].tolist(),nominal_route_end_m=route[-1].tolist(),
        mesh_counts={name:dict(vertices=len(v),displayed_triangles=len(f)) for name,v,f,c in mesh},
        limits='Display uses existing conditional pose, calibration-unit-to-metre factor 0.001, observed points/source triangles with camera depth below 11 m. Figure 05 also displays the existing inferred completion in gray. No new hole filling or global position recovery.')
    (OUT/'figure_provenance.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record['mesh_counts'],indent=2))


if __name__=='__main__':main()
