import fs from 'node:fs/promises';
import path from 'node:path';
export const ROOT='C:/Users/rhunt/Documents/Capstone/reconstruction';
export const OUT=ROOT+'/output/detailed_progress_2026-11-10';
const D=JSON.parse(await fs.readFile(OUT+'/atlas_manifest.json','utf8'));
const C={ink:'#183149',muted:'#52687B',teal:'#087E8B',orange:'#B7472A',bg:'#F7F9FC',line:'#CDD7E0'};
const N=v=>Number(v).toLocaleString('en-US');
const F=(v,n=2)=>v==null?'—':Number(v).toFixed(n);
const P=v=>F(100*v,1)+'%';
const CM=v=>v==null?'—':F(v*100)+' cm';
const absolute=v=>path.isAbsolute(v)?v:ROOT+'/'+v.replaceAll('\\','/');
export const specs=[];
const spec=(title,section,notes,sources,draw)=>specs.push({title,section,notes,sources,draw});
function tx(s,value,x,y,w,h,size=24,color=C.ink,bold=false){
 const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=String(value);a.text.style={typeface:'Arial',fontSize:size,color,bold,verticalAlignment:'top'};return a;
}
function im(s,src,x,y,w,h,alt){s.images.add({path:absolute(src),position:{left:x,top:y,width:w,height:h},fit:'contain',alt});}
function tb(s,values,x,y,w,h,widths,size=21){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnTracks:widths.map(value=>({mode:'fr',value})),values});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({textStyle:{typeface:'Arial',fontSize:size,color:C.ink},fill:'#FFFFFF',margins:{left:10,right:10,top:5,bottom:5},anchor:'center',borders:{bottom:{fill:C.line,width:1}}});
 t.cells.block({row:0,column:0,rowCount:1,columnCount:values[0].length}).assign({fill:C.ink,textStyle:{typeface:'Arial',fontSize:size,color:'#FFFFFF',bold:true}});return t;
}
function foot(s,v){tx(s,v,50,622,1180,44,21,C.orange,true);}
function legend(s,y=589){
 [['Strict stereo','#1F75A8'],['Gated relaxed','#26AD91'],['Video / synthetic','#F07814'],['Linear fill','#A3A8B0']].forEach(([name,color],i)=>tx(s,name,50+i*300,y,296,30,20,color,true));
}
const method=(title,rows,note,sources,extra='')=>spec(title,'Detailed methodology',note+'\n'+extra,sources,s=>{
 tb(s,[['Operation','Implementation and acceptance rule'],...rows],50,158,1180,410,[1,2.8],23);foot(s,extra);
});

spec('Detailed evidence atlas: what is actually available','Read this first',
 'Slides 1–13 remain the result-first 15-minute route. Slides 14–32 are the original technical appendix. This expanded atlas documents the actual saved outputs at the 10 November snapshot. It does not count multiple seeds, parameter sweeps or procedural controls as independent learned video methods. The all-observation rendering is an illustrative command-derived placement, not a global reconstruction. Individual mesh panels use independent complete extents, nominal up and no vertical exaggeration. Color on real/generated mesh panels is per-panel relative height; provenance colors on video panels have a different explicit legend. All OBJ faces are drawn; empty image margins are trimmed, geometry is not cropped.',
 ['output/detailed_progress_2026-11-10/atlas_manifest.json'],s=>{
 tb(s,[['Result inventory','Visible evidence','Interpretation'],['50 accepted local observations','Source image + full mesh for every observation','Observed, open surfaces'],['6 registered groups','Actual fused meshes + support counts','Local relative alignment'],['3 × 3 completion variants','Balanced / extended / simulation surfaces','Measured + inferred terrain'],['2 generated stereo trials','Strict / relaxed + 7 profiles each','Camera gate failed; arbitrary scale'],['15 saved video-derived surfaces','Mesh + labels + frames + result tables','Procedural controls / hypotheses'],['2 invalid temporal controls','Actual candidate meshes + failure counts','Acceptance weaknesses remain']],50,160,1180,408,[1.15,1.5,1.25],22);
 foot(s,'12 learned-model families are planned; no learned-generator result is available in this snapshot.');
});

method('1. Camera rays and metric convention',[
 ['CAHV projection','q = P − C; u = (H·q)/(A·q); v = (V·q)/(A·q). Use the supplied vectors literally.'],
 ['Pinhole equivalent','RQ factorization of M = [H; V; A]; normalize K by K33. Preserve skew and full ray ratios.'],
 ['Rectified camera','x axis along CR − CL; mean optical direction orthogonalized to x; y = z × x.'],
 ['Image warp','Hrect = Krect Rrect M⁻¹. f = 1400.979 px; virtual principal point (511.5, 511.5).'],
 ['Scale / orientation','Baseline = 242.0594 source units; exports use 0.001 m/unit, consistent with nominal 240 mm. Gravity remains unverified.']
 ],'Source CAHV has non-unit A vectors. Normalizing A alone changes the camera model. Original archival report predates the later nominal-baseline paper; metric outputs use the subsequent mm convention. Absolute scale uncertainty and calibration covariance are unavailable. Nominal rover-local Z is not independently measured lunar vertical.',
 ['reconstruction/geometry.py','RECONSTRUCTION_REPORT.md','TERRAIN_COMPLETION.md'],'Rig calibration provides relative rays; it does not provide the rover’s global trajectory.');

method('2. Pair admission and dense stereo matching',[
 ['Pair admission','≥40 feature matches after robust matching; rectified row residual median ≤1 px and p90 ≤2 px.'],
 ['Matching','Archived NC images; SGBM 3-way, 5×5 blocks, P1=200, P2=800, uniqueness=15.'],
 ['Disparity range','512 disparities; equal horizontal padding; crop back and reject unsupported source coordinates.'],
 ['Consistency','Reverse disparity sampled at u − d; |dL + dR| ≤1 px. Speckle window=100, range=2.'],
 ['Information masks','5 < intensity < 250; local standard deviation ≥2 DN over 7×7. Dilate raw clipped/dark pixels by 3×3.']
 ],'The pair gate checks the fixed calibrated rig, before dense matching. Fundamental-matrix estimation rejects feature mismatches but does not replace calibration. Raw masks prevent corrected gray values from disguising sensor saturation. Thresholds here are the production stereo stage, before the final r11 support filter.',
 ['reconstruction/stereo.py','artifacts/runs/r11_filtered_batch/obs_034/provenance.json'],'Failure of the calibrated pair gate cannot be fixed by accepting more dense pixels.');

method('3. Support filtering, triangulation and open meshes',[
 ['Support filter','16 px border; disparity ≥32 px; 5×5 median agreement ≤2 px; ≥8 initially valid neighbors.'],
 ['Connected support','Discard connected regions smaller than 200 pixels. Small genuine objects can also be removed.'],
 ['Backprojection','Z = fB/d; X = (u − cx)Z/f; Y = (v − cy)Z/f. Z is axial camera depth.'],
 ['Mesh construction','Sample valid vertices every 3 image pixels; connect only valid adjacent samples.'],
 ['Triangle rejection','Reject relative axial-depth jump ≥2% or longest edge ≥0.25 baseline. Leave gaps open.']
 ],'No smoothing, plane fitting or hole filling changes retained observed XYZ. Local coverage is whole-image pixel acceptance, not the fraction of lunar terrain recovered. The atlas converts exported camera coordinates to nominal rover coordinates only for display. Raw SGBM used disparity ≥16 before this support stage tightened it to 32.',
 ['configs/filtering.json','reconstruction/stereo.py','RECONSTRUCTION_REPORT.md'],'For small errors, σZ/Z ≈ σd/d; low disparity magnifies error, even with subpixel consistency.');

method('4. Register observations only where overlap supports it',[
 ['Propose links','Temporal separation ≤3 rows; ORB retrieval adds top 3 revisits with ≥25 ratio-test matches.'],
 ['Fit relative pose','Source SIFT features with stereo depth → target 2D points. Deterministic 80/20 fit/holdout split.'],
 ['PnP acceptance','≥30 3D–2D pairs; ≥20 inliers; ≥50% inliers; held-out median ≤2 px, p90 ≤4 px.'],
 ['Independent target depth','≥8 depth comparisons; median relative 3D disagreement ≤3%; feature span ≥120 px in both axes.'],
 ['Fuse each component','Compose accepted SE(3) edges; voxel size 0.025 baseline ≈6.05 mm. Record distinct-frame support.']
 ],'Target depth is checked after pose fitting, but both views share calibration biases. Non-tree edges are cycle diagnostics. This is not global bundle adjustment or a measured lunar trajectory. There are 37 components: six multi-observation groups and 31 singletons. Duplicated acquisitions can weaken the independence of view counts.',
 ['configs/registration.json','reconstruction/register.py','RECONSTRUCTION_REPORT.md'],'Fused voxel count and multi-view-supported voxel count are different quantities.');

method('5. Fill terrain holes while retaining source labels',[
 ['Grid / footprint','5 cm XY cells; median height with ≥2 points. Initial tests crop forward 0.75–6 m and lateral ±2 m.'],
 ['Relaxed stereo','7×7 blocks; uniqueness=5; LR≤2 px; texture≥1 DN; support neighbors≥5 and component≥50.'],
 ['Gate new cells','Distance to strict support ≤0.20 m; |Δheight| ≤0.04 m + tan(35°) × distance. Preserve strict heights.'],
 ['Interpolation extent','Balanced: fill within 0.25 m of support; extended: 0.50 m; simulation: entire chosen convex hull.'],
 ['Closure','Keep the top, add vertical perimeter walls and planar underside. Check topology after OBJ/STL readback.']
 ],'The footprint is a selected projected convex envelope, not surveyed terrain boundaries. Mesh projected area differs from cell count × grid area at boundary triangles. Closure removes open edges but cannot recover hidden craters, rocks, or correct an erroneous upper surface. Large unsupported spans have no terrain accuracy bound.',
 ['configs/completion.json','reconstruction/close_terrain.py','TERRAIN_COMPLETION.md'],'More complete geometry is useful for simulation; inferred areas must remain distinguishable.');

method('6. Construct a procedural monocular video',[
 ['Terrain proposal','Endpoint stereo anchors on a 5 cm grid; 12-neighbor IDW, weights 1/max(distance, 0.005 m)².'],
 ['Unknown-region relief','Noise at σ=1,3,9 cells; amplitudes 0.4,0.65,0.6; relief scale clipped to 3–40 mm.'],
 ['Camera path','33 poses; translation interpolation and rotation Slerp. Command-prior runs turn first, then drive.'],
 ['Rendering','512×512; first visible heightfield crossing over 0.28–11 m; 7 bisection refinements.'],
 ['Appearance / video','Project real endpoint textures onto one fixed surface; real first/last frames. 12 fps; 2.75 s playback.']
 ],'Noise is fixed in world coordinates and tapers with distance from anchors, rather than changing terrain through time. The two real endpoint images remain actual input photographs. Distant panorama appearance is excluded from geometric support. Playback length is not the rover’s physical travel duration. These clips are procedural, not learned diffusion outputs.',
 ['reconstruction/video_bridge.py'],'This creates a controlled image experiment from an assumed surface; it does not observe unknown terrain.');

method('7. Estimate and check poses from output frames',[
 ['Anchor correspondences','SIFT up to 8,000 features; contrast=0.02; reciprocal Lowe ratio 0.75. Real stereo supplies anchor 3D.'],
 ['PnP solve','≥30 correspondences; 20% holdout; EPNP RANSAC 2,000 iterations, confidence 0.999, then LM.'],
 ['Scaled thresholds','RANSAC 2s px; held-out median≤2s, p90≤4s; feature span≥120s per axis, s=resolution/1024.'],
 ['Pose acceptance','≥20 inliers; ≥50% inlier fraction; positive held-out depth. Rejected poses stay invalid.'],
 ['Two-anchor check','If both anchor solutions pass: reject disagreement >0.10 m or >2°. One-anchor solutions can still pass.']
 ],'Conditioned frames and unconditioned frames are reported separately. A frozen image can yield a valid stationary pose; this is not proof of reconstructable camera motion. Pose-check hashes bind the returned clip and anchor bundle. The current one-anchor path lacks an independent second-anchor depth test.',
 ['reconstruction/video_pose_check.py','reconstruction/evaluate_video.py'],'Pose reprojection tests image consistency; useful triangulation also needs parallax and stable geometry.');

method('8. Sparse video reconstruction: three-view geometry',[
 ['Track windows','Start every 3 frames; spans of 6 or 12 frames. Exclude clip endpoints; translation ≥0.045 m.'],
 ['Feature tracks','Up to 6,500 corners; quality=0.002, spacing=2 px. LK window 25×25, pyramid level 4.'],
 ['Track checks','Forward/backward error <0.6 px; intensity >9; eroded image support; avoid 4–5 px borders.'],
 ['Triangulate','Use outer views; require ray angle >0.45° and positive depth 0.4–11 m in all three views.'],
 ['Middle-view validation','Maximum three-view reprojection error <0.85 px. Grid cell needs ≥2 triangulated points.']
 ],'The small reported reprojection residuals are after rejection by the 0.85 px gate. They are not an independent 3D accuracy metric. In the external evaluator, selected valid frames are compressed into a new list; original index gaps remain recorded but are not fully retained in tracking-window construction. This is a known evaluation limitation.',
 ['reconstruction/video_triangulate.py','reconstruction/evaluate_video.py'],'Check geometry, accepted-cell coverage and withheld terrain error together.');

method('9. Dense video reconstruction: height-plane search',[
 ['Normalize appearance','Local mean/std with Gaussian σ=4 px; denominator ≥5 DN; clamp normalized values to ±3.'],
 ['Search candidates','Seven interior views; height planes every 0.01 m. Endpoint depth percentiles 0.1–99.9 ±0.4 m.'],
 ['Candidate support','≥4 valid views; positive depth 0.4–11 m; intensity>7 and local texture std>4 DN.'],
 ['Photometric cost','Variance across views, smoothed spatially with 3×3 Gaussian σ=0.7. Best cost <0.18.'],
 ['Uniqueness / bounds','Alternative ≥0.08 m away must cost >1.45×best+0.012. Reject bracket endpoints.']
 ],'The search is along height, not a free 3D point search. Best cost uniqueness excludes nearby levels by eight 1 cm steps. Dense reconstruction currently has no explicit per-cell ray-angle/parallax gate; frozen-video candidates demonstrate the resulting acceptance weakness.',
 ['reconstruction/video_triangulate.py'],'1 cm height search spacing is numerical resolution, not achieved terrain accuracy.');

method('10. Merge candidates, compare seeds, close the surface',[
 ['Sparse + dense','Reject sparse/dense height disagreement >0.10 m; use dense estimate when available.'],
 ['Prior envelope','Candidate must lie within ±0.20 m of endpoint IDW. Add only unmeasured cells inside support hull.'],
 ['Cross-seed consensus','≥3 unique seed IDs supplied; ≥2 votes per cell; available vote range ≤0.04 m; take median.'],
 ['Source priority','Strict stereo → gated relaxed stereo → consensus video → linear fallback. Keep provenance labels.'],
 ['Export','Grid-index Delaunay triangles, positive-Z winding; append artificial sides/base for closed export.']
 ],'Seed agreement measures repeatability under this prior, not external correctness. The seed integration audit also found that duplicate run entries can count as extra votes despite the unique-seed precondition; inputs must be de-duplicated before promotion. Height gates can improve surviving error by selecting a small subset and bias results toward the interpolation prior.',
 ['reconstruction/video_bridge.py','reconstruction/video_integrate.py','reconstruction/close_terrain.py'],'The visible completed mesh mixes evidence and inference; source proportions must accompany it.');

method('11. Evaluate pose and depth without survey truth',[
 ['Image consistency','Hold out correspondences from pose fitting; track outer views and check the middle view.'],
 ['Terrain reference','Exclude an observation from endpoint pose paths and terrain input; score against its registered stereo heights.'],
 ['Matched-cell baseline','Compute video and interpolation errors on exactly the same accepted reference cells.'],
 ['Fixed-region completion','Insert accepted video into linear fallback; score the entire predefined 561-cell reference region.'],
 ['Report jointly','Eligible / scored cells; coverage; median / p90 / RMSE; raw-before-envelope errors; failures and controls.']
 ],'Registered stereo is a noisy reference with shared calibration and possible pose bias, not ground truth. Spatial depth-mask tests retain endpoint photographs and already-estimated poses: they are easier than withholding an entire observation. The original exploratory rule requires ≥100 scored cells, median≤5 cm and p90≤15 cm, but passing this rule does not establish improvement over a baseline.',
 ['reconstruction/video_bridge.py','output/collaboration_review/2026-11-09/COMPARISON_FINDINGS.md'],'Compare methods on fixed data and matched protocols; do not rank different subsets or resolutions.');

method('12. Separate pose error from depth error',[
 ['Current evidence','Vary 3.5 / 4 / 4.5 m drive and 5 / 10 / 15° turn around the documentary prior; inspect placement and height fit.'],
 ['Observed ambiguity','A 1.13 cm median height fit coexists with ~1.00 m p90 spatial displacement from nominal placement.'],
 ['Next controlled ablation','Use the same frames and depth estimator with supplied render poses vs independently estimated poses.'],
 ['Depth-specific control','Hold poses fixed; compare sparse, dense and fused depths on one withheld region and identical support.'],
 ['Required diagnostics','Plot pose residuals, ray angle, source labels, slope and depth residuals in the same spatial frame.']
 ],'The existing sensitivity experiment illustrates non-identifiability; its variants are not confidence intervals. Six of nine variants passed the height fit and five reached vertical bounds. The additional ablations listed are proposed next work, not completed evidence. Keep rendering truth separate and use it only for controlled synthetic evaluation.',
 ['output/collaboration_review/pose_sensitivity_2026-11-09/FINDINGS.md'],'A smooth surface or good height fit alone cannot validate horizontal pose.');

// Every accepted observed mesh, with its actual rectified input and counts.
for(let start=0;start<D.local.length;start+=4){
 const rows=D.local.slice(start,start+4);
 spec(`Observed terrain atlas: ${rows[0].name.slice(4)}–${rows.at(-1).name.slice(4)}`,'All 50 accepted local reconstructions',
 'Each panel uses the actual saved r11 OBJ and left rectified image. All exported faces are rendered at true XYZ aspect, in nominal rover-local coordinates using the working millimetre convention. Panels have independent extents and independent relative-elevation colors; colors and apparent sizes cannot be compared quantitatively. Whole-image acceptance includes sky in the denominator. These are open observed surfaces, before completion or registration. Exact paths, extents, hashes and metrics are in atlas_manifest.json.',
 rows.flatMap(r=>[r.obj,r.metrics_source,r.input]),s=>{
 rows.forEach((r,i)=>{const x=50+(i%2)*610,y=152+Math.floor(i/2)*231;
 tx(s,r.name,x,y,580,30,25,C.teal,true);
 im(s,OUT+'/figures/'+r.name+'_input.png',x,y+38,142,142,`${r.name} actual rectified left input`);
 im(s,r.render,x+158,y+35,420,151,`${r.name} full observed OBJ; no filling`);
 tx(s,`${N(r.metrics.valid_points)} points · ${P(r.metrics.valid_fraction)} pixels · ${N(r.triangles)} triangles`,x,y+186,585,32,19);
 });foot(s,'Actual input → open observed mesh. Independent full extents; color shows relative height per panel.');
 });
}
for(let start=0;start<D.components.length;start+=3){const rows=D.components.slice(start,start+3);
 spec('Registered groups: '+rows.map(r=>r.name.slice(-3)).join(' / '),'All six registered multi-observation groups',
 'These are the all-observed union OBJ meshes from r12, not completed terrain. The exported meshes and the voxel cloud counts describe different representations. Report distinct-view support rather than implying all voxels have multiple views. Each panel has its own full spatial extent and elevation color range.',rows.flatMap(r=>[r.obj,r.metrics_source]),s=>{
 rows.forEach((r,i)=>{const x=50+i*400;tx(s,r.metrics.frames.map(v=>v.slice(4)).join(' + '),x,158,390,42,25,C.teal,true);im(s,r.render,x,206,380,236,'Actual fused open mesh '+r.name);
 tx(s,`${r.metrics.frames.length} stereo pairs / ${r.metrics.frames.length*2} images\n${N(r.metrics.fused_voxels)} fused voxels\n${N(r.metrics.multiview_supported_voxels)} supported by ≥2 views\n${N(r.triangles)} mesh triangles`,x,456,385,140,22);});
 foot(s,'Only six groups link multiple observations; the remaining 31 accepted views are singletons.');
 });}
for(const r of D.completion){const m=r.metrics;spec(`${r.name}: all three completion settings`,'Actual completed terrain variants',
 'All three models are rendered from their respective saved OBJ exports. Strict input heights are unchanged. Filled hull-cell fraction and projected triangle area have different boundary conventions. Simulation fills the whole hull, regardless of nearest-support distance. These renders show the top surface only; closure is separate.',[r.metrics_source,...Object.values(r.renders).map(x=>x.obj)],s=>{
 ['balanced','extended','simulation'].forEach((name,i)=>{const x=50+400*i,a=m.meshes[name];tx(s,name.toUpperCase(),x,158,385,35,24,C.teal,true);im(s,r.renders[name].render,x,207,380,220,`${r.name} ${name} actual terrain OBJ`);tx(s,`${P(a.convex_hull_cell_coverage)} hull cells covered\n${N(a.filled_cells)} interpolated cells\n${F(a.projected_surface_area_m2)} m² top · ${N(a.triangles)} faces`,x,442,385,112,22);});
 tx(s,`Strict support: ${N(m.original_grid_cells)} / ${N(m.hull_cells)} cells (${P(m.original_grid_coverage)}). New gated stereo: ${N(m.added_gated_stereo_cells)} cells.`,50,565,1180,42,24);
 foot(s,'Distance limits: balanced 0.25 m · extended 0.50 m · simulation unlimited inside the chosen hull.');
 });}
for(const trial of ['stereo_trial_1','stereo_trial_2']){const rows=D.generated_diagnostics.filter(r=>r.trial===trial);
 spec(`${trial}: strict and relaxed diagnostics`,'Generated stereo · original camera gate failed',
 'The original fixed-rig camera gate failed for this generated pair. These diagnostic runs bypass that gate to reveal what dense matching does. No raw sensor images exist, so raw-quality masking cannot be applied. Meshes use arbitrary baseline=1 scale. Numerical filter acceptance does not validate the geometry.',rows.flatMap(r=>[r.obj,r.metrics_source]),s=>{
 im(s,`output/generated_stereo_trial/${trial}/original_canvas.png`,50,157,480,240,'Original generated stereo canvas');
 rows.forEach((r,i)=>{const x=550+345*i;tx(s,r.name.toUpperCase(),x,158,330,35,25,C.teal,true);im(s,r.render,x,205,320,220,`${trial} ${r.name} full diagnostic OBJ`);tx(s,`${P(r.metrics.whole_image_valid_fraction)} accepted pixels\n${N(r.triangles)} triangles\nLR median ${F(r.metrics.left_right_error_px?.median)} px`,x,450,330,110,22);});
 tx(s,'Split into left/right halves; separate 1024² analysis copies. Sparse output remains fragmented.',50,440,465,130,25);
 foot(s,'These are failed-camera diagnostics; neither is an accepted production reconstruction.');
 });}
for(const name of [...new Set(D.generated.map(r=>r.name))]){const rows=D.generated.filter(r=>r.name===name);const cfg=rows[0].metrics.profile;
 spec(name.replaceAll('_',' ')+': both trials','Generated stereo · complete parameter sweep',
 'Full saved OBJ geometry for both trials. No smoothing, outlier deletion, face decimation or geometric cropping. All panels retain independent full extents and arbitrary baseline units. Held-out disparity residual is computed only where held-out feature locations also survive dense acceptance; it is not a whole-surface 3D error. The row-adjusted family also changes the image alignment. Exact profile parameters are in the source metrics.',rows.flatMap(r=>[r.obj,r.metrics_source]),s=>{
 rows.forEach((r,i)=>{const x=50+610*i,m=r.metrics;tx(s,r.trial,x,151,570,35,26,C.teal,true);im(s,r.render,x,200,570,258,`${r.trial} ${name} full geometry`);
 tx(s,`${P(m.whole_image_fraction)} pixels · ${N(r.triangles)} triangles\n${N(m.mesh_topology.components)} components; largest ${P(m.mesh_topology.largest_component_face_fraction)}\nHeld-out disparity: ${F(m.heldout_disparity_error_px?.median)} px median (${m.heldout_features_accepted}/${m.heldout_feature_count} features)`,x,464,580,115,21);});
 foot(s,`Block ${cfg.block_size}² · uniqueness ${cfg.uniqueness_ratio} · internal LR ${cfg.internal_lr_px} px · external LR ${cfg.external_lr_px??'off'} · depth jump ${cfg.relative_depth_jump>1e6?'effectively off':F(100*cfg.relative_depth_jump,0)+'%'}`);
 });}
spec('Trial 2: where relaxed matching accepts pixels','Generated stereo · matching evidence',
 'Trial 2 acceptance masks above, disparity below, for all seven sweep profiles. Percentages divide by the entire image. False sky correspondences and broad disparity plateaus should be inspected with the full geometry. Trial 2 row adjustment has only seven held-out feature matches, so its low residual on a few accepted matches provides limited evidence.',
 ['output/uber_relaxed/stereo_trial_2/comparison.png','output/uber_relaxed/REPORT.md'],s=>{im(s,'output/uber_relaxed/stereo_trial_2/comparison.png',35,168,1210,400,'All seven masks and disparity maps for trial 2');foot(s,'Trial 2 no-checks accepts 85.2% of pixels; this is numerical density, not valid terrain coverage.');});

function val(r){const m=r.metrics,v=m.validation??m.spatial_holdout,h=m.holdout;
 if(v)return {count:v.tested_added_cells??v.scored_cells,total:v.measurable_gap_cells??v.eligible_cells,video:v.video_abs_height_error_m?.rmse,idw:v.matched_idw_abs_height_error_m?.rmse,linear:v.matched_linear_abs_height_error_m?.rmse,reference:v.holdout??`depth holes r=${v.radius_m} m`};
 if(h)return {count:h.consensus_video_m?.count,total:h.eligible_gap_cells,video:h.consensus_video_m?.rmse,idw:h.same_cell_idw_m?.rmse,linear:h.same_cell_linear_m?.rmse,reference:h.name};return null;
}
function interpretation(r){const v=val(r);
 if(!v)return 'Conditional model: no independent withheld-terrain error is available for this run.';
 if(v.count<10)return `Only ${v.count} reference cells scored; insufficient support for an accuracy conclusion.`;
 return `Video RMSE ${CM(v.video)} vs matched IDW ${CM(v.idw)}${v.linear!=null?' / linear '+CM(v.linear):''}; no demonstrated gain.`;
}
for(const r of D.video){const m=r.metrics,v=val(r),integrated=r.integrated;
 const title=r.name==='baseline_unconditioned_eval'?'Estimated-pose control: 044 → 047':r.name.startsWith('disk')?`Depth-hole control: ${F(m.spatial_holdout.radius_m*2,1)} m diameter`:r.name.startsWith('mid036')?`4 m / 10° command prior: ${integrated?'integrated model':'seed '+m.seed}`:r.name==='short_7'?'Short-path sensitivity: 3.4 m / 5°':r.name==='long_7'?'Long-path sensitivity: 4.6 m / 15°':`${m.endpoints.map(x=>x.slice(4)).join(' → ')}: ${integrated?'three-seed consensus':'seed '+m.seed}, withhold ${v?.reference?.slice(-3)??'—'}`;
 spec(title,'Video terrain · individual result sheet',
 `Actual saved terrain for ${r.name}. ${m.endpoints.join(' to ')}. ${integrated?'Three procedural seeds integrated; remaining holes receive linear interpolation.':'Procedural imagery reconstructed from pixels; strict endpoint stereo remains in the candidate surface.'} ${interpretation(r)}\nAll geometry is shown at true aspect and complete extent; provenance is assigned conservatively per face using its most inferred vertex. Colors distinguish evidence origin, not confidence estimates. Grid is 5 cm. Top area is projected triangle area. Small accepted-reference subsets are not representative of unobserved terrain. Exact raw metrics follow in the companion report.`,
 [r.obj,r.metrics_source,...(r.video?[r.video.strip]:[])],s=>{
 tx(s,`${r.name}   |   ${m.endpoints.join(' → ')}   |   ${r.name==='baseline_unconditioned_eval'?'PnP frame poses':integrated?'three seeds / supplied poses':'supplied render poses'}`,50,145,1180,34,22,C.teal,true);
 im(s,r.render,40,202,755,278,`Actual saved OBJ for ${r.name}`);
 im(s,r.plan,845,198,380,238,`Source labels in XY for ${r.name}`);
 if(r.video){im(s,r.video.strip,52,489,710,114,'Actual decoded frames 0, 16 and 32');tx(s,'Decoded frames 0 / 16 / 32',55,600,690,25,17,C.muted);}
 else tx(s,integrated?'Completed upper surface; artificial closure shown separately.':'480² control; 24 unconditioned frames used from a 33-frame clip.',55,535,710,65,23,C.muted);
 const counts=integrated?`Strict ${N(m.cell_counts['1'])} · relaxed ${N(m.cell_counts['2'])}\nVideo ${N(m.cell_counts['3'])} · linear ${N(m.cell_counts['4'])}`:`${m.frames??33} frames · ${N(m.video_tracks)} tracks\n${N(m.new_video_cells)} new video cells (${F(m.new_cell_area_m2)} m²)`;
 tx(s,`${counts}\n${N(r.triangles)} faces · ${F(m.top_area_m2??m.mesh?.projected_surface_area_m2)} m² top\n${v?`Scored ${N(v.count)} / ${N(v.total)} reference cells`:'No independent withheld-height score'}`,815,445,415,145,22);
 legend(s,622);tx(s,interpretation(r),50,661,1180,25,17,C.orange,true);
 });
}
for(let start=0;start<D.video.length;start+=8){const rows=D.video.slice(start,start+8);spec(`Video result ledger ${start===0?'1 / 2':'2 / 2'}`,'Exact saved result comparisons',
 'Metrics transcribed directly from each run JSON. RMSE values in centimetres; each row uses its own scored cells. Rows differ in endpoint pair, support, pose protocol, resolution, spatial holdout and seed, so this table cannot rank video-generation methods. Dashes mean no corresponding independent metric, not zero error. All are procedural results.',rows.map(r=>r.metrics_source),s=>{
 tb(s,[['Run','Scored / eligible','Video RMSE','IDW RMSE','Linear RMSE'],...rows.map(r=>{const v=val(r);return [r.name,v?`${N(v.count)} / ${N(v.total)}`:'not evaluated',CM(v?.video),CM(v?.idw),CM(v?.linear)];})],50,160,1180,430,[1.6,1.2,1,1,1],21);
 foot(s,'A passing tolerance or low reprojection error is not evidence of improvement over interpolation.');
 });}
spec('Invalid temporal controls still export candidate meshes','Failure cases · actual exported geometry',
 'These are real saved evaluator outputs for a frozen image repeated 33 times and a linear endpoint crossfade. Most visible mesh geometry comes from endpoint stereo; its presence must not be mistaken for video reconstruction success. Frozen has four added dense cells and zero sparse points; crossfade adds 49 cells. Only zero and one reference cells, respectively, are scored. Require negative-control rejection and explicit per-cell parallax before promoting candidate surfaces.',D.negative.flatMap(r=>[r.obj,r.metrics_source]),s=>{
 D.negative.forEach((r,i)=>{const x=50+610*i;tx(s,r.name.replaceAll('_',' '),x,155,580,42,27,C.teal,true);im(s,r.render,x,218,575,280,'Actual negative-control candidate surface '+r.name);tx(s,`${N(r.metrics.video_tracks)} sparse points · ${N(r.metrics.new_video_cells)} added cells\n${r.name.startsWith('frozen')?'0':'1'} / 561 withheld reference cells scored`,x,512,580,85,24);});legend(s,584);foot(s,'The large blue surface is retained real stereo; it does not show successful generation.');
 });
spec('Actual closed video-terrain models','Geometry export · topology is not accuracy',
 'Actual closed OBJ exports, showing sides and underside as part of each model. These are Matplotlib mesh renders, not Blender import validation. Closed meshes preserve the existing top and append an artificial base and vertical walls. Both have one connected component, consistent outward winding, and zero boundary or nonmanifold edges/vertices according to saved closure checks. Their upper surfaces still mix observed and inferred cells.',D.closed_video.map(r=>r.obj),s=>{
 D.closed_video.forEach((r,i)=>{const x=50+610*i,m=D.video.find(v=>v.name===r.name).metrics;tx(s,r.name,x,158,580,35,26,C.teal,true);im(s,r.render,x,205,570,280,'Actual closed OBJ including artificial walls and base');tx(s,`${F(m.top_area_m2)} m² top surface\n${N(m.closure.obj.vertices)} vertices · ${N(m.closure.obj.triangles)} triangles\n0 open edges · 1 connected component`,x,501,580,95,23);});foot(s,'Blender import, collision behavior and traversability are still unverified in the saved evidence.');
 });
spec('What the results justify doing next','Research decisions and remaining evidence',
 'This is a work plan, not a record of completed experiments. Keep the professor’s request for more than ten methods as an explicit unfulfilled benchmark target. The colleague will return a ZIP from his GPU. No such learned-result ZIP has been evaluated at this snapshot. Fix acceptance controls and establish comparable evaluation before choosing a reconstruction model. Use actual mesh import screenshots and planner diagnostics for the simulation comparison. Image segmentation has proposals but no validated rock/crater prior yet.',
 ['output/collaboration_review/2026-11-09/COMPARISON_FINDINGS.md','output/collaboration_review/negative_controls_2026-11-09/FINDINGS.md'],s=>{
 tb(s,[['Priority','Deliverable','Evidence needed to proceed'],['1 · validity','Reject frozen/crossfade controls; retain frame indices','Per-cell parallax; deduplicated seed votes; fixed masks'],['2 · first learned return','Evaluate colleague’s ZIP with the same contract','Inputs, model/version, prompt, seed, frames, hashes'],['3 · broad benchmark','Run >10 distinct open/closed method families','Matched endpoints and resolution; failure + cost + quality'],['4 · sim → real test','Import actual completed OBJ into Blender / planner','Units/up verified; slopes, artifacts and edges inspected'],['5 · unknown terrain priors','Review segmentation and test controlled priors','Rock/crater labels; withheld validation; provenance']],50,161,1180,415,[.75,1.4,1.8],23);
 foot(s,'Select a method only after it improves the completed fixed reference region over interpolation.');
 });

export async function append(p,start=0,count=8){
 const expected=32+start;if(p.slides.items.length!==expected)throw new Error(`Expected ${expected} slides, found ${p.slides.items.length}`);
 for(const q of specs.slice(start,start+count)){
 const s=p.slides.add();s.setViewportSize(1280,720);s.background.fill=C.bg;
 tx(s,q.section.toUpperCase(),50,23,1170,25,15,C.teal,true);tx(s,q.title,50,59,1180,89,q.title.length>61?33:37,C.ink,true);
 tx(s,'Chandrayaan-3 terrain reconstruction  |  Detailed evidence: 10 Nov 2026',50,693,1110,20,12,C.muted);tx(s,String(p.slides.items.length),1190,689,45,25,15,C.muted);
 s.speakerNotes.text='Detailed evidence atlas. Use selectively for discussion; outside the 15-minute route.\n\n'+q.notes+'\n\nSources:\n'+q.sources.map(absolute).join('\n');q.draw(s);
 }
 return {slides:p.slides.items.length,added:Math.min(count,specs.length-start),totalExpansion:specs.length};
}
export async function writeReport(){
 const records=specs.map((s,i)=>({number:33+i,title:s.title,section:s.section,notes:s.notes,sources:s.sources.map(absolute)}));
 await fs.writeFile(OUT+'/expanded_slide_evidence.json',JSON.stringify(records,null,2));
 await fs.writeFile(OUT+'/DETAILED_METHODS_AND_RESULTS.md','# Reconstruction methods and complete result atlas\n\nEvidence snapshot: 10 November 2026. Slides 1–13 remain the 15-minute presentation; the appended atlas supplies the full review record. All meshes are renders of actual saved OBJ outputs. No new reconstruction or learned model is claimed.\n\n'+records.map(r=>`## Slide ${r.number}: ${r.title}\n\n${r.notes}\n\nSources:\n${r.sources.map(v=>'- '+v).join('\n')}\n`).join('\n')+'\n## Machine-readable full results\n\nSee atlas_manifest.json for exact per-run metrics, model SHA256 hashes, extents, input paths and render paths. See local_observation_results.csv for all 50 observations.\n');
 return {totalSlides:32+specs.length,expandedSlides:specs.length};
}

export function finish(p){
 for(let i=0;i<D.video.length;i++){
   const r=D.video[i],s=p.slides.getItem(73+i);
   const a=s.shapes.items.find(v=>v.position.top===145);
   a.text=`${r.name}   |   ${r.metrics.endpoints.join(' → ')}   |   ${r.name==='baseline_unconditioned_eval'?'PnP frame poses':r.integrated?'three seeds / supplied poses':'supplied render poses'}`;
 }
 for(const index of [67,68]){
   const a=p.slides.getItem(index).shapes.items.at(-1);
   a.text=String(index===67?'Block 11²':'Block 21²')+' · uniqueness 0 · internal LR 512 px · external LR off · depth jump effectively off';
 }
 const s=p.slides.getItem(73),a=s.shapes.items.find(v=>v.position.top===535);
 if(a){
   a.text='Decoded frames 0 / 16 / 32 · 24 unconditioned frames used';
   a.position={left:55,top:600,width:690,height:25};
   a.text.style={typeface:'Arial',fontSize:17,color:C.muted};
   im(s,OUT+'/figures/baseline_unconditioned_eval_frames.png',52,489,710,114,'Actual decoded 480-pixel control frames 0, 16 and 32');
 }
 return {slides:p.slides.items.length};
}
