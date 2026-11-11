import fs from 'node:fs/promises';
import path from 'node:path';

export const ROOT='C:/Users/rhunt/Documents/Capstone/reconstruction';
const OUT=ROOT+'/output/progress_presentation';
const C={ink:'#183149',muted:'#52687B',teal:'#087E8B',orange:'#B7472A',bg:'#F7F9FC',line:'#CDD7E0'};
const FONT='Arial';
const records=[];
const figureSources=[];
function text(s,value,x,y,w,h,size=25,color=C.ink,bold=false){
 const sh=s.shapes.add({geometry:'textbox',name:'text-'+s.shapes.items.length,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=value; sh.text.style={typeface:FONT,fontSize:size,color,bold,verticalAlignment:'top'}; return sh;
}
function image(s,rel,x,y,w,h,alt){const source=path.isAbsolute(rel)?rel:ROOT+'/'+rel;s.images.add({path:source,position:{left:x,top:y,width:w,height:h},fit:'contain',alt});figureSources.push({slide:records.length,source,alt});}
function table(s,values,x,y,w,h,widths,size=23){
 const tb=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnTracks:widths.map(v=>({mode:'fr',value:v})),values});
 tb.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({textStyle:{typeface:FONT,fontSize:size,color:C.ink},fill:'#FFFFFF',margins:{left:13,right:13,top:6,bottom:6},anchor:'center',borders:{bottom:{fill:C.line,width:1}}});
 tb.cells.block({row:0,column:0,rowCount:1,columnCount:values[0].length}).assign({fill:C.ink,textStyle:{typeface:FONT,fontSize:size,bold:true,color:'#FFFFFF'}});
 return tb;
}
function bullets(s,items,x,y,w,step=89,size=25){items.forEach((item,i)=>{text(s,String(i+1),x,y+i*step,42,45,size,C.teal,true);text(s,item,x+52,y+i*step,w-52,step-8,size);});}
function slide(p,title,section,notes,sources,mins){
 const s=p.slides.add();s.setViewportSize(1280,720);s.background.fill=C.bg;
 const n=p.slides.items.length;
 text(s,section.toUpperCase(),50,23,1160,24,15,C.teal,true);
 text(s,title,50,60,1180,88,39,C.ink,true);
 text(s,'Chandrayaan-3 terrain reconstruction  |  Evidence snapshot: 9 Nov 2026',50,681,1100,22,14,C.muted);
 text(s,String(n).padStart(2,'0'),1180,676,50,30,19,C.muted);
 s.speakerNotes.text=(mins?'Suggested speaking time: '+mins+' minutes.\n\n':'Appendix: use for questions; outside the 15-minute update.\n\n')+notes+'\n\nSources:\n'+sources.map(v=>v.startsWith('http')||path.isAbsolute(v)?v:ROOT+'/'+v).join('\n');
 records.push({number:n,title,section,minutes:mins??0,notes,sources});return s;
}
function takeaway(s,v){text(s,v,50,612,1180,55,24,C.orange,true);}

export async function build(p){
 records.length=0;figureSources.length=0;
 if(p.slides.items.length)p.slides.delete(p.slides.items.map(x=>x.id));
 p.theme.defaultFont=FONT;
 let s;
 s=slide(p,'Lunar terrain reconstruction', 'Biweekly research update',
 'Lead with the results. We have a reproducible real-stereo pipeline and local terrain exports. The largest completed footprint is about 77.2 square metres, but much of it is inferred. The procedural video experiments close the evaluation loop and expose weaknesses, yet do not beat interpolation. No learned video model output has been received in this workspace. Slides 1–13 are the 15-minute talk; the appendix contains parameters, additional experiments and the benchmark plan.',
 ['RECONSTRUCTION_REPORT.md','output/largest_terrain/component_obs_044/metrics.json','output/collaboration_review/2026-11-09/COMPARISON_FINDINGS.md'],.6);
 text(s,'Real stereo produces local terrain.\nVideo-based gap filling remains unproven.',50,180,1170,140,44,C.ink,true);
 table(s,[['Real stereo','Largest completed footprint','Learned-video evaluation'],['50 / 56 observations','77.2 m²; 31% observed cells','No returned results yet']],50,375,1180,150,[1,1.35,1.3],26);
 text(s,'13-slide main update + detailed technical appendix',50,561,1180,35,24,C.muted);

 s=slide(p,'Inputs and the established reconstruction pipeline','Real stereo',
 'These are the actual rectified left/right inputs for obs_034, not generated images. Each image is 1024 by 1024. There are 56 candidate stereo observations, not 56 video frames. Left and right exposure times are often separated by roughly 30–43 seconds, so fixed-rig reconstruction assumes the rover did not move materially between the exposures. The pipeline uses CAHV calibration, rectification, SGBM, support filtering, local triangulation, and registration only when overlap supports it. Totals are per-frame, with overlap, not unique globally mapped terrain.',
 ['artifacts/runs/r08_quality_batch/obs_034/rectified_left.png','artifacts/runs/r08_quality_batch/obs_034/rectified_right.png','RECONSTRUCTION_REPORT.md'],1.1);
 image(s,'artifacts/runs/r08_quality_batch/obs_034/rectified_left.png',50,164,285,285,'Actual obs_034 rectified left image');
 image(s,'artifacts/runs/r08_quality_batch/obs_034/rectified_right.png',355,164,285,285,'Actual obs_034 rectified right image');
 text(s,'obs_034 LEFT',50,455,280,30,21,C.muted,true);text(s,'obs_034 RIGHT',355,455,280,30,21,C.muted,true);
 bullets(s,['Calibrate and rectify the real pair','Match disparity; reject weak support','Triangulate and mesh local terrain','Register only supported overlaps'],690,168,530,86,25);
 text(s,'56 pairs → 50 accepted local reconstructions\n4.97 million per-frame points · 508,095 triangles',50,528,1150,74,28,C.ink,true);

 s=slide(p,'Closing holes increases coverage, not measured evidence','Real terrain completion',
 'For obs_034 the 5 cm grid is cropped to 0.75–6 m forward and ±2 m sideways. Strict support occupies 73.8% of the chosen hull. Gated relaxed stereo adds 314 cells; interpolation fills 851. The completed top has 10.695 m² projected triangle area. The later closed OBJ adds walls and a base without changing the top: 8,882 vertices and 17,760 triangles, with no open/nonmanifold edges. This is a topological property, not an accuracy certificate. Grid spacing is not accuracy. The current metric convention interprets the calibrated baseline as 242.0594 mm, consistent with the paper’s nominal 240 mm; gravity remains unverified.',
 ['artifacts/runs/r15_terrain_completion/obs_034/completion_metrics.json','output/closed_terrain/obs_034/validation.json','TERRAIN_COMPLETION.md'],1.1);
 image(s,'artifacts/runs/r11_filtered_batch/obs_034/mesh_views.png',45,155,595,380,'Strict obs_034 mesh render');
 image(s,'output/completed_terrain_renders/obs_034_closed_obj.png',660,155,575,380,'Actual closed obs_034 OBJ render');
 text(s,'Strict observed mesh',50,542,550,35,24,C.teal,true);text(s,'Completed + artificial walls/base',660,542,570,35,24,C.teal,true);
 takeaway(s,'10.70 m² completed top · strict cell heights preserved · hidden hazards remain unknown');

 s=slide(p,'Largest completed terrain: five registered observations','Real terrain result',
 'The component anchored at obs_044 includes observations 044,045,046,047,048. Five stereo pairs supply ten input images. The completed top spans 11.4 by 11.6 metres in its bounding rectangle, with 77.20125 m² projected footprint. Observed support is 9,573 of 30,900 grid cells, or 30.98%; 21,327 are filled. Maximum fill distance is 2.42 m. The closed OBJ has 61,800 vertices and 123,596 triangles, one connected component and no boundary/nonmanifold edges or vertices. It has not been validated as a Blender/Gazebo collision or navigation asset in this evidence set. The figure is a render of the actual OBJ, not a Blender validation screenshot.',
 ['output/largest_terrain/component_obs_044/metrics.json','output/completed_terrain_renders/component_obs_044_closed_obj.png'],1.2);
 image(s,'output/completed_terrain_renders/component_obs_044_closed_obj.png',40,155,755,455,'Full completed OBJ for registered observations 044–048');
 table(s,[['Quantity','Result'],['Input observations','5 (044–048)'],['Completed top area','77.20 m²'],['Observed grid fraction','31.0%'],['Filled grid fraction','69.0%'],['Closed OBJ triangles','123,596']],825,173,405,370,[1.22,1],23);
 takeaway(s,'A continuous closed surface is available; most of its footprint is inferred');

 s=slide(p,'All observations on an approximate rover traverse','Pose evidence',
 'This new overlay superimposes real stereo samples from all 50 accepted observations, and labels all 56 observations. The route integrates turn/drive commands from the revised SIS Appendix I, pages 52–54. Existing registered groups keep their internal relative poses, then are anchored to the approximate route. Global heading is arbitrary, and slip, exact timing, gravity and some command directions are unresolved. Asterisks mark six additional image/checkpoint ambiguities. The plot is an illustrative scenario and is not installed in the production pose graph. Overlap on this plot does not prove correspondence or global alignment.',
 ['output/all_observations_overlay/README.md','output/all_observations_overlay/overlay_provenance.json','chandrayaan-3-documentation/nav/document/ch3_nav_pds_dp_archive_sis.pdf'],1.0);
 image(s,'output/all_observations_overlay/traverse_plot_for_slides.png',40,148,760,490,'All 56 observations and 50 terrain reconstructions on a command-derived approximate path');
 text(s,'56 observations\n50 stereo reconstructions',825,164,405,93,30,C.ink,true);
 text(s,'Color: early → late\nDashed line: commanded route\nHollow: no accepted terrain\n*: uncertain imaging stage',825,295,405,155,25);
 text(s,'ILLUSTRATIVE PLACEMENT\nNo measured global pose track.\nHeading, slip and timing\nremain uncertain.',825,490,405,135,25,C.orange,true);

 s=slide(p,'Two generated stereo pairs failed the camera checks','Generated stereo experiment',
 'The original generated side-by-side canvases were split losslessly, with separate 1024-square analysis copies. These are two generated pairs, not tests of multiple learned video models. The fixed CAHV camera relationship fails. The production gate requires at least 40 matches, median row error ≤1 pixel and p90 ≤2 pixels. Gate statistics shown use the production feature selection; the independent reciprocal-match report has different counts and should not be mixed with this table. Dense diagnostics bypassed the failed pair gate but still retained almost no support. The generated meshes use arbitrary baseline units, not metres.',
 ['output/generated_stereo_trial/REPORT.md','output/uber_relaxed/REPORT.md'],1.0);
 image(s,'output/generated_stereo_trial/stereo_trial_1/original_canvas.png',50,158,700,350,'Generated stereo trial 1 with left and right views');
 table(s,[['Gate statistic','Trial 1','Trial 2'],['Usable matches','1,313','19'],['Median row error','8.06 px','26.61 px'],['90th percentile','10.36 px','28.36 px'],['Strict pixels*','0.55%','0.61%'],['Relaxed pixels*','4.12%','4.00%']],785,167,445,380,[1.5,1,1],21);
 text(s,'*Whole-image acceptance in diagnostics that bypassed the failed camera gate',50,559,1160,35,21,C.muted);
 takeaway(s,'These two outputs violate our stereo assumptions; this is not a universal failure of generation');

 s=slide(p,'Relaxing checks creates density and severe artifacts','Generated stereo result',
 'Trial 1 illustrates why coverage is not correctness. Uber accepts 30.1% of all pixels; no-checks accepts 85.5%, but its median held-out disparity disagreement is 127.34 pixels. The row-adjusted test fits a vertical affine warp on 80% of image matches and checks the remaining 20%; it is a changed camera model, not only a loose threshold. It reaches 45% acceptance with 0.29 pixel median disparity disagreement on 279 accepted held-out features. That selected-feature result does not certify physical camera pose, metric scale, or the unseen pixels. The displayed meshes preserve the experimental geometry and remain open surfaces.',
 ['output/uber_relaxed/REPORT.md','output/generated_stereo_slide_pack/SLIDE_COPY_AND_FIGURE_GUIDE.md'],1.0);
 image(s,'output/generated_stereo_slide_pack/02_mesh_comparison_trial_1.png',50,153,1180,386,'Actual generated stereo mesh comparison with visible spikes and fragments');
 text(s,'Trial 1 accepted pixels: uber 30.1% · no checks 85.5% · row-adjusted 45.0%',50,554,1175,35,25,C.ink,true);
 takeaway(s,'More triangles do not repair inconsistent stereo geometry');

 s=slide(p,'The procedural video loop runs end to end','Video generation and reconstruction',
 'This contact sheet shows real endpoint observations plus procedural intermediate views. The procedural generator renders a textured heightfield along 33 camera poses; it is not Wan, VACE or MarsGen. The independent reconstruction route decodes video pixels and uses tracking/triangulation plus dense height-plane matching. It does not read rendered ground-truth depths. However the experiment is still prior-conditioned: endpoint terrain and the support/height envelope constrain the result. Original runs used rendering poses at 512 resolution; the external control uses estimated PnP poses at 480 resolution. Do not compare those runs as a controlled model ablation. Learned-video input bundles are prepared, but a learned output ZIP has not been received.',
 ['output/chronological_video/REPORT.md','output/chronological_video/figures/video_contact_sheet.png'],1.1);
 image(s,'output/chronological_video/figures/video_contact_sheet.png',50,150,1180,400,'Contact sheet of actual procedural video outputs and real endpoints');
 text(s,'33-frame clips · real stereo endpoints · procedural intermediate imagery',50,560,1170,35,27,C.ink,true);
 takeaway(s,'The evaluation machinery runs; no learned-generator terrain result is available yet');

 s=slide(p,'Cross-frame checks are implemented, with limits','Validation',
 'For the 480-pixel procedural control, anchor features with stereo depth establish per-frame PnP poses. Separate held-out features and agreement between endpoint anchors check pose consistency. Sparse three-view tracks are triangulated from the outer views and reprojected into the middle view. Accepted sparse points have median reprojection residual 0.322 px, p90 0.704 px and p95 0.779 px. These statistics are after filtering and are internal consistency measures, not ground-truth lunar errors. All 33 camera poses were accepted; 24 unconditioned frames were used for terrain reconstruction. Shared calibration and anchor depth can bias both checks. PnP acceptance does not show that a clip has useful parallax.',
 ['output/collaboration_review/v2_control_2026-11-09/pose_check/metrics.json','output/collaboration_review/v2_control_2026-11-09/evaluation/metrics.json','reconstruction/video_pose_check.py','reconstruction/video_triangulate.py'],1.2);
 text(s,'Triangulate in views A and C\n→ project the 3D point into view B\n→ compare against the tracked image point',50,170,610,170,32,C.ink,true);
 text(s,'Reprojection residual = image-space distance\nbetween predicted and observed locations',50,370,600,80,26,C.muted);
 table(s,[['480-pixel positive control','Result'],['Accepted camera poses','33 / 33'],['Unconditioned frames used','24'],['Accepted sparse points','16,752'],['Median / p90 reprojection','0.322 / 0.704 px'],['Reference-covered new cells','21 / 561']],700,168,530,386,[1.7,1],23);
 takeaway(s,'Low reprojection error is necessary evidence, but it does not prove correct unseen terrain');

 s=slide(p,'Video completion has not beaten interpolation','Primary quantitative result',
 'The reference region is fixed at 561 eligible cells from withheld real stereo obs_046. It is not a surveyed ground truth. The baseline completes the region using strict-stereo linear interpolation. For each video result, replace only accepted video cells, leaving linear interpolation everywhere else, then evaluate the whole same region. The linear baseline is 1.052 cm RMSE; IDW is 2.494 cm. Video plus linear fallback produces 3.710, 3.419 and 1.407 cm for the listed variants. Only 12 cells are shared by all three video support masks, and protocols/resolutions differ, so this is evidence against benefit in these tests, not a learned-model ranking. Retain both coverage and fixed-region error when testing learned outputs.',
 ['output/collaboration_review/2026-11-09/COMPARISON_FINDINGS.md','output/collaboration_review/2026-11-09/baseline_comparison/comparison.json'],1.5);
 s.charts.add('bar',{position:{left:50,top:175,width:650,height:370},categories:['Linear','Seed 7 + linear','Consensus + linear','PnP control + linear'],series:[{name:'Height RMSE (cm)',values:[1.052,3.710,3.419,1.407],fill:C.teal}],hasLegend:false,barOptions:{direction:'column',gapWidth:85},dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:FONT,fontSize:21}},xAxis:{textStyle:{typeface:FONT,fontSize:18}},yAxis:{min:0,max:4.2,title:'Height RMSE (cm)',textStyle:{typeface:FONT,fontSize:20},majorGridlines:{fill:C.line,width:1}}});
 table(s,[['Video variant','Reference support'],['Single seed','143 / 561 (25.5%)'],['Three-seed agreement','85 / 561 (15.2%)'],['Estimated-pose control','21 / 561 (3.7%)']],745,197,485,286,[1.05,1.1],23);
 text(s,'Same 561 cells; linear fill remains elsewhere. Reference: withheld stereo, not survey truth.\nVariants use different frame/pose protocols; this is not a model ranking.',50,548,1160,63,21,C.muted);
 takeaway(s,'Best baseline: 1.052 cm RMSE · none of these procedural additions improves it');

 s=slide(p,'The non-overlapping bridge is a conditional hypothesis','033 → 034 experiment',
 'The plot connects actual terrain from obs_033 and obs_034 using the documented command: 10° CCW then 4 m forward. The ideal planar translation is (3.939, 0.695) m in the assumed initial body frame. Image registration does not establish this relative pose. Shared height fitting estimates elevation and tilt conditional on the horizontal assumption, and the vertical fit reaches a search bound. The closed completion covers 49.98 m²: 9,872 strict cells, 253 relaxed cells, 994 consensus-video cells and 8,888 linear cells. Only 250 video-supported cells lie outside both endpoint hulls, or 0.625 m² of a 5.94 m² between-footprint region. This is a terrain hypothesis, not measured gap recovery.',
 ['output/pose_explanation/REPORT.md','output/chronological_video/mid036_model/metrics.json','output/chronological_video/REPORT.md'],1.1);
 image(s,'output/pose_explanation/03_reconstructions_with_rover_path.png',40,150,1195,408,'Two real reconstructions placed with a conditional rover motion prior');
 text(s,'49.98 m² completed envelope · only 0.625 m² of the between-footprint region has video support',50,566,1170,55,25,C.ink,true);
 text(s,'Placement and unseen geometry remain assumptions',50,625,1170,35,25,C.orange,true);

 s=slide(p,'Progress against the October 28 requests','Meeting follow-through',
 'This table maps the provided October 28 meeting requests to the available evidence. Cross-frame reprojection exists but the negative controls expose missing dense-parallax acceptance. The actual reconstructed OBJ has been rendered for inspection, but there is no verified Blender import/real-versus-sim/navigation run in this evidence set. Earlier SAM2 masks exist, but no reviewed semantic priors are integrated. Twelve candidate generation families are listed in the appendix, but listing is not testing; more than ten completed method evaluations and an evidence-based choice remain outstanding. The status refers to artifacts available here and does not claim the colleague has done no work elsewhere.',
 ['output/collaboration_review/README.md','report_evidence/sam2_inventory.json','https://app.notion.com/p/Capstone-Meeting-w-Dr-Fan-4145a3b3d36181a5acd7c14988a2c0a8'],1.0);
 table(s,[['Requested evidence','Current state','Still needed'],['Inputs, counts, meshes, tables','Available; shown here','Use the same evidence in each update'],['>10 video methods + selection','Not completed here','Run and score >10 distinct methods'],['Cross-frame reprojection','Implemented; control tested','Dense parallax gate + failure tests'],['Actual terrain in Blender','OBJ rendered; import unverified','Import, camera renders, sim comparison'],['Traversability diagnosis','Steep slopes / fill documented','Reproduce planner failure + isolate causes'],['Rock/crater priors','843 SAM2 mask proposals exist','Review classes, link reliable 3D support']],50,158,1180,417,[1.05,1.2,1.5],22);
 takeaway(s,'The main blockers are geometric validation and missing learned-model results');

 s=slide(p,'Next experiments and decision criteria','Next work',
 'The first priority is to harden the evaluation before accepting learned outputs: require per-cell geometric parallax and preserve temporal gaps; frozen images and crossfades must not be promoted as valid bridges. The colleague runs learned generators on their own GPU and returns a ZIP of videos, exact model/config/seed details and hashes. Independent review checks those results with the same evaluator and fixed reference split. Jarvis is available but not a dependency for that GPU work. Run more than ten distinct methods across both open and closed families with explicit conditioning tiers. Wan/VACE is an implementation candidate, not a benchmark winner. Independently, the navigation owner should import the actual closed mesh in Blender and reproduce the traversability failure. Only after the generator comparison should a reconstruction-model ablation change the current baseline.',
 ['output/collaboration_review/negative_controls_2026-11-09/FINDINGS.md','output/collaboration_handoff','output/chronological_video/REPORT.md'],1.1);
 bullets(s,['Harden acceptance: per-cell parallax, temporal gaps, duplicate-seed and provenance checks','Receive the colleague’s learned-video ZIP; evaluate it against unchanged baselines','Benchmark >10 methods using matched tasks, conditioning tiers and repeat trials','Import the actual terrain into Blender; diagnose the traversability failure'],50,170,1170,95,28);
 takeaway(s,'Promote a method only if useful coverage improves without worsening fixed-region terrain error');

 s=slide(p,'Camera calibration, units and acquisition assumptions','Appendix · inputs',
 'The current working scale follows the LPSC abstract’s nominal 240 mm camera baseline and the calibration baseline of 242.0594 units interpreted as mm. New terrain_*_m.obj exports already use metres and should not be scaled by 0.001 again. Older per-frame files named calibration_units require the documented conversion. The calibration is a fixed rig model; differing timestamps create an unverified stationary-rover assumption. Absolute lunar position and gravity are not recovered from these records.',
 ['TERRAIN_COMPLETION.md','RECONSTRUCTION_REPORT.md','C:/Users/rhunt/Downloads/1180 Digital Elevation Model Generation from Navigation Cameras.pdf']);
 table(s,[['Input or assumption','Value / consequence'],['Stereo imagery','56 left/right candidate pairs; 1024 × 1024 images'],['Camera model','Archive CAHV calibration; fixed stereo rig'],['Calibrated baseline','242.0594 units; working interpretation: millimetres'],['Supporting nominal baseline','240 mm in Iyer et al., LPSC 2024 abstract 1180'],['Timing','Typical left/right separation ~30–43 s; motion is a risk'],['Export units','terrain_*_m.obj is already in metres'],['Orientation','Nominal rover-up; gravity and global heading unverified']],50,160,1180,416,[1,2.1],24);
 takeaway(s,'Metric convention is documented; this does not establish absolute physical accuracy');

 s=slide(p,'Strict stereo and the gated relaxed completion','Appendix · parameters',
 'These are the real-imagery completion settings, separate from the generated-image sweep. Both retain the fixed-camera geometry admission and real raw-information mask. Relaxed candidates may only add empty grid cells after spatial and height gating. Strict occupied medians remain unchanged. The baseline dense disparity floor of 16 px differs from the 32 px floor in the final support-filtered batch; name the stage when reporting it.',
 ['TERRAIN_COMPLETION.md','RECONSTRUCTION_REPORT.md']);
 table(s,[['Parameter','Strict','Relaxed completion'],['SGBM block / uniqueness','5 × 5 / 15','7 × 7 / 5'],['Left–right error','≤1 px','≤2 px'],['Local texture standard deviation','≥2','≥1'],['Speckle component size','100','50'],['Support median / neighbours','≤2 px / ≥8','≤3 px / ≥5'],['Support component size','≥200 pixels','≥50 pixels'],['New terrain-cell acceptance','Original occupied median','≤20 cm from support; height envelope']],50,158,1180,430,[1.6,1,1.25],23);
 text(s,'Height envelope: |Δz| ≤ 0.04 m + tan(35°) × support distance; heuristic, not an error guarantee',50,610,1180,50,23,C.orange,true);

 s=slide(p,'Registration supports local groups, not a global map','Appendix · real-image registration',
 'The 50 accepted local frames form 37 disconnected components: six multi-image groups and 31 singletons. Mutual SIFT matches use a 0.75 ratio threshold. Correspondences with valid depth enter PnP; 20% are held out. Gates require at least 30 depth correspondences, 20 inliers, 50% inlier fraction, held-out median error ≤2 px and p90 ≤4 px, 120 px span in both axes, positive depth, eight target-depth checks and median relative 3D discrepancy ≤3%. Example 044→047 has 135 matches, 55 depth correspondences, 44 inliers and 11 held-out points. Its median 0.489 px, p90 0.761 px and 1.85% median relative 3D discrepancy measure consistency, not external accuracy.',
 ['RECONSTRUCTION_REPORT.md','output/pose_explanation/figure_provenance.json','artifacts/runs/r12_registration/component_obs_044/camera_trajectory.json']);
 table(s,[['Registered multi-image group','Frames'],['003–004','2'],['005–006','2'],['010, 012, 013, 014','4'],['029–031','3'],['044–048','5'],['051–053','3']],50,161,515,379,[1.7,.6],24);
 text(s,'37 disconnected components\n6 groups + 31 singletons',625,170,590,88,34,C.ink,true);
 text(s,'044 → 047 held-out check\n0.489 px median reprojection\n0.761 px at the 90th percentile\n1.85% median relative 3D discrepancy',625,308,590,190,28);
 takeaway(s,'Rejected observations: 015, 032, 036, 037, 043, 050');

 s=slide(p,'Generated stereo: what each relaxation changes','Appendix · generated-image rules',
 'The generated diagnostic gate was deliberately relaxed to at least 16 matches, median row error ≤30 px and p90 ≤60 px. The production gate remains at least 40 matches, median ≤1 px and p90 ≤2 px. These settings admit a computation; they cannot make horizontal SGBM search different image rows. No-checks still requires positive disparity, image bounds, rectification overlap and the search range. Row adjustment changes alignment through a fitted vertical warp. All generated meshes remain in arbitrary baseline units.',
 ['output/uber_relaxed/REPORT.md']);
 table(s,[['Profile','What changes','Interpretation'],['Strict / relaxed diagnostic','Camera gate bypassed; matching filters retained','0.55% / 4.12% trial-1 pixels'],['Uber relaxed','Uniqueness 0–2; LR up to 16 px; weaker masks','30.1%; suspect matches'],['No checks','External LR off; internal 512 px; weak mesh limits','85.5%; spikes / sky geometry'],['Wide window','21 × 21 matching block','60.7%; gross mismatch'],['Row-adjusted','Fit vertical warp on 80% of features','45.0%; changed camera model'],['Tighter row-adjusted','Restore LR, uniqueness, speckle, mesh gates','25.1% / 19.1%; still modified']],50,160,1180,427,[1,1.7,1.3],22);
 takeaway(s,'“No checks” means most rejection disabled; it does not mean unconstrained or validated');

 s=slide(p,'Generated stereo: accepted pixels and disparity','Appendix · diagnostic evidence',
 'Trial 1, full seven-profile comparison. Top: white pixels are accepted; black pixels rejected. Bottom: disparity is shown from 0–512 px, with white indicating invalid pixels. Percentages divide by the whole image, including sky. They are not terrain coverage or accuracy. Thick bands and regions near the disparity limits indicate failures. Row adjustment materially improves held-out feature disparity on these images, but provides no 3D ground truth.',
 ['output/uber_relaxed/REPORT.md','output/uber_relaxed/stereo_trial_1/comparison.png']);
 image(s,'output/uber_relaxed/stereo_trial_1/comparison.png',35,165,1210,400,'Seven trial-1 acceptance masks and disparity maps');
 takeaway(s,'Trial 1 no-checks: 85.5% pixels accepted, but only 40.0% pass a 2 px LR check');

 s=slide(p,'Generated stereo: full geometry from all seven tests','Appendix · mesh evidence',
 'These are actual renders of the experimental OBJ geometry for all seven trial-1 profiles. No outlier cropping, hole filling or manual smoothing was used to improve the previews. Keep OBJ, MTL and texture files together when viewing. The geometry is in arbitrary baseline units and consists of open experimental surfaces. Dense coverage and largest-component fraction should be interpreted alongside held-out image agreement.',
 ['output/uber_relaxed/REPORT.md','output/uber_relaxed/stereo_trial_1/renders/all_seven_meshes.png']);
 image(s,'output/uber_relaxed/stereo_trial_1/renders/all_seven_meshes.png',35,152,1210,447,'All seven full experimental mesh renders');
 takeaway(s,'Connectivity increases when rejection is removed, while geometry can become less credible');

 s=slide(p,'Procedural generation and independent reconstruction','Appendix · closed loop',
 'Generation begins with accepted endpoint stereo and a relative pose or conditional prior. A 5 cm textured heightfield with stochastic relief in holes is rendered along 33 poses. Reconstruction uses decoded frames, intrinsics, estimated or provided poses and support, not generator depths. Sparse outer-view triangulation with middle-view reprojection and dense height-plane sweeps supply candidate heights. A ±0.20 m envelope around endpoint interpolation limits outliers. Consensus requires at least two of three seeds to agree within 4 cm. Strict stereo wins; gated real relaxed stereo can add cells; consensus video fills unmeasured cells; linear interpolation fills the remainder. This is image-driven but still prior-conditioned.',
 ['output/chronological_video/REPORT.md','reconstruction/video_bridge.py','reconstruction/video_triangulate.py','reconstruction/video_integrate.py']);
 bullets(s,['Real stereo + relative-pose hypothesis → textured terrain proposal','Render 33 monocular views; retain provenance and support masks','Decode video → estimate output poses → three-view / dense reconstruction','Apply support and height gates; require cross-seed agreement','Integrate labelled sources; compare against withheld real stereo'],50,163,1180,85,27);
 takeaway(s,'The generator’s depth is not read back; the terrain prior still constrains what can be accepted');

 s=slide(p,'Video reconstruction: additional controlled tests','Appendix · actual results',
 'All results are procedural, not learned. Height RMSE compares video and baselines on the same scored cells within each row. Rows use different splits and cannot rank methods directly. The 0.5 m and 1 m depth-hole cases retain photographs and poses estimated before masking depth; they are not whole-observation holdouts. The 045→048 case had only four scored cells and is not included as an accuracy claim. The reference is noisy stereo reconstruction, not survey truth.',
 ['output/chronological_video/REPORT.md','output/collaboration_review/v2_control_2026-11-09/evaluation/metrics.json']);
 table(s,[['Experiment','Scored cells','Video RMSE','Matched baseline'],['044 → 047; holdout 046','143 / 561','7.16 cm','IDW 3.78 cm'],['Three-seed consensus','85 / 561','8.45 cm','Linear 1.25; IDW 3.52 cm'],['044 → 048; holdout 046','210 / 763','11.08 cm','IDW 2.83 cm'],['Fixed-pose hole: 0.5 m','675 / 2,377','8.06 cm','IDW 2.48 cm'],['Fixed-pose hole: 1.0 m','1,245 / 3,814','7.37 cm','IDW 4.02 cm'],['PnP / unconditioned control','21 / 561','4.90 cm','Linear 0.85; IDW 0.77 cm']],50,160,1180,425,[1.65,1,1,1.45],23);
 takeaway(s,'No demonstrated improvement over the matched interpolation baseline in these tests');

 s=slide(p,'Negative controls expose an acceptance gap','Appendix · failure analysis',
 'A 33-frame frozen clip repeats the first endpoint, including its final frame. All 31 unconditioned poses pass PnP, but there are zero sparse triangulated points. The dense route adds four cells, none overlapping the reference. A crossfade has 24/31 accepted poses, 292 sparse points, 49 candidate cells and just one of 561 scored reference cells. Its estimated camera jumps 0.887 m over an eight-frame index gap. The current pipeline can export candidate meshes with success status, so downstream checks must prevent promotion of these invalid traversal controls. Add per-cell parallax and ray-geometry checks and retain original indices. A valid stationary-camera pose does not imply useful triangulation.',
 ['output/collaboration_review/negative_controls_2026-11-09/FINDINGS.md','output/collaboration_review/negative_controls_2026-11-09/negative_control_review.json']);
 image(s,'output/collaboration_review/negative_controls_2026-11-09/pose_progression.png',50,155,720,400,'Estimated camera progress for frozen and crossfade negative controls');
 table(s,[['Diagnostic','Frozen','Fade'],['PnP frames','31 / 31','24 / 31'],['Sparse points','0','292'],['New candidates','4 cells','49 cells'],['Scored cells','0 / 561','1 / 561']],795,170,435,352,[1.4,1,1],23);
 takeaway(s,'Accepted poses and a nonempty mesh are insufficient; require actual multi-view parallax');

 s=slide(p,'A good height fit can coexist with wrong placement','Appendix · pose sensitivity',
 'Independent review examined nine illustrative command variants: distances of 3.5, 4 and 4.5 m, each at turns of 5, 10 and 15 degrees. These are sensitivity cases, not measured confidence intervals. Six height fits pass and five hit vertical bounds. The 4 m / 5° case has 1.13 cm median height residual but 0.997 m p90 displacement from nominal placement. The 4.5 m / 5° case has 0.71 cm residual and 1.188 m displacement. The 15° cases lack shared support. Height agreement alone cannot identify horizontal pose or yaw. Choosing the best surface fit would require independent constraints.',
 ['output/collaboration_review/pose_sensitivity_2026-11-09/FINDINGS.md','output/collaboration_review/pose_sensitivity_2026-11-09/pose_sensitivity.csv']);
 image(s,'output/collaboration_review/pose_sensitivity_2026-11-09/pose_sensitivity.png',45,155,1190,420,'Sensitivity of terrain alignment to assumed drive distance and turn angle');
 takeaway(s,'Example: 1.13 cm height residual, yet about 1.00 m spatial displacement from nominal');

 s=slide(p,'How the documentary pose prior was constructed','Appendix · source evidence',
 'Revised SIS Appendix I places MID 036 at day 243, 12:20:00 on 31 August 2023: turn 10° CCW and drive 4 m. The obs_033 left timestamp is 08:13:01.9172; obs_034 is 13:04:31.6922. Their ordering brackets the command but does not prove achieved odometry. Ideal planar translation is (4 cos10°, 4 sin10°). The conditional terrain fit gives a +0.409444726 m vertical offset and tilt rotation-vector components (-2.871°, -0.913°); its vertical parameter reaches a lower bound. Camera mounting offset and rectification are included when converting body to camera poses. Intermediate turn/drive timing is assumed.',
 ['output/pose_explanation/REPORT.md','chandrayaan-3-documentation/nav/document/ch3_nav_pds_dp_archive_sis.pdf']);
 image(s,'output/pose_explanation/01_documentation_to_pose.png',45,151,1190,450,'Source mobility entry and documented derivation of the conditional pose');
 takeaway(s,'Commanded movement constrains a scenario; it is not a released measured pose trajectory');

 s=slide(p,'Completion validation with hidden terrain disks','Appendix · real-stereo interpolation',
 'Remove physical disks from strict observed height cells, exclude relaxed stereo, interpolate from the remaining strict cells and compare against withheld heights. Test up to 16 random and 16 relief-targeted centers per diameter, spaced at least 30 cm. Patches can overlap and are not independent samples. Predictions outside the training hull are excluded. Error ranges across obs_003, 029 and 034 show agreement on small gaps in observed terrain, but do not bound errors for inherently hidden rocks or craters. The largest discrepancy, 14.77 cm, occurred in a relief-targeted 1 m disk in obs_029.',
 ['TERRAIN_COMPLETION.md','artifacts/runs/r15_terrain_completion/summary.json']);
 table(s,[['Hidden disk diameter','Random p95 error','Relief-targeted p95'],['0.10 m','0.65–1.06 cm','1.46–3.02 cm'],['0.25 m','0.82–1.48 cm','1.75–3.36 cm'],['0.50 m','1.17–1.95 cm','2.13–2.78 cm'],['1.00 m','1.86–4.74 cm','1.74–6.40 cm']],50,167,1180,330,[1,1,1],27);
 text(s,'Three-scene pilot: obs_003 / 029 / 034\nMaximum individual discrepancy: 14.77 cm',50,533,1180,70,29,C.ink,true);
 takeaway(s,'Agreement with noisy stereo is measured; accuracy in unseen terrain is still unknown');

 s=slide(p,'Blender and traversability: evidence and diagnosis plan','Appendix · simulation',
 'There is no verified Blender import or planner output in this workspace evidence set. The reported lack of valid traversability still needs to be reproduced with the actual mesh. The largest obs_044 top has p95 slope 30.2069° and maximum 78.5150°, relative to nominal rover-up rather than measured gravity. Artificial walls and undersides are closure geometry and should not be treated as drivable terrain. Long fill distances can hide obstacles. Import terrain_closed_m.obj at scale 1, verify its 11.4 × 11.6 × 3.109 m bounding box, isolate the top, check normals and degenerate faces, then apply actual planner parameters incrementally and count rejection reasons. These are diagnostic hypotheses, not a confirmed root cause.',
 ['output/largest_terrain/component_obs_044/metrics.json','output/closed_terrain/obs_034/validation.json']);
 image(s,'output/largest_terrain/component_obs_044/preview.png',45,165,650,380,'Existing terrain support and completion preview for the largest mesh');
 bullets(s,['Import actual OBJ at scale 1; verify dimensions and axes','Separate terrain top from artificial walls/base','Count rejection by slope, roughness, clearance, unknown area and edge distance','Render from known cameras; compare to source photographs'],740,168,490,97,23);
 takeaway(s,'Mesh diagnostics: p95 slope 30.2° · maximum 78.5° · fill can extend 2.42 m from support');

 const inv=JSON.parse(await fs.readFile(ROOT+'/report_evidence/sam2_inventory.json','utf8'));
 s=slide(p,'SAM2 proposals exist; geometric priors remain a plan','Appendix · image priors',
 'The September 30 inventory found 224 CSV files and previews with 843 binary mask proposals across calibrated/raw left/right products. These are 224 image products from 56 stereo observations, not independent new views. Every manual-class field was blank; six image products had no retained masks. Binary geometry and CSV checks passed, but semantic quality was not evaluated. The current script uses SAM2.1 Hiera Tiny, 16 points per side, batch size 8, predicted IoU 0.8, stability 0.95 and minimum area 25 pixels; historical configuration hashes are unavailable. Next review classes and missed small rocks, associate reliable stereo depth and deduplicate objects. Statistical priors in unknown regions must remain distinguished from measured obstacles.',
 ['report_evidence/sam2_inventory.json','report_evidence/sam2_output_checks.json','MIDTERM_REVISION_NOTES.md']);
 image(s,inv.examples[0].preview,50,165,650,400,'Existing SAM2 mask proposal preview from actual lunar imagery');
 text(s,'843 proposals\n224 image products\n0 reviewed class labels recorded',755,176,470,145,32,C.ink,true);
 text(s,'Next: review rock/crater classes,\nattach reliable depth, deduplicate\nobjects, and preserve uncertainty.',755,362,470,130,27);
 takeaway(s,'Mask area in pixels is not rock size in metres; proposals are not verified objects');

 s=slide(p,'Open-model candidates for the required broad evaluation','Appendix · planned benchmark',
 'This is a screening slate, not completed experiments or a ranking. Count distinct generator families rather than multiple checkpoints as distinct methods. Wan/VACE is the first configured candidate and has no returned evaluated result yet. Open-weight/code terms and conditioning capabilities vary by checkpoint. Pin exact versions, licenses and adapters before testing. Some families may lack matched endpoint conditioning and belong in a separate qualitative tier. Replace ineligible candidates until more than ten methods have actual completed tests.',
 ['https://github.com/ali-vilab/VACE','https://github.com/Lightricks/LTX-Video','https://github.com/Tencent-Hunyuan/HunyuanVideo-I2V','https://github.com/zai-org/CogVideo','https://github.com/Stability-AI/generative-models','https://github.com/hpcaitech/Open-Sora','https://github.com/genmoai/mochi']);
 table(s,[['Candidate family','Role in evaluation','Local evidence'],['Wan / VACE','First configured masked-video candidate','Inputs prepared; output pending'],['LTX-Video','Alternative generation family','Not tested'],['HunyuanVideo-I2V','Image-conditioned candidate','Not tested'],['CogVideoX','Alternative image/video generation','Not tested'],['Stable Video Diffusion','Older image-to-video baseline','Not tested'],['Open-Sora','Additional open family','Not tested'],['Mochi','Broader generation / conditioning screen','Not tested']],50,158,1180,428,[1,1.5,1.2],23);
 takeaway(s,'Seven open families proposed; an entry on this list does not count as a completed test');

 s=slide(p,'Closed-model candidates and a fair comparison','Appendix · planned benchmark',
 'These five families make twelve screening candidates in total. Verify the exact offering, endpoint conditioning and account access at test time. Public documentation confirms the families, not availability on our accounts. Replace ineligible methods, then complete more than ten distinct method tests including open and closed models. Use identical real inputs and prompts where possible. Separate one-endpoint, two-endpoint and pose-anchor tiers; preserve original outputs and define common decoded frame sets. Run three trials per method and scenario, with seeds when available and recorded nondeterminism otherwise. Record cost, runtime and failures alongside visual quality, pose consistency, coverage and error. Wan is not preferred until the evidence supports it.',
 ['https://runway.com/','https://deepmind.google/models/veo/','https://ir.kuaishou.com/node/11216/pdf','https://docs.lumalabs.ai/reference/creategeneration','https://www.adobe.com/products/firefly/features/ai-video-generator.html']);
 table(s,[['Candidate family','Status'],['Runway','Not tested'],['Google Veo','Not tested'],['Kling','Not tested'],['Luma / Ray','Not tested'],['Adobe Firefly Video','Not tested']],50,165,490,360,[1.5,1],25);
 bullets(s,['Match real inputs and separate conditioning tiers','Repeat each scenario 3 times; retain failed runs','Score pose consistency, parallax, coverage and fixed-region error','Select by reconstruction utility; then compare reconstruction models'],595,171,625,95,25);
 takeaway(s,'Target: >10 completed methods, not >10 names, videos or parameter settings');

 s=slide(p,'Promotion gates and division of remaining work','Appendix · handoff',
 'Ownership reflects the agreed arrangement: the colleague uses their GPU for learned generation and owns implementation; independent review handles returned ZIP metrics, fixtures and reporting. No navigation owner is assigned by name. The ZIP should include original videos, exact model revision, configuration, prompt, seeds, input hashes, conditioned frame indices, inference environment and logs. Verify per-cell support, common frames, unique-seed fusion, hash binding and unchanged strict stereo. Require adequate reference coverage and no degradation against the fixed-region baseline; a numeric minimum coverage threshold has not yet been validated. Reprojection alone cannot separate pose and depth error: hold one fixed and perturb the other, first with known synthetic geometry and then a real holdout. Unobserved regions remain hypotheses even if checks pass.',
 ['output/collaboration_review/README.md','output/collaboration_review/2026-11-09/REVIEW.md','output/collaboration_review/negative_controls_2026-11-09/FINDINGS.md']);
 table(s,[['Workstream','Concrete deliverable','Acceptance evidence'],['Colleague / GPU work','Learned outputs ZIP; >10-method trials','Pinned model/config, repeats, hashes, failures'],['Evaluator implementation','Parallax + temporal-gap gates','Frozen/crossfade failures; positive control retained'],['Independent review','Common-split results and comparison','Coverage + reprojection + fixed-region error'],['Simulation / navigation','Actual OBJ imported into Blender','Camera comparison; per-cause rejection counts'],['Image priors','Reviewed rock/crater proposals','Semantic checks + reliable depth association']],50,165,1180,365,[1,1.5,1.5],23);
 text(s,'Pose/depth diagnosis: hold pose fixed and vary depth; then reverse the test.\nUse known-geometry controls before interpreting lunar residuals.',50,589,1180,65,24,C.orange,true);

 s=slide(p,'Stereo depth and the support-filtered output','Appendix · reconstruction mechanics',
 'Rectification aligns epipolar search along image rows using the calibrated cameras. SGBM estimates horizontal disparity d. In the rectified pinhole model, depth Z = fB/d, with focal length f in pixels and baseline B in consistent length units. Small disparities are particularly sensitive to disparity error. Brightness, texture, raw-information and left–right checks reject unreliable pixels. The later support filter removes weak local agreement and small components; neighbouring accepted samples form triangles only when depth jumps and edge lengths are sufficiently small. The figure is the actual final filtered obs_034 diagnostic, not a fabricated depth map. It shows why high-density-looking source imagery can still yield disconnected geometry.',
 ['artifacts/runs/r11_filtered_batch/obs_034/filtered_diagnostics.png','artifacts/runs/r11_filtered_batch/obs_034/metrics.json','RECONSTRUCTION_REPORT.md']);
 image(s,'artifacts/runs/r11_filtered_batch/obs_034/filtered_diagnostics.png',45,155,1190,389,'Actual obs_034 image support, depth map and point-cloud diagnostics');
 text(s,'Rectified depth: Z = fB / d   ·   f: focal length   ·   B: baseline   ·   d: disparity',50,565,1180,45,27,C.ink,true);
 takeaway(s,'Support filters and triangle limits deliberately leave holes where geometry is unreliable');

 s=slide(p,'Completed bridge: observed and inferred terrain','Appendix · integrated video result',
 'This is the actual integrated upper surface for the conditional 033→034 bridge. The grid retains explicit provenance: 9,872 strict stereo cells, 253 gated relaxed stereo cells, 994 consensus-video cells and 8,888 linear-interpolation cells. Those counts sum to 20,007 cells; the projected top-triangle area is 49.98125 m² and differs from simply multiplying every vertex cell by grid-cell area. An artificial base and sidewalls yield a closed OBJ with 40,014 vertices and 80,024 triangles. Topological checks find one component and zero boundary/nonmanifold edges or vertices. It remains a conditional, largely inferred terrain hypothesis. The grey completed path illustration elsewhere must not be mistaken for a recovered video surface.',
 ['output/chronological_video/mid036_model/metrics.json','output/chronological_video/figures/terrain_surface.png','output/chronological_video/REPORT.md']);
 image(s,'output/chronological_video/figures/terrain_surface.png',40,153,765,442,'Actual completed terrain upper surface with source attribution');
 table(s,[['Source','Grid cells'],['Strict stereo','9,872'],['Relaxed stereo','253'],['Video consensus','994'],['Linear fill','8,888']],835,182,395,322,[1.35,1],24);
 takeaway(s,'Video-supported cells are synthetic inference; strict measured cells remain unchanged');

 await fs.mkdir(OUT,{recursive:true});
 await fs.writeFile(OUT+'/slide_evidence.json',JSON.stringify(records,null,2));
 await fs.writeFile(OUT+'/figure_sources.json',JSON.stringify(figureSources,null,2));
 const report='# Reconstruction and video progress — 9 November 2026\n\nMain talk: slides 1–13 (~14 minutes plus questions). Slides 14–32 are the detailed appendix.\n\n'+records.map(r=>`## ${r.number}. ${r.title}\n\n${r.notes}\n\nSources:\n${r.sources.map(a=>'- '+a).join('\n')}\n`).join('\n');
 await fs.writeFile(OUT+'/DETAILED_REPORT_AND_SPEAKER_NOTES.md',report);
 return {slides:records.length,mainTalkMinutes:records.reduce((a,b)=>a+b.minutes,0),evidence:OUT+'/slide_evidence.json'};
}


