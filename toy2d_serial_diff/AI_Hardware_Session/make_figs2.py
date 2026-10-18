#!/usr/bin/env python3
"""Batch 2 of diagrams."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle, Patch
import numpy as np, os

OUT = "/sessions/gracious-busy-knuth/mnt/outputs/figures"
DIG="#2f6fb0"; DIG_L="#d6e6f5"; ANA="#e08a2b"; ANA_L="#fbe6cd"
TEAL="#1b8a8a"; TEAL_L="#cdeceb"; GREY="#555555"; GREY_L="#e9e9e9"; RED="#c0392b"; INK="#222222"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"savefig.dpi":200,"figure.dpi":200})

def box(ax,x,y,w,h,text,fc=DIG_L,ec=DIG,tc=INK,fs=10,bold=False,rounded=0.02):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0.01,rounding_size={rounded}",fc=fc,ec=ec,lw=1.6))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,color=tc,fontweight="bold" if bold else "normal")
    return (x+w/2,y+h/2)
def arrow(ax,p1,p2,color=GREY,lw=1.8,style="-|>",ls="-"):
    ax.add_patch(FancyArrowPatch(p1,p2,arrowstyle=style,mutation_scale=14,color=color,lw=lw,linestyle=ls,shrinkA=2,shrinkB=2))
def finish(fig,ax,name,xlim=(0,10),ylim=(0,10),title=None):
    ax.set_xlim(*xlim);ax.set_ylim(*ylim);ax.axis("off")
    if title: ax.set_title(title,fontsize=13,fontweight="bold",color=INK,pad=8)
    fig.tight_layout();fig.savefig(f"{OUT}/{name}.png",bbox_inches="tight",facecolor="white");plt.close(fig);print("wrote",name)

# FIG 6 — near-memory dataflow (NorthPole style)
fig,ax=plt.subplots(figsize=(10,6.2))
ax.add_patch(FancyBboxPatch((0.6,0.8),8.8,7.2,boxstyle="round,pad=0.02,rounding_size=0.05",fc="#f4f8fc",ec=DIG,lw=2))
for r in range(4):
    for c in range(5):
        x=1.05+c*1.62;y=1.4+r*1.55
        box(ax,x,y,0.72,0.72,"MAC",fc=DIG_L,ec=DIG,fs=7.5)
        box(ax,x+0.78,y,0.62,0.72,"wt\nSRAM",fc="#e7f3e7",ec=TEAL,fs=6.5)
ax.text(5.0,8.35,"Weights distributed on-chip, interleaved with compute — NO off-chip weight fetch",
        ha="center",fontsize=9.5,color=DIG,fontweight="bold")
box(ax,0.6,-0.35,8.8,0.7,"Result: ~25× energy & ~5× area efficiency vs conventional (IBM NorthPole, digital near-memory)",
    fc="#fbfbe8",ec="#b3a600",fs=9)
finish(fig,ax,"fig06_nearmemory",xlim=(0,10),ylim=(-0.6,9),
       title="Figure 6. Digital near-memory dataflow ASIC: keep every weight beside its compute unit")

# FIG 7 — RRAM crossbar
fig,ax=plt.subplots(figsize=(9.5,7))
n=4
xs=[2.4+j*1.5 for j in range(n)]
ys=[6.4-i*1.3 for i in range(n)]
# horizontal wordlines (inputs)
for i,y in enumerate(ys):
    ax.plot([1.4,xs[-1]+0.6],[y,y],color=ANA,lw=2.2,zorder=1)
    arrow(ax,(0.7,y),(1.4,y),color=ANA,lw=2)
    ax.text(0.55,y,f"V{i+1}",ha="right",va="center",color=ANA,fontsize=10,fontweight="bold")
# vertical bitlines (outputs sum)
for j,x in enumerate(xs):
    ax.plot([x,x],[ys[-1]-1.1,ys[0]+0.4],color=TEAL,lw=2.2,zorder=1)
    arrow(ax,(x,ys[-1]-1.1),(x,ys[-1]-1.8),color=TEAL,lw=2)
    ax.text(x,ys[-1]-2.05,f"I{j+1}=ΣVᵢGᵢⱼ",ha="center",va="top",color=TEAL,fontsize=8.5,fontweight="bold")
# devices at crosspoints
for i,y in enumerate(ys):
    for j,x in enumerate(xs):
        ax.add_patch(Circle((x,y),0.18,fc=ANA_L,ec=ANA,lw=1.6,zorder=3))
        ax.text(x,y,"G",ha="center",va="center",fontsize=7.5,color=INK,zorder=4)
box(ax,5.9,5.2,3.2,1.4,"Ohm's law:  I = V·G  → MULTIPLY\nKCL:  currents sum on the wire → ADD\n⇒ full matrix-vector product in\nONE physical step, weights never move",
    fc="#fbfbe8",ec="#b3a600",fs=8.8)
ax.text(4.5,-1.15,"Devices: RRAM / memristor · PCM · SRAM-CIM   |   catch: device drift, noise, and ADC cost",
        ha="center",fontsize=8.8,color=GREY,style="italic")
finish(fig,ax,"fig07_crossbar",xlim=(0,9.5),ylim=(-1.5,7.2),
       title="Figure 7. Analog resistive crossbar: physics computes the MVM in place")

# FIG 8 — Photonic MZI mesh
fig,ax=plt.subplots(figsize=(10,6))
# inputs
for i in range(4):
    y=6.2-i*1.3
    arrow(ax,(0.5,y),(1.4,y),color=RED,lw=2.2)
    ax.text(0.35,y,f"in{i+1}",ha="right",va="center",color=RED,fontsize=9,fontweight="bold")
# MZI nodes as a triangular mesh
def mzi(ax,x,y):
    box(ax,x,y-0.35,0.9,0.7,"MZI\nφ",fc="#efe3f3",ec="#7b4b9e",fs=7.5)
positions=[(2.2,5.55),(2.2,2.95),(3.6,4.9),(3.6,3.6),(5.0,5.55),(5.0,2.95),(6.4,4.25)]
# beam lines
ys=[6.2,4.9,3.6,2.3]
for y in ys:
    ax.plot([1.4,8.6],[y,y],color="#c9b3dd",lw=1.2,zorder=0)
for (x,y) in positions: mzi(ax,x,y)
for i in range(4):
    y=6.2-i*1.3
    arrow(ax,(8.0,y),(8.9,y),color=TEAL,lw=2.2)
    ax.text(9.05,y,f"out{i+1}",ha="left",va="center",color=TEAL,fontsize=9,fontweight="bold")
box(ax,2.0,0.5,6.0,0.9,"A mesh of Mach-Zehnder interferometers = arbitrary linear transform (matrix multiply) at the SPEED OF LIGHT",
    fc="#fbfbe8",ec="#b3a600",fs=9)
finish(fig,ax,"fig08_photonic",xlim=(0,10),ylim=(0.2,7.2),
       title="Figure 8. Photonic accelerator: MZI mesh multiplies with light (phase shifts = weights)")

# FIG 9 — Neuromorphic spiking
fig,ax=plt.subplots(figsize=(10,6))
# cores mesh
for r in range(3):
    for c in range(4):
        x=0.7+c*1.35;y=3.9+r*1.15
        box(ax,x,y,1.05,0.95,"neuro-\ncore",fc=TEAL_L,ec=TEAL,fs=7.5)
ax.text(3.5,7.35,"Asynchronous mesh of neuro-cores (memory + compute co-located)",ha="center",
        fontsize=9.5,color=TEAL,fontweight="bold")
# spike train
t=np.linspace(0,6,600)
spike=np.zeros_like(t)
for s in [0.6,1.4,1.7,3.1,4.6,4.8,5.4]:
    spike+=np.exp(-((t-s)**2)/0.002)
ax.plot(1.0+t*1.15, 1.2+spike*0.9, color=RED, lw=1.6)
ax.axhline(1.2, xmin=0.09, xmax=0.87, color="#bbb", lw=0.8)
ax.text(4.5,0.55,"Event-driven 'spikes': a neuron does work ONLY when it fires → near-zero power when idle (sparse loads)",
        ha="center",fontsize=8.8,color=GREY,style="italic")
box(ax,6.6,4.3,3.1,2.2,"e.g. Intel Loihi 2\n~128 cores/chip,\n~1M neurons/chip\nHala Point: 1,152 chips\n→ 1.15B neurons",
    fc=GREY_L,ec=GREY,fs=8.8)
finish(fig,ax,"fig09_neuromorphic",xlim=(0,10),ylim=(0.2,7.7),
       title="Figure 9. Neuromorphic / spiking hardware: compute only on events")

# FIG 10 — KirchhoffNet
fig,ax=plt.subplots(figsize=(11,5.6))
# left: graph/circuit
ax.text(2.6,5.5,"(a) Circuit = directed graph",ha="center",fontsize=10.5,fontweight="bold",color=ANA)
nodes={ "n1":(1.2,4.2),"n2":(2.6,4.6),"n3":(3.9,4.0),"n4":(2.0,2.6),"n5":(3.5,2.4),"n0":(1.0,1.4)}
edges=[("n1","n2"),("n2","n3"),("n1","n4"),("n4","n5"),("n3","n5"),("n2","n4")]
for a,b in edges:
    x1,y1=nodes[a];x2,y2=nodes[b]
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),arrowprops=dict(arrowstyle="-|>",color=ANA,lw=1.8))
for k,(x,y) in nodes.items():
    c = "#dddddd" if k=="n0" else ANA_L
    ax.add_patch(Circle((x,y),0.32,fc=c,ec=ANA if k!="n0" else GREY,lw=1.8,zorder=3))
    ax.text(x,y,("gnd" if k=="n0" else k),ha="center",va="center",fontsize=7.5,zorder=4)
# fixed caps to ground (dashed)
for k in ["n1","n2","n3","n4","n5"]:
    x,y=nodes[k]
    ax.plot([x,1.0],[y,1.4],color=GREY,lw=0.9,ls=":",zorder=0)
ax.text(2.6,0.7,"node voltage = neuron state · edge device = learnable weight",
        ha="center",fontsize=8,color=GREY,style="italic")
# right: ODE evolution
ax.text(8.0,5.5,"(b) Output = circuit state after time evolution",ha="center",fontsize=10.5,fontweight="bold",color=TEAL)
tt=np.linspace(0,1,200)
rng=np.random.default_rng(3)
for i in range(6):
    v0=rng.uniform(-1,1); target=rng.uniform(-1,1)
    v=v0+(target-v0)*(3*tt**2-2*tt**3)+0.04*np.sin(6*tt)*(1-tt)
    ax.plot(5.9+tt*3.6, 3.2+v*0.9, lw=1.7)
ax.axvline(5.9,color="#bbb",lw=0.8,ls="--");ax.axvline(9.5,color="#bbb",lw=0.8,ls="--")
ax.text(5.9,1.55,"t=0\ninput = v(0)",ha="center",fontsize=8,color=ANA)
ax.text(9.5,1.55,"t=1\noutput = v(1)",ha="center",fontsize=8,color=TEAL)
ax.text(7.7,0.75,"dv/dt = f(v,θ)  — a Neural ODE, trained by the ADJOINT method\n(adjoint system = a circuit of the SAME topology)",
        ha="center",fontsize=8.2,color=INK)
finish(fig,ax,"fig10_kirchhoffnet",xlim=(0,10.6),ylim=(0.3,6),
       title="Figure 10. KirchhoffNet: the network IS a circuit; computation is its evolution under Kirchhoff's current law")

# FIG 11 — Digital flow
fig,ax=plt.subplots(figsize=(11.5,3.4))
steps=[("Spec &\narchitecture","what to build",DIG_L),
       ("RTL design\n(Verilog/VHDL)","behavior",DIG_L),
       ("Functional\nverification","prove it",DIG_L),
       ("Logic\nsynthesis","→ gates",DIG_L),
       ("Place &\nroute","→ geometry",DIG_L),
       ("Signoff →\nGDSII (tape-out)","→ foundry","#cddcea")]
x=0.2;w=1.75
for i,(t,sub,fc) in enumerate(steps):
    cx,cy=box(ax,x,1.1,w,1.4,t,fc=fc,ec=DIG,fs=8.8,bold=True)
    ax.text(cx,0.75,sub,ha="center",fontsize=7.5,color=GREY,style="italic")
    if i<len(steps)-1: arrow(ax,(x+w,1.8),(x+w+0.35,1.8),color=DIG,lw=2)
    x+=w+0.35
ax.text(6.1,2.85,"FPGA off-ramp: run the same RTL on an FPGA — real hardware for the price of a dev board",
        ha="center",fontsize=8.5,color=TEAL,style="italic")
finish(fig,ax,"fig11_digital_flow",xlim=(0,12.6),ylim=(0.4,3.2),
       title="Figure 11. Designing a digital AI chip from scratch: RTL → GDSII")

# FIG 12 — Analog flow
fig,ax=plt.subplots(figsize=(11.5,3.4))
steps=[("Spec\n(I-V, gain,\nnoise)","targets",ANA_L),
       ("Pick process\n+ PDK\n(e.g. 350nm)","device models",ANA_L),
       ("Schematic\ndesign","transistors",ANA_L),
       ("SPICE sim\n+ sensitivity\n(adjoint)","the gradient","#fbdca6"),
       ("Layout\n(matching,\nparasitics)","geometry",ANA_L),
       ("Extract, DRC/\nLVS → tape-out","→ foundry","#fbdca6")]
x=0.2;w=1.8
for i,(t,sub,fc) in enumerate(steps):
    cx,cy=box(ax,x,1.1,w,1.5,t,fc=fc,ec=ANA,fs=8.2,bold=True)
    ax.text(cx,0.72,sub,ha="center",fontsize=7.3,color=GREY,style="italic")
    if i<len(steps)-1: arrow(ax,(x+w,1.85),(x+w+0.3,1.85),color=ANA,lw=2)
    x+=w+0.3
ax.text(6.2,2.95,"No logic synthesis exists for analog — YOU are responsible for correctness; SPICE is the only oracle",
        ha="center",fontsize=8.5,color=RED,style="italic")
finish(fig,ax,"fig12_analog_flow",xlim=(0,12.9),ylim=(0.4,3.3),
       title="Figure 12. Designing an analog / mixed-signal AI chip: schematic → SPICE → layout")

# FIG 13 — positioning scatter
fig,ax=plt.subplots(figsize=(10,6.6))
ax.axis("on")
data=[("GPU",9.2,6.5,DIG,900),("TPU/systolic",6.5,8.0,DIG,700),("FPGA",7.5,5.2,DIG,500),
      ("Near-mem ASIC\n(NorthPole)",3.2,8.8,DIG,500),("RRAM/PCM\ncrossbar",2.6,9.2,ANA,500),
      ("Photonic",2.2,8.4,ANA,450),("Neuromorphic\n(Loihi 2)",4.2,8.6,ANA,450),
      ("KirchhoffNet",1.7,9.3,RED,520)]
for name,flex,eff,c,s in data:
    ax.scatter(flex,eff,s=s,c=c,alpha=0.5,edgecolors=c,linewidths=1.8,zorder=3)
    ax.text(flex,eff-0.02,name,ha="center",va="center",fontsize=8.2,fontweight="bold",zorder=4)
ax.set_xlabel("Flexibility / programmability  →",fontsize=11,fontweight="bold")
ax.set_ylabel("Energy efficiency (potential)  →",fontsize=11,fontweight="bold")
ax.set_xlim(0,10);ax.set_ylim(4,10.2)
ax.grid(True,ls=":",alpha=0.5)
ax.text(8.6,4.4,"maturity ↑ toward the right",fontsize=8.5,color=GREY,style="italic",ha="right")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(fc=DIG,alpha=0.5,label="Digital"),Patch(fc=ANA,alpha=0.5,label="Analog/emerging"),
                   Patch(fc=RED,alpha=0.5,label="KirchhoffNet")],loc="lower left",fontsize=9,frameon=True)
ax.set_title("Figure 13. Positioning: efficiency vs. flexibility (bubble size ≈ design difficulty)",
             fontsize=12.5,fontweight="bold",pad=10)
fig.tight_layout();fig.savefig(f"{OUT}/fig13_positioning.png",bbox_inches="tight",facecolor="white");plt.close(fig);print("wrote fig13")
print("BATCH 2 DONE")
