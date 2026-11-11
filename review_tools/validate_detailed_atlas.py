from pathlib import Path
from html.parser import HTMLParser
import json, hashlib, zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/detailed_progress_2026-11-10'
EXPORTS=ROOT/'output/progress_presentation/slide_layouts'
class Links(HTMLParser):
    def __init__(self):super().__init__();self.refs=[]
    def handle_starttag(self,tag,attrs):
        self.refs.extend(v for k,v in attrs if k in ('href','src'))
p=Links();p.feed((OUT/'RESULTS_GALLERY.html').read_text(encoding='utf8'))
missing=[r for r in p.refs if not r.startswith('#') and not (OUT/r).is_file()]
assert not missing,missing
bad=[];counts={}
for i in range(1,94):
    d=json.loads((EXPORTS/f'slide-{i}.layout.json').read_text(encoding='utf8'))
    assert (OUT/'slide_previews'/f'slide_{i:02}.png').is_file()
    for e in d['elements']:
        counts[e['kind']]=counts.get(e['kind'],0)+1
        a=e['position']
        if a['left']<0 or a['top']<0 or a['left']+a['width']>1280.1 or a['top']+a['height']>720.1:bad.append((i,e['id'],a))
assert not bad,bad
with zipfile.ZipFile(OUT/'complete_reconstruction_results_and_figures.zip') as z:
    manifest=json.loads(z.read('SHA256SUMS.json'))
    assert all(hashlib.sha256(z.read(name)).hexdigest()==value for name,value in manifest.items())
print(json.dumps({'slides_checked':93,'gallery_links_checked':len(p.refs),'missing_assets':missing,'off_canvas':bad,'native_element_counts':counts,'packaged_hashes_verified':len(manifest)},indent=2))
