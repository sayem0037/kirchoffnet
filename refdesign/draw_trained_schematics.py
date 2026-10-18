"""Draw deterministic transistor schematics from the exported trained SPICE decks.

Outputs: all six full-layer SVG schematics, and slide-size L1 output-pair-1 SVGs.
Repeated net labels denote electrical connections. Bulk pins use conventional ties.
No simulator or image-generation model is used.
"""
from pathlib import Path
from html import escape
import re
import json
import hashlib

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'netlists' / 'trained'
OUT = BASE / 'figs' / 'trained_schematics'
OUT.mkdir(parents=True, exist_ok=True)
INK, POS, NEG, CONTROL = '#172c42', '#166da0', '#b34e17', '#5f488c'

def label(x, y, value, size=18, anchor='start', color=INK, weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{color}" font-weight="{weight}">{escape(str(value))}</text>'

def wire(d, color=INK):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'

def dot(x, y):
    return f'<circle cx="{x}" cy="{y}" r="3.5" fill="{INK}"/>'

def ground(x, y):
    return wire(f'M{x} {y-8} V{y} M{x-12} {y} H{x+12} M{x-8} {y+6} H{x+8} M{x-4} {y+12} H{x+4}')

def mos(x, y, name, p=False, color=INK):
    s = wire(f'M{x+16} {y-36} V{y-18} H{x} M{x} {y-18} V{y-9} M{x} {y-4} V{y+4} M{x} {y+9} V{y+18} H{x+16} V{y+36} M{x-12} {y-22} V{y+22}', color)
    s += wire(f'M{x-36} {y} H{x-(21 if p else 12)}', color)
    if p:
        s += f'<circle cx="{x-17}" cy="{y}" r="4" fill="white" stroke="{color}" stroke-width="2"/>'
    return s + label(x+28, y-4, name, 17, color=color)

def resistor(x, y, name, value, color=INK):
    s = wire(f'M{x} {y} v8 l-7 5 l14 7 l-14 7 l14 7 l-14 7 l7 5 V{y+60}', color)
    return s + label(x-15, y+23, name, 17, 'end', color) + label(x-15, y+45, f'{float(value)/1000:.4g} kΩ', 18, 'end', color)

def source(x, y, name, value):
    s = f'<circle cx="{x}" cy="{y}" r="18" fill="white" stroke="{INK}" stroke-width="2"/>'
    s += label(x, y-3, '+', 16, 'middle') + label(x, y+13, '−', 16, 'middle')
    return s

def parse(path):
    components = {}
    for line in path.read_text().splitlines():
        tokens = line.split()
        if tokens and tokens[0][0].upper() in 'MRCV' and not tokens[0].startswith('*'):
            components[tokens[0]] = tokens
    return components

def assert_term(c, name, terminals):
    assert c[name][1:1+len(terminals)] == terminals, (name, c[name], terminals)

def tia(c, j, side):
    tag = f'{side}{j}'
    col = f'c{"p" if side=="P" else "n"}{j}'
    output = f'o{"p" if side=="P" else "n"}{j}'
    tail = f's{"p" if side=="P" else "n"}{j}'
    names = [f'MP{tag}1', f'MP{tag}2', f'MN{tag}1', f'MN{tag}2', f'MT{tag}', f'MP{tag}3', f'MN{tag}3']
    expected = [[tag+'_m',tag+'_m','vdd','vdd'],[tag+'_o1',tag+'_m','vdd','vdd'],[tag+'_m',col,tail,'0'],[tag+'_o1','vref',tail,'0'],[tail,'g_vota','0','0'],[output,tag+'_o1','vdd','vdd'],[output,'g_vota','0','0']]
    for name, pins in zip(names, expected):
        assert_term(c,name,pins)
    rf = f'RF{side}{j}'
    cap = f'C{side}{j}'
    assert_term(c,rf,[output,col]); assert_term(c,cap,[col,'0'])
    s = label(10,20,f'{col} → {output} · seven-transistor TIA',24,weight=500)
    s += label(280,55,'vdd',18,'middle') + wire('M116 70 H446 M116 70 V94 M286 70 V94 M446 70 V94') + dot(286,70)
    s += mos(100,130,names[0],True) + mos(270,130,names[1],True) + mos(430,130,names[5],True)
    s += wire('M116 166 V244 M286 166 V244 M446 166 V364')
    s += wire('M64 130 V210 H116 M64 130 V86 H234 V130') + dot(116,210) + dot(64,130)
    s += label(122,228,tag+'_m',16)
    s += wire('M286 200 H352 V130 H394') + dot(286,200) + label(310,191,tag+'_o1',16)
    s += mos(100,280,names[2]) + mos(270,280,names[3])
    s += wire('M20 280 H64') + label(20,264,col,19,color=POS if side=='P' else NEG)
    s += label(229,263,'vref',18,'end')
    s += wire('M116 316 V350 H286 V316 M200 350 V368') + dot(200,350) + label(208,345,tail,16)
    s += mos(184,404,names[4]) + wire('M200 440 V482') + ground(200,490)
    s += label(144,385,'g_vota',18,'end')
    s += mos(430,400,names[6]) + wire('M446 436 V482') + ground(446,490)
    s += label(390,381,'g_vota',18,'end')
    s += wire('M446 240 H535 V575 H340 M292 575 H20 V280') + dot(446,240)
    s += label(532,227,output,20,'end',POS if side=='P' else NEG)
    s += wire('M292 575 l6 -7 l9 14 l9 -14 l9 14 l9 -14 l6 7')
    s += label(315,550,f'{rf} · {float(c[rf][3])/1000:g} kΩ',19,'middle')
    s += wire('M20 575 H55 V608 M43 608 H67 M43 619 H67 M55 619 V647') + dot(20,575) + ground(55,655)
    s += label(75,618,f'{cap} · {c[cap][3].replace("f", " fF")}',18)
    return s, set(names + [rf,cap])

def pair(c, j, rows, heading, source_name):
    height = max(1080,180+rows*260+80)
    s = label(40,58,heading,36,weight=500)
    s += label(40,95,source_name,21)
    s += label(40,136,'1T1R branches · trained resistance values (rounded)',24,weight=500)
    included=set()
    for i in range(1,rows+1):
        y=160+(i-1)*260
        s += f'<g transform="translate(0,{y})">'
        row, wl = f'r{i}', f'wl{i}'
        for name in [f'VR{i}',f'VWL{i}']:
            assert_term(c,name,[row if name.startswith('VR') else wl,'0'])
            included.add(name)
        s += wire('M65 47 V20 H496 M246 20 V59 M496 20 V59') + dot(246,20)
        s += label(145,10,f'{row}'+(' · bias' if i==1 else ''),18)
        s += source(65,65,f'VR{i}',c[f'VR{i}'][4]) + wire('M65 83 V187') + ground(65,195)
        s += label(15,107,f'VR{i}',17) + label(15,128,f'{float(c[f"VR{i}"][4]):.6f} V',16)
        s += wire('M105 132 V45 H444 M194 45 V95 M444 45 V95') + dot(194,45)
        s += label(120,37,wl,17,color=CONTROL)
        s += source(105,150,f'VWL{i}',c[f'VWL{i}'][4]) + wire('M105 168 V187') + ground(105,195)
        s += label(127,210,f'VWL{i}',17) + label(127,232,f'{float(c[f"VWL{i}"][4]):g} V',17)
        for x, side, prefix, color in [(230,'P','p',POS),(480,'N','n',NEG)]:
            mn=f'MS{side}{i}_{j}'; rn=f'RC{side}{i}_{j}'
            internal=f'n{"p" if side=="P" else "m"}{i}_{j}'; col=f'c{prefix}{j}'
            assert_term(c,mn,[row,wl,internal,'0']); assert_term(c,rn,[internal,col])
            included.update([mn,rn])
            s += mos(x,95,mn,color=color) + wire(f'M{x+16} 131 V145',color)
            s += resistor(x+16,145,rn,c[rn][3],color) + wire(f'M{x+16} 205 V217',color)
            s += label(x+16,239,col,18,'middle',color)
        s += '</g>'
    for x,side in [(700,'P'),(1290,'N')]:
        amp, names=tia(c,j,side);included.update(names)
        s += f'<g transform="translate({x},160)">{amp}</g>'
    note_y = height-104
    s += label(700,890,f'Readout: V(op{j}) − V(on{j})',25,weight=500)
    s += label(700,925,'Differencing / ADC are outside these SPICE decks.',20)
    s += label(40,note_y,'Shared supplies: V0 → vdd = 3.3 V   ·   VREF → vref = 1.0 V   ·   VOTA → g_vota = 0.8 V',20)
    s += label(40,note_y+34,'Repeated net labels are connected. NMOS bulk = 0; PMOS bulk = vdd. Selector W/L = 20/1 µm.',19)
    s += label(40,note_y+67,'Actual exported read circuit: ideal input sources; no decoder or programming-driver circuits added.',19)
    return s,height,included

def svg_document(content,w,h,title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="Arial, Helvetica, sans-serif"><title>{escape(title)}</title><rect width="{w}" height="{h}" fill="white"/>{content}</svg>'

manifest=[]
for path in sorted(SOURCE.glob('*.sp')):
    c=parse(path)
    for supply,node,value in [('V0','vdd',3.3),('VREF','vref',1.0),('VOTA','g_vota',0.8)]:
        assert_term(c,supply,[node,'0'])
        assert float(c[supply][4])==value
    rows=sum(bool(re.fullmatch(r'VR\d+',name)) for name in c)
    pairs=max(int(re.fullmatch(r'RFP(\d+)',name)[1]) for name in c if re.fullmatch(r'RFP(\d+)',name))
    dataset=path.stem.split('_')[1]; layer=path.stem.split('_')[2]
    included=set(['V0','VREF','VOTA']);groups=[]
    columns=4 if pairs>4 else 2
    ph=max(1080,180+rows*260+80)
    for j in range(1,pairs+1):
        s,h,names=pair(c,j,rows,f'Trained {dataset} · {layer} · output pair {j}',path.name)
        included.update(names)
        gx=((j-1)%columns)*1920;gy=((j-1)//columns)*ph
        groups.append(f'<g transform="translate({gx},{gy})">{s}</g>')
        if j==1 and layer=='L1':
            slide=OUT/f'{path.stem}_pair1_slide.svg'
            # Explicitly disclose that this is one pair, not the full layer.
            s=s.replace(escape(path.name),escape(f'{path.name} · 3 rows × 16 output pairs · pair 1 expanded; pairs 2–16 repeat this topology'))
            slide.write_text(svg_document(s,1920,h,f'{path.stem} output pair 1'),encoding='utf-8')
    assert included==set(c),{'missing':sorted(set(c)-included),'extra':sorted(included-set(c))}
    full=OUT/f'{path.stem}_full.svg'
    full.write_text(svg_document(''.join(groups),1920*min(columns,pairs),ph*((pairs+columns-1)//columns),path.stem+' full transistor schematic'),encoding='utf-8')
    manifest.append({'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':rows,'output_pairs':pairs,'mos':sum(n.startswith('M') for n in c),'resistors':sum(n.startswith('R') for n in c),'capacitors':sum(n.startswith('C') for n in c),'voltage_sources':sum(n.startswith('V') for n in c),'covered_components':len(included),'all_components_covered':True,'full_schematic':str(full)})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
