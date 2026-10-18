"""Export PPT figures and exact arithmetic decks from digital_netlist.py.
The MLP figure describes software; the circuit figures describe existing primitives.
"""
from pathlib import Path
from html import escape
import json
import hashlib
import digital_netlist as D

BASE=Path(__file__).resolve().parent
OUT=BASE/'figs'/'digital_schematics'
OUT.mkdir(parents=True,exist_ok=True)
INK='#172c42'; BLUE='#166da0'; GREEN='#25724f'; PALE='#eef5fa'
def t(x,y,s,size=22,anchor='start',color=INK,weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{color}" font-weight="{weight}">{escape(str(s))}</text>'
def w(d,color=INK,width=2):
    return f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="none" stroke-linejoin="round"/>'
def dot(x,y):return f'<circle cx="{x}" cy="{y}" r="4" fill="{INK}"/>'
def arrow(x1,y1,x2,y2):return w(f'M{x1} {y1} L{x2} {y2}',BLUE,3)+f'<path d="M{x2-12} {y2-7} L{x2} {y2} L{x2-12} {y2+7}" fill="none" stroke="{BLUE}" stroke-width="3"/>'
def save(name,s,width=1920,height=1080):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Arial, Helvetica, sans-serif"><title>{escape(name)}</title><rect width="100%" height="100%" fill="white"/>{s}</svg>'
    (OUT/(name+'.svg')).write_text(svg,encoding='utf-8')
def box(x,y,width,height,lines):
    s=f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" fill="{PALE}" stroke="{BLUE}" stroke-width="2"/>'
    for i,line in enumerate(lines):s+=t(x+width/2,y+height/2+(i-(len(lines)-1)/2)*34,line,25,'middle',weight=500 if i==0 else 400)
    return s
def mos(x,y,name,p=False):
    s=w(f'M{x+16} {y-36} V{y-18} H{x} M{x} {y-18} V{y-9} M{x} {y-4} V{y+4} M{x} {y+9} V{y+18} H{x+16} V{y+36} M{x-12} {y-22} V{y+22}')
    s+=w(f'M{x-36} {y} H{x-(21 if p else 12)}')
    if p:s+=f'<circle cx="{x-17}" cy="{y}" r="4" fill="white" stroke="{INK}" stroke-width="2"/>'
    return s+t(x+30,y-4,name,21)
def ground(x,y):return w(f'M{x} {y-8} V{y} M{x-12} {y} H{x+12} M{x-8} {y+6} H{x+8} M{x-4} {y+12} H{x+4}')

class Recorded(D.GateNetlist):
    def __init__(self):super().__init__();self.records=[]
    def nand(self,a,b,out):
        super().nand(a,b,out);self.records.append({'id':self.n,'type':'NAND','inputs':[a,b],'out':out})
        return out
    def inv(self,a,out):
        super().inv(a,out);self.records.append({'id':self.n,'type':'INV','inputs':[a],'out':out})
        return out

fa=Recorded();fa.full_adder('a','b','cin','s','cout')
assert len(fa.records)==11 and len(fa.lines)==44
(OUT/'full_adder_exact.sp').write_text(fa.deck({'a':0,'b':0,'cin':0}),encoding='utf-8')
mul=Recorded();A=['a0','a1'];B=['b0','b1'];P=[None]*4;mul.array_multiply(A,B,P)
assert len(mul.lines)==112
(OUT/'unsigned_multiplier_2x2_exact.sp').write_text(mul.deck({n:0 for n in A+B}),encoding='utf-8')
add=Recorded();add.ripple_add(['a0','a1'],['b0','b1'],['s0','s1'])
assert len(add.lines)==88
(OUT/'ripple_adder_2bit_exact.sp').write_text(add.deck({n:0 for n in A+B}),encoding='utf-8')

# Software model and trained parameter shapes, from the existing metadata.
m=json.loads((BASE/'results'/'digital_circle_run_meta.json').read_text())
assert m['sizes']==[2,8,2] and m['bits']==8
q1,q2=m['int_weights'];assert len(q1['q'])==3 and len(q1['q'][0])==8 and len(q2['q'])==9 and len(q2['q'][0])==2
s=t(55,65,'Digital MLP · implemented 2 → 8 → 2 model',42,weight=500)
s+=t(55,112,'Source: digital_train.py · circle trained weights: results/digital_circle_run_meta.json',23)
s+=t(55,185,'Network topology',30,weight=500)
ys_in=[375,595];ys_hidden=[240+79*i for i in range(8)];ys_out=[375,595]
for yi in ys_in:
    for yh in ys_hidden:s+=w(f'M250 {yi} L680 {yh}','#b7c9d6',1.5)
for yh in ys_hidden:
    for yo in ys_out:s+=w(f'M680 {yh} L1110 {yo}','#b7c9d6',1.5)
for x,ys,prefix in [(250,ys_in,'x'),(680,ys_hidden,'h'),(1110,ys_out,'score')]:
    for i,y in enumerate(ys):
        s+=f'<circle cx="{x}" cy="{y}" r="25" fill="white" stroke="{BLUE}" stroke-width="3"/>'
        s+=t(x,y+7,f'{i+1}',21,'middle')
    s+=t(x,850,{'x':'2 inputs','h':'8 ReLU units','score':'2 class scores'}[prefix],26,'middle',weight=500)
s+=t(475,220,'W1 + bias',23,'middle')+t(895,220,'W2 + bias',23,'middle')
s+=box(1280,235,575,130,['Layer 1 parameters','3 × 8 = 24 values, including bias',f'Exported integer weight scale: {q1["scale"]:g}'])
s+=box(1280,420,575,130,['Hidden activation','ReLU, then 8-bit quantization','Scale recomputed for each sample'])
s+=box(1280,605,575,130,['Layer 2 parameters','9 × 2 = 18 values, including bias',f'Exported integer weight scale: {q2["scale"]:g}'])
s+=t(55,925,'Forward: append bias → quantized W1 multiply → ReLU + quantize → append bias → W2 multiply → argmax',25,weight=500)
s+=t(55,980,'Software model: input and matrix arithmetic remain floating point; quantized values are dequantized.',23)
s+=t(55,1020,'The folder contains no complete trained digital MLP transistor netlist, SRAM, registers, or control circuit.',23)
save('digital_mlp_model_slide',s)

# Actual hierarchical full-adder connections from full_adder(), with CMOS NAND expansion.
def gate(x,y,kind,name):
    if kind=='XOR':
        shape=w(f'M{x} {y} Q{x+35} {y+45} {x} {y+90} Q{x+60} {y+90} {x+120} {y+45} Q{x+60} {y} {x} {y} M{x-10} {y} Q{x+25} {y+45} {x-10} {y+90}')
        shape+=w(f'M{x-35} {y+25} H{x+14} M{x-35} {y+65} H{x+14} M{x+120} {y+45} H{x+160}')
    else:
        shape=w(f'M{x} {y} H{x+60} Q{x+120} {y} {x+120} {y+45} Q{x+120} {y+90} {x+60} {y+90} H{x} Z M{x-35} {y+25} H{x} M{x-35} {y+65} H{x}')
        shape+=f'<circle cx="{x+127}" cy="{y+45}" r="7" fill="white" stroke="{INK}" stroke-width="2"/>'+w(f'M{x+134} {y+45} H{x+160}')
    return shape+t(x+55,y+52,kind,20,'middle')+t(x+55,y-17,name,20,'middle')

s=t(55,65,'Digital arithmetic · actual full-adder and CMOS NAND',40,weight=500)
s+=t(55,110,'Source: digital_netlist.py · hierarchical connections match the generator',23)
s+=t(55,175,'Full adder: 2 XOR blocks + 3 NAND gates = 11 NANDs = 44 MOSFETs',27,weight=500)
s+=gate(170,290,'XOR','XOR1 · 4 NANDs')+gate(590,290,'XOR','XOR2 · 4 NANDs')
s+=t(95,310,'a',23)+t(95,350,'b',23)+w('M110 315 H135 M110 355 H135')
s+=w('M330 335 H545 V315 H555')+t(450,317,'s_h',23,'middle')
s+=t(505,375,'cin',23)+w('M525 395 H545 V355 H555')
s+=w('M750 335 H1030')+t(1035,343,'s',25)
s+=gate(170,590,'NAND','NAND9')+gate(590,590,'NAND','NAND10')+gate(930,590,'NAND','NAND11')
s+=t(95,610,'a',23)+t(95,650,'b',23)+w('M110 615 H135 M110 655 H135')
s+=t(500,610,'s_h',23)+t(500,650,'cin',23)+w('M540 615 H555 M540 655 H555')
s+=w('M330 635 H400 V495 H865 V615 H895')+t(425,477,'cout_n1',23)
s+=w('M750 635 H825 V655 H895')+t(780,697,'cout_n2',23,'middle')
s+=w('M1090 635 H1120')+t(1123,643,'cout',23)
s+=t(55,790,'s = a XOR b XOR cin',27,weight=500)
s+=t(55,834,'cout = (a AND b) OR (cin AND (a XOR b))',27,weight=500)
s+=t(55,910,'Existing ripple adder repeats this cell; unsigned multiplier uses AND partial products and full adders.',23)
s+=t(55,950,'Saved DC checks: full adder 8/8; 2-bit adder 16/16; 2×2 multiplier 14/16 converged, all 14 correct.',23)
s+=t(55,1015,'NAND expansion shown at right is gate 1 of the full adder. NMOS bulk = ground; PMOS bulk = vdd.',22)
# Expanded NAND1, with exact names and terminal mapping checked against emitted deck.
c={line.split()[0]:line.split() for line in fa.lines}
expected={'MNA1':['s_h_x1','a','nx1','0'],'MNB1':['nx1','b','0','0'],'MPA1':['s_h_x1','a','vdd','vdd'],'MPB1':['s_h_x1','b','vdd','vdd']}
for name,pins in expected.items():assert c[name][1:5]==pins
sub=t(5,5,'NAND1 transistor expansion',26,weight=500)
sub+=t(250,54,'vdd · 3.3 V',22,'middle')+w('M116 70 H336 M116 70 V124 M336 70 V124')
sub+=mos(100,160,'MPA1',True)+mos(320,160,'MPB1',True)
sub+=t(40,144,'a',22)+t(260,144,'b',22)
sub+=w('M116 196 V250 H336 V196 M236 250 V294 M336 250 H455')+dot(236,250)
sub+=t(460,258,'s_h_x1',21)
sub+=mos(220,330,'MNA1')+t(157,313,'a',22)
sub+=w('M236 366 V424')+dot(236,395)+t(248,401,'nx1',22)
sub+=mos(220,460,'MNB1')+t(157,443,'b',22)
sub+=w('M236 496 V542')+ground(236,550)
sub+=t(15,630,'NMOS: W/L = 2 / 0.35 µm',22)+t(15,668,'PMOS: W/L = 5 / 0.35 µm',22)
s+=f'<g transform="translate(1280,220)">{sub}</g>'
save('digital_full_adder_cmos_slide',s)

# Full transistor schematic: all 11 actual NAND cells, joined by exact named nets.
parts=[]
for g in fa.records:
    n=g['id'];a,b=g['inputs'];out=g['out'];x=((n-1)%4)*480;y=((n-1)//4)*610
    z=t(15,35,f'NAND{n}: {out}',21,weight=500)
    z+=t(215,70,'vdd',18,'middle')+w('M116 88 H316 M116 88 V114 M316 88 V114')
    z+=mos(100,150,f'MPA{n}',True)+mos(300,150,f'MPB{n}',True)
    z+=t(64,134,a,16,'end')+t(264,134,b,16,'end')
    z+=w('M116 186 V230 H316 V186 M216 230 V274 M316 230 H385')+dot(216,230)+t(385,216,out,16,'end')
    z+=mos(200,310,f'MNA{n}')+t(164,294,a,16,'end')
    z+=w('M216 346 V414')+dot(216,385)+t(229,391,f'nx{n}',17)
    z+=mos(200,450,f'MNB{n}')+t(164,434,b,16,'end')+w('M216 486 V532')+ground(216,540)
    parts.append(f'<g transform="translate({x},{y+90})">{z}</g>')
all_names=set(recs[0] for recs in [line.split() for line in fa.lines])
drawn={name for g in fa.records for name in [f'MPA{g["id"]}',f'MPB{g["id"]}',f'MNA{g["id"]}',f'MNB{g["id"]}']}
assert drawn==all_names
save('digital_full_adder_all_44_mos',t(15,38,'Full-adder transistor schematic · all 44 MOSFETs',32,weight=500)+t(15,73,'Repeated node labels connect the panels. Bodies: NMOS → 0; PMOS → vdd.',21)+''.join(parts),1920,1940)
(OUT/'manifest.json').write_text(json.dumps({'source':'digital_netlist.py','sha256':hashlib.sha256((BASE/'digital_netlist.py').read_bytes()).hexdigest(),'full_adder_mos':44,'full_adder_nand_gates':11,'ripple_adder_2bit_mos':88,'unsigned_multiplier_2x2_mos':112,'full_adder_drawn_names_match_netlist':True,'full_network_transistor_netlist_exists':False,'output_nodes_2x2':P,'primitive_connectivity':fa.records},indent=2),encoding='utf-8')
print('Exported digital MLP overview, actual arithmetic schematics, and three exact primitive decks.')
