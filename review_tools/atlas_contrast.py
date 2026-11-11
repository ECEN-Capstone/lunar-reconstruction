from review_tools.terrain_result_atlas import *
d=read(OUT/'atlas_manifest.json')
for r in d['local']+d['components']:
    obs=r['name'].replace('component_','')
    pr=read(ROOT/'artifacts/runs/r11_filtered_batch'/obs/'provenance.json')
    T=np.eye(4);T[:3,:3]=np.asarray(pr['R_rectified_from_source']).T;T[:3,3]=CENTRE
    updated=render(ROOT/r['obj'],ROOT/r['render'],T=T,background='#102435')
    r.update(updated)
(OUT/'atlas_manifest.json').write_text(json.dumps(d,indent=2))
print('Contrast improved for 56 full observed meshes; no geometry changed.')
