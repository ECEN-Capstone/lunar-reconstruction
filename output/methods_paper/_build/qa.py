from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from pypdf import PdfReader
import sys
src=Path(sys.argv[1])
qa=src.parent/'_build'/'qa' if src.parent.name!='_build' else src.parent/'qa_word'
qa.mkdir(parents=True,exist_ok=True)
pdf=pdfium.PdfDocument(src)
imgs=[]
for i,page in enumerate(pdf):
    im=page.render(scale=1.30).to_pil().convert('RGB')
    im.save(qa/f'page_{i+1:02}.png')
    im.thumbnail((288,374),Image.Resampling.LANCZOS)
    imgs.append(im)
for batch in range(0,len(imgs),8):
    sheet=Image.new('RGB',(4*300,2*400),'#dbe0e0')
    for n,img in enumerate(imgs[batch:batch+8]):
        x=n%4*300+6;y=n//4*400+4
        sheet.paste(img,(x,y));ImageDraw.Draw(sheet).text((x+5,y+374),str(batch+n+1),fill='black')
    sheet.save(qa/f'spread_{batch+1}.jpg',quality=92)
reader=PdfReader(src)
print('pages',len(reader.pages))
for i,page in enumerate(reader.pages):
    s=page.extract_text()
    print(i+1,len(s),s[:82].replace('\n',' '))
