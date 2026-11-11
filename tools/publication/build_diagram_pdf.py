from pathlib import Path
import math,xml.etree.ElementTree as ET
from argparse import ArgumentParser
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3,landscape
parser=ArgumentParser(description='Render CR-EXT-R1 electrical and hydraulic review drawings as a vector PDF.')
repo=Path(__file__).resolve().parents[2]
default=repo/'docs/hardware/extended-rig/CR-EXT-R1'
parser.add_argument('--source-dir',type=Path,default=default)
parser.add_argument('--output-dir',type=Path,default=default)
args=parser.parse_args()
base=args.source_dir
out=args.output_dir
out.mkdir(parents=True,exist_ok=True)
ns='{http://www.w3.org/2000/svg}'
texts={
'Hardware authority':('Hardware authority',420,252),
'24V permanent instrument branch (not through K1/K2)':('Permanent 24 V instrument branch',35,308),
'12V5A / 24V2.5A':('12 V / 5 A; 24 V / 2.5 A',None,None),
'Hardware10Hz watchdog':('Hardware 10 Hz watchdog',None,None),
'Pump12V; valve24V clamps':('Pump 12 V; valve 24 V clamps',None,None),
'Pressure loop24V / 100ohm':('Pressure loop 24 V / 100 ohm',None,None),
'Pi / host3.3V':('Pi / host 3.3 V',None,None),
'Separate official5V supply':('Separate official 5 V supply',None,None),
'No24V or5V on Pi GPIO':('No 24 V or 5 V on Pi GPIO',None,None),
'Hardware authority':('Hardware authority',420,250),
}
pages=[]
for name in ['electrical.svg','hydraulic.svg']:
 root=ET.fromstring((base/name).read_text())
 for e in root:
  if e.tag==ns+'text' and e.text in texts:
   t,x,y=texts[e.text];e.text=t
   if x is not None:e.set('x',str(x))
   if y is not None:e.set('y',str(y))
 pages.append(root)
ET.register_namespace('','http://www.w3.org/2000/svg')
ET.ElementTree(pages[0]).write(out/'CertaRig_Extended_Bench_Electrical_CR-EXT-R1.svg',encoding='unicode')
pdf=out/'CertaRig_Extended_Bench_Circuit_Diagrams_CR-EXT-R1.pdf'
c=canvas.Canvas(str(pdf),pagesize=landscape(A3))
c.setTitle('CertaRig CR-EXT-R1 - Extended bench electrical and water connections')
c.setAuthor('Chintan Dedhia')
for page_no,root in enumerate(pages,1):
 width,height=landscape(A3);margin=28;scale=min((width-2*margin)/1200,(height-2*margin-12)/830)
 c.saveState();c.translate(margin,height-margin);c.scale(scale,scale)
 for e in root:
  tag=e.tag.split('}')[-1]
  if tag in ['defs','style']:continue
  if tag=='rect':
   x=float(e.get('x',0));y=float(e.get('y',0));w=float(e.get('width'));h=float(e.get('height'))
   c.setFillColor(HexColor(e.get('fill','#ffffff')));stroke=e.get('stroke')
   if stroke:c.setStrokeColor(HexColor(stroke))
   c.roundRect(x,-y-h,w,h,float(e.get('rx',0)),stroke=int(bool(stroke)),fill=1)
  elif tag=='text':
   size=float(e.get('font-size',14 if e.get('class')=='small' else 14))
   c.setFont('Helvetica-Bold' if e.get('font-weight')=='bold' else 'Helvetica',size)
   c.setFillColor(HexColor('#152d3a'));c.drawString(float(e.get('x')),-float(e.get('y')),e.text or '')
  elif tag=='polyline':
   pts=[tuple(map(float,p.split(','))) for p in e.get('points').split()]
   c.setStrokeColor(HexColor(e.get('stroke','#176b82')));c.setLineWidth(float(e.get('stroke-width',1)))
   c.setDash([float(x) for x in e.get('stroke-dasharray','').split()] or [])
   p=c.beginPath();p.moveTo(pts[0][0],-pts[0][1])
   for x,y in pts[1:]:p.lineTo(x,-y)
   c.drawPath(p)
   if e.get('marker-end'):
    (px,py),(x,y)=pts[-2:];dx=x-px;dy=y-py;dist=math.hypot(dx,dy);ux=dx/dist;uy=dy/dist
    tip=(x,y);b=(x-10*ux,y-10*uy);head=c.beginPath();head.moveTo(x,-y);head.lineTo(b[0]-4*uy,-(b[1]+4*ux));head.lineTo(b[0]+4*uy,-(b[1]-4*ux));head.close()
    c.setFillColor(HexColor('#176b82'));c.drawPath(head,stroke=0,fill=1)
 c.restoreState();c.setFont('Helvetica',9);c.setFillColor(HexColor('#50707d'))
 c.drawString(margin,16,'CR-EXT-R1 | Review drawing | Detailed supplier schematics and physical commissioning pending')
 c.drawRightString(width-margin,16,str(page_no));c.showPage()
c.save()
from pypdf import PdfReader,PdfWriter
r=PdfReader(pdf);w=PdfWriter();w.add_page(r.pages[0])
w.add_metadata({'/Title':'CertaRig CR-EXT-R1 - Extended bench electrical connection diagram','/Author':'Chintan Dedhia'})
with (out/'CertaRig_Extended_Bench_Circuit_CR-EXT-R1.pdf').open('wb') as stream:w.write(stream)
print(pdf)
