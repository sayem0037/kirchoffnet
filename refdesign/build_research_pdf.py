"""Rebuild the research PDF and its audit manifest from the reviewed manuscript."""
from pathlib import Path
import csv
import json
import hashlib
import re
import math
from html import escape
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, PageBreak, Table, TableStyle, Flowable, KeepTogether)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE=Path(__file__).resolve().parent
OUT=BASE/'output'/'pdf'; OUT.mkdir(parents=True,exist_ok=True)
QA=BASE/'tmp'/'pdfs';QA.mkdir(parents=True,exist_ok=True)
TARGET=OUT/'analog_digital_ring_research.pdf'
WIDTH,HEIGHT=letter
LEFT=48;CW=WIDTH-2*LEFT
INK=HexColor('#193247');TEAL=HexColor('#167a86');MUTED=HexColor('#516572');PALE=HexColor('#edf4f7');LINE=HexColor('#d5e0e6')
pdfmetrics.registerFont(TTFont('ReportArial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ReportArialBold',r'C:\Windows\Fonts\arialbd.ttf'))
pdfmetrics.registerFontFamily('ReportArial',normal='ReportArial',bold='ReportArialBold',italic='ReportArial',boldItalic='ReportArialBold')
styles={
 'Body':ParagraphStyle('Body',fontName='ReportArial',fontSize=10.2,leading=14.6,textColor=INK,spaceAfter=10,allowWidows=0,allowOrphans=0),
 'Section':ParagraphStyle('Section',fontName='ReportArialBold',fontSize=19,leading=24,textColor=INK,spaceAfter=19),
 'Small':ParagraphStyle('Small',fontName='ReportArial',fontSize=8.7,leading=12.2,textColor=MUTED,spaceAfter=8),
 'Table':ParagraphStyle('Table',fontName='ReportArial',fontSize=8.5,leading=11.7,textColor=INK),
 'TableHead':ParagraphStyle('TableHead',fontName='ReportArialBold',fontSize=8.5,leading=11.7,textColor=INK),
 'Equation':ParagraphStyle('Equation',fontName='ReportArial',fontSize=10,leading=15,textColor=INK,leftIndent=11,rightIndent=7,backColor=PALE,borderPadding=9,spaceBefore=4,spaceAfter=12),
 'Cover':ParagraphStyle('Cover',fontName='ReportArialBold',fontSize=30,leading=37,textColor=INK,spaceAfter=23),
 'SubCover':ParagraphStyle('SubCover',fontName='ReportArial',fontSize=15,leading=21,textColor=TEAL,spaceAfter=24)
}

def rich(s):
    s=escape(s)
    s=re.sub(r'\[R(\d+)\]',lambda m:f'<link href="#refR{m[1]}" color="#167a86">[R{m[1]}]</link>',s)
    s=re.sub(r'https?://[^\s]+',lambda m:f'<link href="{m[0]}" color="#167a86">{m[0]}</link>',s)
    return s

class Overview(Flowable):
    def __init__(self):Flowable.__init__(self);self.width=CW;self.height=210
    def draw(self):
        c=self.canv
        lanes=[('CURRENT DIFF-PAIR RING',['Clipped IC seeds','10-stage ring','Learned readout'],'30 analog controls + 22 learned readout values'),('RESISTIVE CROSSBAR',['DAC / drivers','1T1R + TIAs','ADC / tanh'],'Conductance weights; hybrid learning'),('DIGITAL MLP',['Codes / memory','Signed MACs','Rescale / ReLU'],'Integer deployment requires a full arithmetic contract'),('KFQ NETWORK',['Differential input','4-MOS synapses','Diff-pair neurons'],'Gate-voltage weights; simulator-adjoint learning')]
        for k,(name,blocks,note) in enumerate(lanes):
            y=174-k*49
            c.setFont('ReportArialBold',8.5);c.setFillColor(INK);c.drawString(0,y+13,name)
            for j,b in enumerate(blocks):
                x=151+j*119
                c.setFillColor(PALE);c.setStrokeColor(LINE);c.roundRect(x,y,108,29,4,fill=1,stroke=1)
                c.setFillColor(INK);c.setFont('ReportArial',8.2);c.drawCentredString(x+54,y+10,b)
                if j<2:
                    c.setStrokeColor(TEAL);c.line(x+109,y+14,x+118,y+14)
                    c.line(x+115,y+17,x+118,y+14);c.line(x+115,y+11,x+118,y+14)
            c.setFillColor(MUTED);c.setFont('ReportArial',8.5);c.drawString(151,y-13,note)

class RingStage(Flowable):
    """Vector schematic traced from netlist_ring.py; named nets share connections."""
    def __init__(self):Flowable.__init__(self);self.width=CW;self.height=345
    def draw(self):
        c=self.canv
        c.setFillColor(INK);c.setFont('ReportArialBold',10)
        c.drawString(0,330,'CURRENT DESIGN: FIXED ENCODER -> ANALOG EVOLUTION -> LEARNED READOUT')
        labels=[('2-D input','Input standardization'),('10 IC voltages','Fixed affine + clip'),('10-stage ring','Read h1..h10 @100ns'),('2 class scores','Standardize + affine')]
        for i,(title,sub) in enumerate(labels):
            x=i*129
            c.setFillColor(PALE);c.setStrokeColor(LINE);c.roundRect(x,276,117,40,4,fill=1,stroke=1)
            c.setFillColor(INK);c.setFont('ReportArialBold',8.6);c.drawCentredString(x+58.5,299,title)
            c.setFont('ReportArial',7.7);c.drawCentredString(x+58.5,285,sub)
            if i<3:
                c.setStrokeColor(TEAL);c.line(x+118,296,x+127,296)
                c.line(x+124,299,x+127,296);c.line(x+124,293,x+127,296)
        c.setFillColor(INK);c.setFont('ReportArialBold',10);c.drawString(0,251,'Actual repeated stage j: five MOSFETs and one state capacitor')
        c.setFont('ReportArial',8);c.setFillColor(MUTED)
        c.drawString(0,237,'h_(j-1) drives the signal gate; stage 1 uses h_10, closing the loop.')
        c.setStrokeColor(INK);c.setLineWidth(1.15)
        def dot(x,y):c.setFillColor(INK);c.circle(x,y,2,fill=1,stroke=0)
        def ground(x,y):
            c.line(x,y+8,x,y)
            for k,w in enumerate([10,6,2]):c.line(x-w/2,y-3*k,x+w/2,y-3*k)
        def mos(x,y,label,pmos=False):
            c.setStrokeColor(INK);c.line(x,y+21,x,y+13);c.line(x,y+13,x-7,y+10)
            c.line(x-7,y+10,x-7,y-10);c.line(x-7,y-10,x,y-13);c.line(x,y-13,x,y-21)
            c.line(x-20,y+12,x-20,y-12)
            if pmos:
                c.circle(x-24,y,3.5,fill=0,stroke=1);c.line(x-48,y,x-27.5,y)
            else:c.line(x-48,y,x-20,y)
            c.setFillColor(INK);c.setFont('ReportArialBold',8.5);c.drawString(x+10,y+2,label)
            c.setFont('ReportArial',7.5);c.drawString(x+10,y-10,'PCH' if pmos else 'NCH')
        a,b,tail=177,359,268
        c.line(a,220,b,220);c.line(a,220,a,213);c.line(b,220,b,213)
        c.setFont('ReportArialBold',9);c.drawString(244,223,'VDD = 3.3 V')
        mos(a,192,'Mpd_j',True);mos(b,192,'Mps_j',True)
        for x in (a,b):
            c.setFont('ReportArial',8);c.drawRightString(x-51,190,'th_j')
        c.line(a,171,a,141);c.line(b,171,b,141)
        dot(a,147);dot(b,147)
        c.setFont('ReportArial',8.5);c.drawString(a+10,148,'dm_j');c.drawString(b+10,151,'h_j')
        c.line(b,147,454,147);c.setFont('ReportArial',8);c.drawString(416,153,'state output')
        mos(a,120,'Md_j');mos(b,120,'Ms_j')
        c.setFont('ReportArial',8.5);c.drawRightString(a-51,118,'vn_j / VN_j')
        c.drawRightString(b-51,118,'h_(j-1)')
        c.line(a,99,a,88);c.line(b,99,b,88);c.line(a,88,b,88);dot(tail,88)
        c.line(tail,88,tail,81);c.setFont('ReportArial',8);c.drawString(tail+8,90,'tl_j')
        mos(tail,60,'Mt_j');c.setFont('ReportArial',8.5);c.drawRightString(tail-51,58,'vb_j / VB_j')
        ground(tail,31)
        c.line(454,147,454,116);c.line(445,116,463,116);c.line(445,111,463,111)
        c.line(454,111,454,98);ground(454,90)
        c.setFont('ReportArial',8);c.drawString(468,116,'C_j');c.drawString(468,105,'1 pF')
        c.setFillColor(MUTED);c.setFont('ReportArial',7.6)
        c.drawString(0,13,'th_j is driven by VTH_j; PMOS bulks = VDD, NMOS bulks = ground (bulk leads omitted).')
        c.drawString(0,1,'The two PMOS gates share th_j. They are biased active loads, not a diode-connected mirror.')

class HistoricalBars(Flowable):
    def __init__(self,rows):Flowable.__init__(self);self.rows=rows;self.width=CW;self.height=172
    def draw(self):
        c=self.canv;colors=[TEAL,HexColor('#9d601f')]
        c.setFillColor(INK);c.setFont('ReportArialBold',10);c.drawString(0,154,'Local final accuracies: different widths / protocols, not a ranking')
        for idx,(task,a,b) in enumerate(self.rows):
            y=119-idx*45
            c.setFont('ReportArial',9);c.setFillColor(INK);c.drawString(0,y+4,task)
            for k,v in enumerate([a,b]):
                yy=y-k*14
                c.setFillColor(colors[k]);c.rect(84,yy,330*v,9,fill=1,stroke=0)
                c.setFillColor(INK);c.setFont('ReportArial',9);c.drawString(424,yy,f'{v*100:.1f}%')
        c.setFont('ReportArial',8.5);c.setFillColor(TEAL);c.drawString(84,3,'Crossbar 2-16-2')
        c.setFillColor(colors[1]);c.drawString(241,3,'Digital 2-8-2')

class LearningLoop(Flowable):
    def __init__(self):Flowable.__init__(self);self.width=CW;self.height=105
    def draw(self):
        c=self.canv
        labels=['Read actual\nforward circuit','Compute loss\nand gradients','Accumulate\nlegal updates','Program or set\nweight controls']
        for i,lab in enumerate(labels):
            x=i*129
            c.setFillColor(PALE);c.setStrokeColor(LINE);c.roundRect(x,37,117,48,5,fill=1,stroke=1)
            c.setFillColor(INK);c.setFont('ReportArial',9)
            for j,line in enumerate(lab.split('\n')):c.drawCentredString(x+58.5,65-j*13,line)
            if i<3:
                c.setStrokeColor(TEAL);c.line(x+118,61,x+128,61)
                c.line(x+125,64,x+128,61);c.line(x+125,58,x+128,61)
        c.setFillColor(MUTED);c.setFont('ReportArial',8.7)
        c.drawString(0,17,'A simulator can expose gradients that a physical controller cannot obtain without additional circuitry.')

class Doc(BaseDocTemplate):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw)
        self.addPageTemplates(PageTemplate(id='report',frames=[Frame(LEFT,49,CW,HEIGHT-103,id='main',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.chrome))
    def chrome(self,c,doc):
        c.saveState()
        if doc.page>1:
            c.setFont('ReportArial',8);c.setFillColor(MUTED)
            c.drawString(LEFT,HEIGHT-30,'ANALOG / DIGITAL / KIRCHHOFF | RESEARCH & COMPARISON')
            c.setStrokeColor(LINE);c.line(LEFT,HEIGHT-39,WIDTH-LEFT,HEIGHT-39)
        c.setFont('ReportArial',8);c.setFillColor(MUTED)
        c.drawString(LEFT,29,'Research review | 12 October 2026 | evidence levels stated explicitly')
        c.drawRightString(WIDTH-LEFT,29,str(doc.page));c.restoreState()
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and f.style.name=='Section' and getattr(f,'_bookmark',None):
            key=f._bookmark;self.canv.bookmarkPage(key);self.canv.addOutlineEntry(f.getPlainText(),key,0,False)
            self.notify('TOCEntry',(0,f.getPlainText(),self.page,key))

def paragraph(s,style='Body'):return Paragraph(rich(s),styles[style])
def table(lines):
    rows=[[cell.strip() for cell in line.strip().strip('|').split('|')] for line in lines]
    rows=[r for r in rows if not all(re.fullmatch(r'[-: ]+',c) for c in r)]
    n=len(rows[0]);widths=([110,135,135,CW-380] if n==4 else [115,(CW-115)/2,(CW-115)/2] if n==3 else [CW/n]*n)
    formatted=[[Paragraph(rich(cell),styles['TableHead' if i==0 else 'Table']) for cell in row] for i,row in enumerate(rows)]
    tb=Table(formatted,colWidths=widths,repeatRows=1,hAlign='LEFT')
    tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.8,LINE),('LINEBELOW',(0,1),(-1,-1),.35,LINE)]))
    return [tb,Spacer(1,13)]

raw=(BASE/'research_report.md').read_text(encoding='utf-8')
sections=[]
for title,body in re.findall(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)',raw,re.S|re.M):sections.append((title,body))
story=[Spacer(1,26),Paragraph('Analog crossbars,<br/>digital MLPs, and<br/>your Kirchhoff designs',styles['Cover']),Paragraph('How they compute, learn, and deploy -<br/>and how to compare them fairly',styles['SubCover']),Spacer(1,15),Overview(),Spacer(1,22),paragraph('Focused on your confirmed toy2d_serial_diff ring, with resistive crossbar, digital MLP, and feedforward KFQ comparisons.'),paragraph('30 selected references. Primary papers, official documentation, and inspected source code. Includes circuit diagrams, checkpoint findings, and a ring-specific experimental plan.'),Spacer(1,17),paragraph('Prepared 12 October 2026. No new training runs or silicon measurements are claimed.','Small'),PageBreak(),Paragraph('Contents',styles['Section'])]
toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC',fontName='ReportArial',fontSize=9,leading=12,textColor=INK,leftIndent=0,firstLineIndent=0,spaceBefore=0)]
story.extend([toc,PageBreak()])
for idx,(title,body) in enumerate(sections):
    h=Paragraph(escape(title),styles['Section']);h._bookmark=f'section{idx}'
    story.append(h)
    if title.startswith('2. '):story.extend([Overview(),Spacer(1,12)])
    if title.startswith('5. '):story.extend([LearningLoop(),Spacer(1,12)])
    if title.startswith('13A. '):story.extend([RingStage(),Spacer(1,16)])
    if title.startswith('15. '):story.extend([HistoricalBars([('Two moons',.975,1),('Circle',.975,1),('Two spirals',.908333,.783333)]),Spacer(1,12)])
    blocks=re.split(r'\n\s*\n',body.strip())
    for block in blocks:
        block=block.strip()
        if not block:continue
        if block.startswith('|'):
            story.extend(table(block.splitlines()))
        elif block.startswith('EQUATION:'):
            for line in block.splitlines():story.append(paragraph(line.removeprefix('EQUATION:').strip(),'Equation'))
        elif title=='References':
            text=re.sub(r'^\[R(\d+)\]',lambda m:f'REFANCHOR{m[1]} ',block)
            m=re.match(r'REFANCHOR(\d+) ',text)
            if m:
                ref=m[1];text=text[m.end():]
                p=Paragraph(f'<a name="refR{ref}"/><b>[R{ref}]</b> '+rich(text),styles['Small']);story.append(p)
            else:story.append(paragraph(block,'Small'))
        else:story.append(paragraph(' '.join(block.splitlines())))
    if idx!=len(sections)-1:story.append(PageBreak())
doc=Doc(str(TARGET),pagesize=letter,leftMargin=LEFT,rightMargin=LEFT,topMargin=54,bottomMargin=49,title='Analog Crossbars, Digital MLPs, and Kirchhoff Designs: Research and Comparison',author='Prepared for Ahmad Sayeed Sayem',subject='Operation, training, validation, and fair hardware comparison grounded in local source code')
doc.multiBuild(story)

# Reproducibility manifest: source hashes and local historical evidence.
local=['xbar1t1r_device.py','xbar1t1r_netlist.py','xbar1t1r_train.py','digital_train.py','digital_netlist.py','digital_verify.py','verify_digital.log','../kfabric/netlist_kfq.py','../kfabric/netlist_kdn.py','../kfabric/train_kfq.py','../kfabric/kfq_spec.py','../kfabric/ARCHITECTURE.md','../kfabric/simulator_api.py','../toy2d_serial_diff/netlist_ring.py','../toy2d_serial_diff/train_ring.py','../toy2d_serial_diff/dataset.py','../toy2d_serial_diff/ring_common.py','../toy2d_serial_diff/diag_ring.py','../toy2d_serial_diff/animate_ring.py','../toy2d_serial_diff/README.md','../compare/tech.py','../compare/metrics.py','../compare/measure_existing.py']
ring_dir=BASE.parent/'toy2d_serial_diff'
for p in sorted((ring_dir/'results').iterdir()):
    if p.suffix in ('.json','.csv','.txt'):
        local.append('../toy2d_serial_diff/results/'+p.name)
sim=Path(r'D:\Simulator\circuit_simulator with level3\src\models\mosfet_level1_model.py')
records=[]
for rel in local:
    p=(BASE/rel).resolve();records.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
records.append({'path':str(sim),'sha256':hashlib.sha256(sim.read_bytes()).hexdigest()})
runs=[]
for p in sorted((BASE/'results').glob('*_meta.json')):
    if not (p.name.endswith('_fix_meta.json') or (p.name.startswith('digital_') and p.name.endswith('_run_meta.json'))):continue
    m=json.loads(p.read_text());rows=list(csv.DictReader(Path(str(p).replace('_meta.json','_log.csv')).open()))
    vals=[float(r['test_acc']) for r in rows];best=max(vals)
    runs.append({'source':str(p),'sizes':m['sizes'],'n_train':m['n_train'],'n_test':m['n_test'],'seed':m['seed'],'rule':m['update_rule'],'epochs':len(rows),'final':vals[-1],'best':best,'actual_best_epoch':next(int(r['epoch']) for r in rows if float(r['test_acc'])==best),'last10_mean':sum(vals[-10:])/len(vals[-10:])})
decks=[]
for p in sorted((BASE/'netlists'/'trained').glob('*.sp')):
    counts={k:0 for k in 'MRCV'}
    for line in p.read_text().splitlines():
        if line and line[0] in counts:counts[line[0]]+=1
    decks.append({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'counts':counts})
ring_runs=[]
for name in ['twomoon','circle','2spirals']:
    p=ring_dir/'results'/f'{name}_ring_best.json';m=json.loads(p.read_text())
    ring_runs.append({'dataset':name,'source':str(p),'checkpoint_epoch':m['epoch'],'stored_test_acc':m['test_acc'],'stored_train_acc':m['train_acc'],'nominal_n_train':40,'nominal_n_test':24,'valid_test_count':'not saved','metric_warning':'accuracy measured before circuit step; stored circuit may be post-step','animation_source':str(ring_dir/'results'/f'{name}_ring_anim_stdout.txt'),'animation_warning':'new readout fitted to combined train and test labels; circle falls back to frozen circ_init'})
previous_path=OUT/'research_evidence.json'
previous=json.loads(previous_path.read_text()) if previous_path.exists() else {}
evidence={'date':'2026-10-12','report':str(TARGET),'confirmed_current_design':str(ring_dir),'research_manuscript_sha256':hashlib.sha256(raw.encode()).hexdigest(),'source_hashes':records,'historical_runs':runs,'ring_historical_artifacts':ring_runs,'trained_deck_counts':decks,'scope':'Read-only code/data audit and targeted numerical/Boolean checks; no new training, full SPICE benchmark, or hardware measurements.'}
if 'level1_direct_model_smoke_check' in previous:
    evidence['level1_direct_model_smoke_check']=previous['level1_direct_model_smoke_check']
(OUT/'research_evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
print(str(TARGET))
print('Manuscript words:',len(raw.split()),'sections:',len(sections))
