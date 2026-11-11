from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen import canvas
import re

build=Path(__file__).resolve().parent
out=build.parent
root=out.parent.parent
name='Pragyan_terrain_reconstruction_methods'
atlas=root/'output/detailed_progress_2026-11-10/figures'
obs=root/'artifacts/runs/r08_quality_batch/obs_034'
fonts=Path('C:/Windows/Fonts')
def panel(tag, entries, sizes):
    width,height=sizes
    buf=Image.new('RGB',(width,height),'white')
    draw=ImageDraw.Draw(buf)
    font=ImageFont.truetype(str(fonts/'arialbd.ttf'),min(37,int(width*.021)))
    half=width//len(entries)
    for i,(src,label) in enumerate(entries):
        im=Image.open(src).convert('RGB')
        im.thumbnail((half-22,height-64),Image.Resampling.LANCZOS)
        buf.paste(im,(i*half+(half-im.width)//2,54+(height-58-im.height)//2))
        draw.text((i*half+half//2,18),label,font=font,fill='#213c4e',anchor='mt')
    dest=build/(tag+'.png')
    buf.save(dest)
    return dest
assets={'@stereo':panel('034_stereo',[(obs/'rectified_left.png','Left camera'),(obs/'rectified_right.png','Right camera')],(2000,1040)),
'@generated':panel('generated_comparison',[(atlas/'stereo_trial_1_uber_relaxed_no_checks.png','No checks'),(atlas/'stereo_trial_1_uber_relaxed_row_adjusted.png','Row adjusted')],(1150,555)),
'@bridge':panel('bridge_sources',[(atlas/'mid036_model_provenance.png','Source of each height'),(atlas/'mid036_model_closed.png','Closed model')],(1600,660))}
parts=[(build/x).read_text(encoding='utf-8-sig') for x in ['part1.txt','part2.txt']]
pages=('\n---\n'.join(p.strip() for p in parts)).split('\n---\n')
def records(page):
    lines=page.strip().splitlines()
    i=0
    while i<len(lines):
        s=lines[i].strip(); i+=1
        if not s:continue
        if s.startswith('| '):
            rows=[[x.strip() for x in s[2:].split('|')]]
            while i<len(lines) and lines[i].startswith('| '):
                rows.append([x.strip() for x in lines[i][2:].split('|')]);i+=1
            yield 'table',rows
        elif s.startswith('! '):
            f,h,c=[x.strip() for x in s[2:].split('|')]
            p=assets[f] if f in assets else root/f
            w0,h0=Image.open(p).size
            scale=min(6.82/w0,float(h)/h0)
            yield 'fig',(p,scale*w0,scale*h0,c)
        else:
            for prefix,typ in [('## ','sub'),('# ','head'),('@ ','by'),('~ ','cap')]:
                if s.startswith(prefix):
                    yield typ,s[len(prefix):]
                    break
            else:yield 'body',s
def colfractions(rows):
    if len(rows[0])==5: return [.24,.19,.19,.19,.19]
    if len(rows[0])==3: return [.47,.17,.36]
    if rows[0][0]=='Matching profile':return [.29,.12,.12,.47]
    return [.30,.23,.23,.24]
# Generate Word and PDF from the same paragraphs, figure files and table cells.
doc=Document()
sec=doc.sections[0]
sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=Inches(.73);sec.bottom_margin=Inches(.65);sec.left_margin=sec.right_margin=Inches(.84)
sec.header_distance=Inches(.32);sec.footer_distance=Inches(.29)
styles={'Normal':('Cambria',11,'16252C',False,5.4),'Title':('Calibri',26,'000000',True,8),
'Heading 1':('Calibri',21,'152E3A',True,8),'Heading 2':('Calibri',13,'235266',True,3.5),
'Figure note':('Calibri',9,'334F5B',False,6),'Byline':('Calibri',11,'435D67',False,9)}
for key,(font,sz,hexcol,bold,after) in styles.items():
    style=doc.styles[key] if key in doc.styles else doc.styles.add_style(key,WD_STYLE_TYPE.PARAGRAPH)
    style.font.name=font;style.font.size=Pt(sz);style.font.bold=bold;style.font.color.rgb=RGBColor.from_string(hexcol)
    pf=style.paragraph_format;pf.space_after=Pt(after);pf.space_before=Pt(4 if key=='Heading 2' else 0)
    pf.line_spacing=1.07;pf.widow_control=False
    props=style.element.get_or_add_pPr()
    for border in list(props.findall(qn('w:pBdr'))):props.remove(border)
doc.core_properties.title='Reconstructing lunar terrain from Pragyan’s navigation cameras'
doc.core_properties.subject='Chandrayaan-3 terrain reconstruction methodology and experimental results'
doc.core_properties.author='Chandrayaan-3 capstone project'
hp=sec.header.paragraphs[0];hp.text='CHANDRAYAAN-3 NAVCAM     /     METHODS AND RESULTS'
hp.runs[0].font.name='Calibri';hp.runs[0].font.size=Pt(8);hp.runs[0].font.color.rgb=RGBColor.from_string('486370')
fp=sec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
rr=fp.add_run('10 NOVEMBER 2026      /      ');rr.font.size=Pt(8)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');fp._p.append(fld)
def wdtable(rows):
    t=doc.add_table(rows=0,cols=len(rows[0]));t.autofit=False;t.alignment=WD_TABLE_ALIGNMENT.CENTER
    fr=colfractions(rows)
    for c,f in zip(t.columns,fr):c.width=Inches(6.82*f)
    for j,row in enumerate(rows):
        tr=t.add_row()
        for cell,val,f in zip(tr.cells,row,fr):
            cell.width=Inches(6.82*f);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'274854' if j==0 else ('EDF2F3' if j%2 else 'FFFFFF'));cell._tc.get_or_add_tcPr().append(shade)
            p=cell.paragraphs[0];p.paragraph_format.space_before=Pt(2);p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1
            run=p.add_run(val);run.font.name='Calibri';run.font.size=Pt(9);run.bold=j==0
            if j==0:run.font.color.rgb=RGBColor.from_string('FFFFFF')
for k,page in enumerate(pages):
    for ty,v in records(page):
        if ty=='fig':
            path,w,h,cap=v;p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(2);p.paragraph_format.keep_with_next=True
            p.add_run().add_picture(str(path),width=Inches(w),height=Inches(h));doc.add_paragraph(cap,'Figure note')
        elif ty=='table':wdtable(v)
        else:
            st={'head':'Title' if k==0 else 'Heading 1','sub':'Heading 2','body':'Normal','by':'Byline','cap':'Figure note'}[ty]
            p=doc.add_paragraph(v,st)
            if ty=='head' and k>0:p.paragraph_format.page_break_before=True
doc.save(out/(name+'.docx'))
# Fixed-layout reading edition; fit only by small leading changes, never by cropping.
for tag,file in [('Body','cambria.ttc'),('Sans','calibri.ttf'),('Bold','calibrib.ttf')]:
    pdfmetrics.registerFont(TTFont(tag,str(fonts/file)))
pdf=canvas.Canvas(str(out/(name+'.pdf')),pagesize=(612,792),pageCompression=1)
pdf.setTitle(doc.core_properties.title);pdf.setAuthor(doc.core_properties.author)
C=colors.HexColor
def para(txt,font,size,leading,col):
    return Paragraph(escape(txt),ParagraphStyle('p',fontName=font,fontSize=size,leading=leading,textColor=C(col),splitLongWords=1,spaceBefore=0,spaceAfter=0))
W=490;X=61
def lay(page,k,factor,emit=False):
    y=741
    def paragraph(txt,font,sz,lead,color,after,before=0):
        nonlocal y
        p=para(txt,font,sz*factor,lead*factor,color);w,h=p.wrap(W,1000);y-=h+before
        if emit:p.drawOn(pdf,X,y)
        y-=after*factor
    for ty,v in records(page):
        if ty=='fig':
            path,w,h,cap=v;w*=72;h*=72;y-=h
            if emit:pdf.drawImage(str(path),(612-w)/2,y,width=w,height=h,preserveAspectRatio=True,mask='auto')
            y-=5;paragraph(cap,'Sans',9.5,11.3,'#34505A',8)
        elif ty=='table':
            rows=v;fr=colfractions(rows)
            tx=[[para(val,'Bold' if j==0 else 'Sans',9.4*factor,11.1*factor,'#FFFFFF' if j==0 else '#16252C') for val in row] for j,row in enumerate(rows)]
            tbl=Table(tx,colWidths=[W*f for f in fr])
            tbl.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),C('#274854')),('ROWBACKGROUNDS',(0,1),(-1,-1),[C('#EDF2F3'),colors.white]),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
            w,h=tbl.wrap(W,1000);y-=h
            if emit:tbl.drawOn(pdf,X,y)
            y-=5
        elif ty=='body':paragraph(v,'Body',11.6,15.35,'#17242B',7)
        elif ty=='head':paragraph(v,'Bold',29 if k==0 else 23,32 if k==0 else 26,'#101F26',10)
        elif ty=='sub':paragraph(v,'Bold',14.2,17,'#235266',4,4)
        elif ty=='by':paragraph(v,'Sans',12.3,16,'#435D67',9)
        elif ty=='cap':paragraph(v,'Sans',9.5,11.3,'#34505A',8)
    return y
for k,page in enumerate(pages):
    factor=1
    while lay(page,k,factor)<52 and factor>.8:factor-=.012
    end=lay(page,k,factor,True)
    print('Page',k+1,'font scale',round(factor,2),'bottom',round(end))
    assert end>=48
    pdf.setFont('Sans',8);pdf.setFillColor(C('#486370'))
    pdf.drawString(X,765,'CHANDRAYAAN-3 NAVCAM     /     METHODS AND RESULTS')
    pdf.drawRightString(551,30,'10 NOVEMBER 2026      /      '+str(k+1))
    pdf.showPage()
pdf.save()
