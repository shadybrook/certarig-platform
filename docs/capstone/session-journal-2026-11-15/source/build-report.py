from pathlib import Path
import json, os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
BASE=Path(__file__).resolve().parent
content=json.loads((BASE/'report-content.json').read_text())
doc=Document();section=doc.sections[0]
section.page_width=Inches(8.5);section.page_height=Inches(11)
for k in ['top_margin','bottom_margin','left_margin','right_margin']:setattr(section,k,Inches(1))
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption']:
 s=doc.styles[name];s.font.name='Times New Roman';s.font.size=Pt(14 if name in ['Title','Heading 1','Heading 2','Heading 3'] else 12);s.font.color.rgb=RGBColor(0,0,0);s.paragraph_format.line_spacing=1.5;s.paragraph_format.space_after=Pt(8)
 rpr=s.element.get_or_add_rPr()
 for old in list(rpr.findall(qn('w:rFonts'))):rpr.remove(old)
 fonts=OxmlElement('w:rFonts')
 for attr in ['ascii','hAnsi','eastAsia','cs']:fonts.set(qn('w:'+attr),'Times New Roman')
 rpr.insert(0,fonts)
 if s.element.pPr is not None:
  for border in list(s.element.pPr.findall(qn('w:pBdr'))):s.element.pPr.remove(border)
 if name in ['Title','Heading 1','Heading 2','Heading 3']:s.font.bold=True
for name in ['Heading 1','Heading 2','Heading 3']:doc.styles[name].paragraph_format.keep_with_next=True
for style in doc.styles:
 if style.element.pPr is not None:
  for border in list(style.element.pPr.findall(qn('w:pBdr'))):style.element.pPr.remove(border)
footer=section.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
doc.add_paragraph(content['title'],style='Title').alignment=WD_ALIGN_PARAGRAPH.CENTER
for t in ['Capstone implementation report draft','Chintan Dedhia','BSc Computer Science Online Mode','Roll number and institution details to confirm','Academic year and current supervisor to confirm','15 November 2026']:
 doc.add_paragraph(t).alignment=WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph('Draft status',style='Heading 2')
doc.add_paragraph('This report records a locally tested software increment. It is not a final university submission. Genuine provider and container qualification, physical evidence or an approved scope amendment, institutional metadata and a recorded demo remain outstanding.')
doc.add_paragraph('Declaration',style='Heading 2')
doc.add_paragraph('The institution requires a student declaration of original work. The student must review and complete that declaration before submission. No signature or submission approval is supplied in this draft.')
doc.add_page_break();doc.add_paragraph('Abstract',style='Heading 1')
assert 200<=len(content['abstract'].split())<=300,len(content['abstract'].split())
for p in content['abstract'].split('\n\n'):doc.add_paragraph(p)
doc.add_page_break();doc.add_paragraph('Contents',style='Heading 1')
for c in content['chapters']:doc.add_paragraph(c['title'])
for t in ['References','Appendix A User manual','Appendix B Installation guide','Appendix C Source and demonstration links']:doc.add_paragraph(t)
doc.add_paragraph('List of figures',style='Heading 2');doc.add_paragraph('Figure 1 Session Journal with deterministic prototype data')
doc.add_paragraph('List of tables',style='Heading 2');doc.add_paragraph('Table 1 Selected acceptance cases')
doc.add_paragraph('Abbreviations',style='Heading 2');doc.add_paragraph('API Application Programming Interface; CSV Comma Separated Values; HIL Hardware in the Loop; OIDC OpenID Connect; SDK Software Development Kit; UI User Interface.')
for idx,c in enumerate(content['chapters']):
 doc.add_page_break();doc.add_paragraph(c['title'],style='Heading 1')
 for title,text in c['sections']:
  doc.add_paragraph(title,style='Heading 2');doc.add_paragraph(text)
 if idx==1:
  image=Path(os.environ.get('CERTARIG_REPORT_SCREENSHOT',str(BASE/'assets/journal.png')))
  if image.exists():
   p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run().add_picture(str(image),width=Inches(6.4))
   doc.add_paragraph('Figure 1 Session Journal with deterministic prototype data',style='Caption')
 if idx==2:
  doc.add_paragraph('Table 1 Selected acceptance cases',style='Caption')
  table=doc.add_table(rows=1,cols=5);table.style='Table Grid';table.autofit=False
  widths=[.75,1.45,1.25,2.15,.9]
  for col,width in zip(table.columns,widths):col.width=Inches(width)
  for cell,width,label in zip(table.rows[0].cells,widths,['ID','Description','Input','Expected result','Status']):
   cell.width=Inches(width);cell.text=label
   for run in cell.paragraphs[0].runs:run.bold=True
  table.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
  cases=[['BS01','Revision conflict','Old revision','Refuse overwrite','Passed'],['BS02','Incomplete mapping','Unknown units','Explicit blockers','Passed'],['BS03','Unfamiliar procedure','Electrical V','Analysis only','Passed'],['BS04','Scope loss','Revoked grant','Access refused','Passed'],['UI01','Draft recovery','Saved session URL','Restore actual conversation','Passed'],['UI02','Independent review','Two test identities','Author refused and Reviewer allowed','Passed'],['RT01','Container isolation','Pinned image absent','Refuse execution','Unrun'],['HW01','Physical feedback','No new trial','No result claimed','Unrun']]
  for values in cases:
   row=table.add_row();row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
   for cell,width,text in zip(row.cells,widths,values):cell.width=Inches(width);cell.text=text
  for row in table.rows:
   for cell in row.cells:
    for p in cell.paragraphs:p.paragraph_format.line_spacing=1.5;p.paragraph_format.space_after=Pt(4)
doc.add_page_break();doc.add_paragraph('References',style='Heading 1')
for i,t in enumerate(content['references'],1):doc.add_paragraph(f'[{i}] {t}')
appendices=[('Appendix A User manual','Select a permitted bench and describe the commissioning goal. Inspect the proposed instructions, tool scope and limits. Save a draft and resolve any missing-information prompts. Save an immutable version, collect the evaluation and inspect its raw traces. Obtain genuine Sandbox qualification before independent deployment review. Start bounded observation separately and monitor its health. Revoke when finished. Export evidence and run the offline verifier. For an unfamiliar bench, open Benches and create a description; resolve support questions without treating description review as execution authority.'),('Appendix B Installation guide','Clone the release source and create an isolated Python environment. Install the documented development and platform extras; install Studio test dependencies only when running browser checks. Follow docs/product/AGENT_LIFECYCLE.md for actual identity provisioning, local simulator services, managed model sign-in, qualified Sandbox and the observation runtime. Run the documented preflight before preparing a runtime. Do not overwrite an existing installation, switch Docker contexts globally or weaken isolation. Source checkout execution is required for Studio assets in this release.'),('Appendix C Source and demonstration links','Source repository: https://github.com/shadybrook/certarig-platform. Branch: product/session-journal-2026-11-14. Validation records: docs/product/validation/session-journal. Demonstration video link: pending an actual attended recording. Supervisor remarks: no new remarks received. Final institution deadline and submission process: unconfirmed.')]
for title,text in appendices:doc.add_paragraph(title,style='Heading 1');doc.add_paragraph(text)
out=BASE.parent/'files'/'CertaRig_Report_Draft_2026-11-15.docx';out.parent.mkdir(parents=True,exist_ok=True);doc.save(out)
(BASE/'report-metadata.json').write_text(json.dumps({'abstract_words':len(content['abstract'].split()),'status':'draft','body_font':'Times New Roman','body_pt':12,'heading_pt':14,'line_spacing':1.5,'margins_inch':1,'page_numbers':'bottom-centred'},indent=2))
print(out)
