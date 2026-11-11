"""Portable, source-linked scientific result gallery and presentation evidence."""
from pathlib import Path
import json, html, hashlib, shutil, zipfile
from PIL import Image, ImageOps, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/detailed_progress_2026-11-10'
EXPORTS=Path('C:/Users/rhunt/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Roaming/Codex/web/Codex/artifact-sessions/exports/latest/eb383c220925d7582755e9116ead7eb07efba0b16bf76971c77fa6c7688e4149')
E=html.escape
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def relasset(src):return 'figures/'+Path(src).name
def card(r,title=None):
    title=title or r.get('name',r.get('trial','mesh'))
    src=relasset(r['render']);m=r.get('metrics',{})
    details=f"{r['vertices']:,} vertices · {r['triangles']:,} triangles"
    extent=' × '.join(f'{v:.3f}' for v in r['extent'])
    top=f'<article><h3>{E(title)}</h3><a href="{src}" target="_blank"><img src="{src}" loading="lazy" alt="Actual saved OBJ: {E(title)}"></a><p>{details}<br>Extent X × Y × Z: {extent} {E(r["units"])}</p>'
    if 'input' in r:top+=f'<p>Actual rectified left input</p><img class="input" src="figures/{r["name"]}_input.png" alt="Actual input">'
    if 'plan' in r:top+=f'<p>Strict = blue; relaxed = green; video = orange; linear = gray.</p><img src="{relasset(r["plan"])}" alt="Terrain source provenance">'
    if r.get('gallery_movie'):top+=f'<video controls preload="none" src="{r["gallery_movie"]}"></video>'
    top+=f'<details><summary>Exact metrics and source</summary><pre>{E(json.dumps(m,indent=2))}</pre><p>Saved OBJ: {E(r["obj"])}<br>SHA256: {r["obj_sha256"]}</p></details></article>'
    return top

def main():
    d=json.loads((OUT/'atlas_manifest.json').read_text())
    (OUT/'videos').mkdir(exist_ok=True)
    for r in d['video']+d['negative']:
        movie=None
        if r in d['video'] and r.get('video'):
            movie=ROOT/r['video'].get('movie',str(Path(r['metrics_source']).parent/'transition.mp4'))
        elif r in d['negative']:movie=ROOT/Path(r['metrics_source']).parent.parent/'negative_control.mp4'
        if movie and movie.exists():
            dst=OUT/'videos'/(r['name']+'.mp4');shutil.copy2(movie,dst);r['gallery_movie']='videos/'+dst.name
    sections=[('local','All 50 accepted local reconstructions',d['local']),('registered','All six registered groups',d['components']),('completion','All nine completion variants',[dict(v,name=r['name']+' / '+mode,metrics=r['metrics']['meshes'][mode]) for r in d['completion'] for mode,v in r['renders'].items()]),('generated','Both generated stereo trials: 18 settings',[dict(r,name=r['trial']+' / '+r['name']) for r in d['generated_diagnostics']+d['generated']]),('video','All 15 saved video terrain results',d['video']),('negative','Invalid temporal controls',d['negative']),('closed','Actual closed video terrain',d['closed_video'])]
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lunar terrain — complete results atlas</title><style>
    body{font:16px/1.5 system-ui,sans-serif;background:#f7f9fc;color:#183149;margin:0;padding:28px}header{max-width:1120px}h1{font-size:36px;line-height:1.1}h2{margin-top:48px;border-bottom:2px solid #087e8b;padding-bottom:12px}h3{font-size:18px}nav{display:flex;gap:18px;flex-wrap:wrap;margin:26px 0}a{color:#087e8b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}article{background:white;border:1px solid #ccd7e0;padding:18px;min-width:0}img{display:block;width:100%;height:225px;object-fit:contain;background:#fff}.input{height:170px}video{width:100%;margin:10px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}details{overflow-wrap:anywhere}summary{cursor:pointer;color:#087e8b}.notice{border-left:5px solid #b7472a;padding:12px 18px;background:#fff}footer{margin:48px 0}button{font:inherit;padding:8px 14px} @media print{body{padding:0}.grid{grid-template-columns:repeat(2,1fr)}article{break-inside:avoid}video{display:none}}
    </style><header><h1>Lunar reconstruction: complete result atlas</h1><p>Evidence snapshot: 10 November 2026. These are renders of actual saved OBJ files, not illustrative generated terrain images. Click a model to open its full-size figure. Open each metrics panel for exact values and source hashes.</p><p class="notice">Local and generated meshes use independent full extents and relative-height colors; apparent size/color cannot rank accuracy. Video surfaces use source-provenance colors. No geometry was smoothed, clipped, filled or decimated for these renders. Nominal rover up is unverified. Generated stereo has arbitrary scale. All video results here are procedural; no learned-generator output has been evaluated.</p><p><a href="DETAILED_METHODS_AND_RESULTS.md">Detailed slide notes and methodology</a> · <a href="local_observation_results.csv">50-observation table</a> · <a href="atlas_manifest.json">Full numeric evidence and hashes</a></p></header>'''
    page+='<nav>'+''.join(f'<a href="#{key}">{E(title)}</a>' for key,title,_ in sections)+'</nav>'
    for key,title,rows in sections:page+=f'<section id="{key}"><h2>{E(title)}</h2><div class="grid">'+''.join(card(r) for r in rows)+'</div></section>'
    page+='<footer>Closed topology is not an accuracy certificate. Withheld registered stereo is a noisy reference, not survey ground truth. Read the slide notes for each experiment’s split and limitations.</footer></html>'
    (OUT/'RESULTS_GALLERY.html').write_text(page,encoding='utf8')
    # A scientific contact sheet of actual geometry, available as a zoomable poster.
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',30)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
    poster=Image.new('RGB',(2400,10*340+125),'#f7f9fc');draw=ImageDraw.Draw(poster)
    draw.text((24,22),'ALL 50 ACCEPTED OBSERVED MESHES — actual saved geometry',font=font,fill='#183149')
    draw.text((24,70),'Independent extents / relative-height colors; open surfaces; no hole filling or vertical exaggeration.',font=small,fill='#52687b')
    for i,r in enumerate(d['local']):
        x=(i%5)*480;y=125+(i//5)*340
        draw.text((x+14,y+6),r['name'],font=font,fill='#087e8b')
        im=Image.open(ROOT/r['render']).convert('RGB');im=ImageOps.contain(im,(452,235));poster.paste(im,(x+14+(452-im.width)//2,y+48+(235-im.height)//2))
        draw.text((x+14,y+292),f"{r['metrics']['valid_fraction']*100:.1f}% pixels / {r['triangles']:,} triangles",font=small,fill='#183149')
    poster.save(OUT/'all_50_observed_meshes_poster.png')
    readme='''# Complete reconstruction and video evidence — 10 November 2026

Open RESULTS_GALLERY.html to browse every model render and play the saved procedural video clips. No server or internet connection is required. Click each figure for full size; expand its metrics for the exact source records.

The editable presentation is the live Codex artifact artifact_DVCU5iyih2QXVXO5k70flhvAj9qwuYuR.

## Presentation navigation

- Slides 1–13: 15-minute result-first presentation route.
- Slides 14–32: initial technical appendix and evaluation findings.
- Slide 33: evidence inventory and reading conventions.
- Slides 34–45: exact pipeline methodology, thresholds, equations, assumptions and evaluation protocol.
- Slides 46–58: all 50 accepted local observed meshes with input images and counts.
- Slides 59–60: all six registered groups with distinct-view support counts.
- Slides 61–63: all nine completion variants across observations 003, 029 and 034.
- Slides 64–73: strict/relaxed diagnostics and both generated stereo trials under all seven sweep settings.
- Slides 74–88: every saved chronological-video terrain run, including source labels and actual decoded frames.
- Slides 89–90: exact numeric result ledgers.
- Slides 91–92: actual invalid-control candidate meshes and closed terrain models.
- Slide 93: decisions, blockers and next evidence needed.

## Interpretation

102 OBJ products are rendered in the expanded atlas/gallery (including variants and controls, not 102 independent observations). Individual views retain full geometry and true aspect; units and orientation remain subject to the stated calibration conventions. Mesh panel colors are relative height unless the provenance legend is shown. The largest original completed real-terrain result and full-traverse overlay remain visible in the presentation and original evidence package.

No learned-video result has been received; the 12-family slate is a plan. Current procedural additions do not improve the fixed-region interpolation baseline. Closed surfaces are not Blender/Gazebo or traversability validation. See the method notes for selection bias, uncertain poses, raw-before-envelope failures, and negative-control gaps.

The gallery embeds actual rendered geometry and clips. OBJ files themselves remain in the repository at the paths recorded in atlas_manifest.json; this package includes model hashes and metrics. Historical reports are preserved as evidence, with later limitations explained in the current notes.
'''
    (OUT/'README.md').write_text(readme,encoding='utf8')
    # Preserve source metrics, current implementation/config and earlier evidence.
    evidence=set()
    for _,_,rows in sections:
        for r in rows:
            if r.get('metrics_source'):evidence.add(r['metrics_source'])
    evidence.update(['reconstruction/geometry.py','reconstruction/stereo.py','reconstruction/register.py','reconstruction/video_bridge.py','reconstruction/video_pose_check.py','reconstruction/video_triangulate.py','reconstruction/video_integrate.py','reconstruction/evaluate_video.py','configs/filtering.json','configs/registration.json','configs/completion.json','configs/uber_relaxed.json'])
    for r in d['completion']:evidence.add(r['metrics_source'])
    for rel in evidence:
        src=ROOT/rel;dst=OUT/'source_evidence'/Path(rel);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    previews=OUT/'slide_previews';previews.mkdir(exist_ok=True)
    for i in range(1,94):shutil.copy2(EXPORTS/f'slide-{i}.png',previews/f'slide_{i:02}.png')
    # Reuse earlier package to retain its full-traverse map and original figures.
    with zipfile.ZipFile(ROOT/'output/progress_presentation/reconstruction_update_figures_and_evidence.zip') as z:
        for name in z.namelist():
            if name.startswith(('figures/','evidence/','all_observations_overlay/')) or name in ['slide_evidence.json','DETAILED_REPORT_AND_SPEAKER_NOTES.md','figure_index.json']:
                dst=OUT/'original_evidence'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(z.read(name))
    files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='SHA256SUMS.json']
    (OUT/'SHA256SUMS.json').write_text(json.dumps({str(p.relative_to(OUT)).replace('\\','/'):sha(p) for p in files},indent=2))
    dst=OUT/'complete_reconstruction_results_and_figures.zip'
    with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[OUT/'SHA256SUMS.json']:z.write(p,str(p.relative_to(OUT)))
    with zipfile.ZipFile(dst) as z:assert z.testzip() is None
    print(json.dumps({'zip':str(dst),'size_mb':round(dst.stat().st_size/1024**2,1),'files':len(files)+1,'mesh_products':sum(len(rows) for _,_,rows in sections),'video_clips':len(list((OUT/'videos').glob('*.mp4'))),'slides':93,'sha256':sha(dst)},indent=2))

if __name__=='__main__':main()
