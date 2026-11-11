from review_tools.terrain_result_atlas import *

d=read(OUT/'atlas_manifest.json')
d['generated_diagnostics']=[]
for trial in ['stereo_trial_1','stereo_trial_2']:
    for mode in ['strict','relaxed']:
        folder=ROOT/'output/generated_stereo_trial'/trial/('diagnostic_'+mode)
        T=np.eye(4);T[:3,:3]=np.array([[1,0,0],[0,0,1],[0,-1,0]])*1000
        r=render(folder/'INVALID_GEOMETRY_mesh_baseline_units.obj',ASSETS/f'{trial}_{mode}.png',T=T,units='baseline=1')
        r.update(trial=trial,name=mode,metrics=read(folder/'metrics.json'),metrics_source=str((folder/'metrics.json').relative_to(ROOT)),diagnostic=str((folder/'dense_diagnostic.png').relative_to(ROOT)))
        d['generated_diagnostics'].append(r)
d['negative']=[]
for name in ['frozen_first_endpoint','linear_endpoint_crossfade']:
    folder=ROOT/'output/collaboration_review/negative_controls_2026-11-09'/name/'evaluation'
    s=np.load(folder/'surfaces.npz');xy=np.stack(np.meshgrid(s['x'],s['y'],indexing='ij'),-1)
    r=render(folder/'candidate_stereo_plus_video_m.obj',ASSETS/f'{name}_model.png',labels=s['labels'],xy=xy)
    r.update(name=name,metrics=read(folder/'metrics.json'),metrics_source=str((folder/'metrics.json').relative_to(ROOT)))
    d['negative'].append(r)
d['closed_video']=[]
for name in ['holdout046_model','mid036_model']:
    r=render(ROOT/'output/chronological_video'/name/'closed/terrain_closed_m.obj',ASSETS/f'{name}_closed.png')
    r.update(name=name);d['closed_video'].append(r)
d['render_count']=len(list(ASSETS.glob('*.png')))
(OUT/'atlas_manifest.json').write_text(json.dumps(d,indent=2))
print('Added',len(d['generated_diagnostics'])+len(d['negative'])+len(d['closed_video']),'actual OBJ renders')
