from pathlib import Path
import re
import json
import pymupdf as fitz
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r'C:\Users\rhunt\Downloads\Rylee Hunt Individual Technical Report.pdf')
OUT = ROOT / 'output/pdf/Rylee Hunt Individual Technical Report - IEEE Citations.pdf'
TEMP = ROOT / 'tmp/pdfs/current_report'
OUT.parent.mkdir(parents=True, exist_ok=True)
FONT = 'C:/Windows/Fonts/arial.ttf'
font = fitz.Font(fontfile=FONT)
doc = fitz.open(SOURCE)
original_text = [p.get_text(sort=True) for p in doc]
changes = []

def edit_lines(page_index, start, end, old, new, limit):
    page = doc[page_index]
    lines = [l for b in page.get_text('dict')['blocks'] if b['type'] == 0 for l in b['lines']]
    texts = [''.join(s['text'] for s in l['spans']).strip() for l in lines]
    first = next(i for i,t in enumerate(texts) if t.startswith(start))
    last = next(i for i in range(first,len(texts)) if texts[i].endswith(end))
    selected = lines[first:last+1]
    text = ' '.join(texts[first:last+1])
    assert text.count(old) == 1
    revised = text.replace(old, new)
    wrapped = []
    line = ''
    for word in revised.split():
        trial = (line+' '+word).strip()
        if font.text_length(trial,fontsize=11) > 470:
            wrapped.append(line)
            line=word
        else:
            line=trial
    if line: wrapped.append(line)
    baseline=selected[0]['spans'][0]['origin'][1]
    assert baseline+(len(wrapped)-1)*14.546265+3 < limit, (revised,wrapped,limit)
    for l in selected:
        r=fitz.Rect(l['bbox'])
        page.add_redact_annot(fitz.Rect(71,r.y0,544,r.y1),fill=(1,1,1))
    page.apply_redactions(images=0,graphics=0)
    page.insert_font(fontname='CitationArial',fontfile=FONT)
    for i,t in enumerate(wrapped):
        page.insert_text((72,baseline+i*14.546265),t,fontname='CitationArial',fontsize=11)
    changes.append({'page':page_index+1,'old':text,'new':revised,'original_lines':len(selected),'new_lines':len(wrapped)})

edit_lines(1,'For the first pipeline,','rocks and','SAM2 masks','SAM2 [1] masks',622)
edit_lines(3,'Once the team decided','stereo','Chandrayaan-3 stereo','Chandrayaan-3 [2] stereo',369)
edit_lines(3,'examined. These models','vectors.','projection vectors.','projection vectors [2].',499)
edit_lines(4,'Camera projection','using','same image row.','same image row [3].',277)
edit_lines(4,'where Z is depth','disparity.','disparity.','disparity [4].',337)
edit_lines(4,'Dense matching uses','acquisition.','StereoSGBM implementation.','StereoSGBM implementation [5].',490)

refs = [
    'N. Ravi <i>et al.</i>, “SAM 2: Segment anything in images and videos,” arXiv:2408.00714, 2024, doi: <link href="https://doi.org/10.48550/arXiv.2408.00714">10.48550/arXiv.2408.00714</link>.',
    'Space Applications Centre, Indian Space Research Organisation, <i>Chandrayaan-3 Navigational Camera (NavCam) PDS4 Data Products and Archive Software Interface Specification</i>, ver. 2.0. Ahmedabad, India, Jul. 3, 2024, sec. 6.4.2 and Appendix H.',
    'OpenCV, “Camera calibration and 3D reconstruction,” <i>OpenCV 4.13.0 Documentation</i>, “stereoRectify.” Accessed: Oct. 1, 2026. [Online]. Available: <link href="https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html">https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html</link>',
    'OpenCV, “Depth map from stereo images,” <i>OpenCV 4.13.0 Documentation</i>. Accessed: Oct. 1, 2026. [Online]. Available: <link href="https://docs.opencv.org/4.13.0/dd/d53/tutorial_py_depthmap.html">https://docs.opencv.org/4.13.0/dd/d53/tutorial_py_depthmap.html</link>',
    'OpenCV, “cv::StereoSGBM class reference,” <i>OpenCV 4.13.0 Documentation</i>. Accessed: Oct. 1, 2026. [Online]. Available: <link href="https://docs.opencv.org/4.13.0/d2/d85/classcv_1_1StereoSGBM.html">https://docs.opencv.org/4.13.0/d2/d85/classcv_1_1StereoSGBM.html</link>',
]
pdfmetrics.registerFont(TTFont('Arial','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialItalic','C:/Windows/Fonts/ariali.ttf'))
pdfmetrics.registerFontFamily('Arial',normal='Arial',italic='ArialItalic',bold='Arial',boldItalic='ArialItalic')
heading=ParagraphStyle('Heading',fontName='Arial',fontSize=20,leading=26,spaceAfter=16)
style=ParagraphStyle('Reference',fontName='Arial',fontSize=11,leading=14.55,leftIndent=20,firstLineIndent=-20,spaceAfter=16,splitLongWords=True)
refs_pdf=TEMP/'references_page.pdf'
SimpleDocTemplate(str(refs_pdf),pagesize=(612,792),leftMargin=72,rightMargin=72,topMargin=72,bottomMargin=72).build([Paragraph('References',heading)]+[Paragraph(f'[{i}] {r}',style) for i,r in enumerate(refs,1)])
with fitz.open(refs_pdf) as r:
    assert len(r)==1
    doc.insert_pdf(r)
doc.save(OUT,garbage=4,deflate=True)
doc.close()

# Text changes must be only citation insertions, regardless of line wrapping.
norm=lambda s: re.sub(r'\s+','',re.sub(r'\s*\[[1-5]\]','',s.replace('\u00ad','-')))
with fitz.open(OUT) as final:
    for i,old in enumerate(original_text):
        assert norm(old)==norm(final[i].get_text(sort=True)), f'Unexpected text change page {i+1}'
    body=' '.join(p.get_text() for p in list(final)[:10])
    assert set(re.findall(r'\[([1-5])\]',body))==set('12345')
    for i,page in enumerate(final):
        page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(TEMP/f'final-{i+1}.png')

md=['# Citation placements for the current PDF','', 'Source: Rylee Hunt Individual Technical Report.pdf (10 pages). The cited copy preserves all body wording and figures and appends a References page.','']
for c in changes:
    md.extend([f"- Page {c['page']}: {c['new']}",''])
md+=['## References','']
for i,r in enumerate(refs,1):
    plain=re.sub(r'<link href="[^"]+">(.*?)</link>',r'\1',r)
    plain=plain.replace('<i>','*').replace('</i>','*')
    md.extend([f'[{i}] {plain}',''])
md+=['## Separate factual correction','', 'Page 8 retains the source wording “2.18 × 10^-11 mm” because this pass is limited to citations. The saved geometry_tests.json records calibration units, not verified millimeters. No external reference validates that unit conversion.','', 'Reference [2] is the exact local version 2.0 mission document already inspected in the reconstruction repository. Its date comes from its own change history. No DOI or direct public PDF URL was verified; none is invented. Official retrieval instructions are at https://pradan.issdc.gov.in/ch3/faq.xhtml (NavCam section).','']
(ROOT/'CURRENT_REPORT_CITATIONS.md').write_text('\n'.join(md),encoding='utf-8')
(TEMP/'citation_changes.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
print(json.dumps({'output':str(OUT),'pages':11,'body_text_preserved':True,'citations':5,'changes':len(changes)}))
