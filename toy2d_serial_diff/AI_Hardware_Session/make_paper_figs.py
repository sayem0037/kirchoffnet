#!/usr/bin/env python3
"""Figures for the KirchhoffNet closed-ring IEEE paper, from the REAL committed data."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
import numpy as np, csv, os

SRC="/sessions/gracious-busy-knuth/mnt/toy2d_serial_diff"
OUT="/sessions/gracious-busy-knuth/mnt/outputs/paper3_figs"; os.makedirs(OUT,exist_ok=True)
DIG="#2f6fb0"; DIGL="#d6e6f5"; ANA="#e08a2b"; ANAL="#fbe6cd"; TEAL="#1b8a8a"; TEALL="#cdeceb"; GREY="#555"; INK="#222"; RED="#c0392b"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"savefig.dpi":200})

def box(ax,x,y,w,h,t,fc=DIGL,ec=DIG,fs=9,bold=False,tc=INK,r=0.02):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0.01,rounding_size={r}",fc=fc,ec=ec,lw=1.5))
    ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=fs,color=tc,fontweight="bold" if bold else "normal")
def arr(ax,p1,p2,c=GREY,lw=1.7,st="-|>",ls="-"):
    ax.add_patch(FancyArrowPatch(p1,p2,arrowstyle=st,mutation_scale=13,color=c,lw=lw,ls=ls,shrinkA=2,shrinkB=2))
def fin(ax,name,xl,yl,fig):
    ax.set_xlim(*xl);ax.set_ylim(*yl);ax.axis("off");fig.tight_layout()
    fig.savefig(f"{OUT}/{name}.png",bbox_inches="tight",facecolor="white");plt.close(fig);print("wrote",name)

# ---- Fig 1: system pipeline ----
fig,ax=plt.subplots(figsize=(11,3.1))
box(ax,0.2,1.0,1.7,1.3,"(x,y)\n2 features\nstandardized",fc="#eee",ec=GREY,fs=8.5)
box(ax,2.2,1.0,2.0,1.3,"Fixed linear\nencoder\n→ 10 .IC seeds\nh₁..h₁₀ @ t=0",fc=ANAL,ec=ANA,fs=8.2)
box(ax,4.5,0.7,2.5,1.9,"10-STAGE CLOSED\nDIFF-AMP RING\nevolve 0→100 ns\n(seed-then-evolve)\n30 params VTH/VB/VN",fc=DIGL,ec=DIG,fs=8.2,bold=True)
box(ax,7.3,1.0,2.0,1.3,"read h₁..h₁₀\n@100 ns →\nstandardize",fc=TEALL,ec=TEAL,fs=8.2)
box(ax,9.6,1.0,1.7,1.3,"softmax\nreadout\n10→2 → class",fc="#e7f3e7",ec=TEAL,fs=8.2)
for x in [1.9,4.2,7.0,9.3]: arr(ax,(x,1.65),(x+0.3,1.65),c=INK)
arr(ax,(5.75,2.6),(5.75,3.05),c=RED,lw=1.6,st="<|-")
ax.text(5.75,3.25,"per-stage VTH/VB/VN trained via 100 ns transient adjoint  dV(hⱼ,100ns)/d{·}",
        ha="center",fontsize=8,color=RED,style="italic")
fin(ax,"fig1_pipeline",(0,11.5),(0.5,3.5),fig)

# ---- Fig 2: one diff-amp stage (transistor level) ----
fig,ax=plt.subplots(figsize=(7,6))
# rails
ax.plot([0.5,6.5],[7.2,7.2],color=RED,lw=2); ax.text(6.6,7.2,"VDD=3.3V",color=RED,fontsize=9,va="center")
ax.plot([0.5,6.5],[0.5,0.5],color=INK,lw=2); ax.text(6.6,0.5,"GND",fontsize=9,va="center")
# PMOS loads
def mos(x,y,lbl,c):
    ax.add_patch(Rectangle((x-0.35,y-0.5),0.7,1.0,fc="white",ec=c,lw=1.8))
    ax.text(x,y,lbl,ha="center",va="center",fontsize=8,color=INK)
mos(2.2,6.0,"Mpd",ANA); mos(4.4,6.0,"Mps",ANA)
ax.plot([2.2,2.2],[7.2,6.5],color=INK,lw=1.4); ax.plot([4.4,4.4],[7.2,6.5],color=INK,lw=1.4)
ax.text(3.3,6.0,"th_j (VTH_j)",ha="center",fontsize=7.5,color=ANA)
ax.plot([2.55,4.05],[6.0,6.0],color=ANA,lw=1.2,ls=":")
# output node h_j
ax.plot([4.4,4.4],[5.5,4.7],color=INK,lw=1.4)
ax.add_patch(Circle((4.4,4.7),0.08,fc=TEAL,ec=TEAL)); ax.text(4.75,4.7,"h_j (OUT, 1pF cap, .IC-seeded)",fontsize=7.5,color=TEAL,va="center")
ax.plot([5.4,5.4],[4.7,0.9],color=TEAL,lw=1.2); ax.plot([4.4,5.4],[4.7,4.7],color=TEAL,lw=1.2)
ax.add_patch(Rectangle((5.25,2.3),0.3,0.7,fc="white",ec=TEAL,lw=1.4)); ax.text(6.0,2.65,"C_j=1pF",fontsize=7.5,color=TEAL)
# diff pair
mos(2.2,3.6,"Md",DIG); mos(4.4,3.6,"Ms",DIG)
ax.plot([2.2,2.2],[6.0,4.1],color=INK,lw=1.4); ax.plot([4.4,4.4],[6.0,4.1],color=INK,lw=1.4)
ax.annotate("vn_j (VN_j ref)",xy=(1.85,3.6),xytext=(0.2,3.9),fontsize=7.5,color=DIG,
            arrowprops=dict(arrowstyle="-|>",color=DIG,lw=1.2))
ax.annotate("h_{j-1} (prev stage out; signal in)",xy=(4.05,3.6),xytext=(3.0,2.9),fontsize=7.5,color=DIG,
            arrowprops=dict(arrowstyle="-|>",color=DIG,lw=1.2))
# tail
ax.plot([2.2,4.4],[3.1,3.1],color=INK,lw=1.4); ax.plot([3.3,3.3],[3.1,2.6],color=INK,lw=1.4)
mos(3.3,2.1,"Mt",TEAL); ax.plot([3.3,3.3],[1.6,0.5],color=INK,lw=1.4)
ax.annotate("vb_j (VB_j tail bias)",xy=(2.95,2.1),xytext=(0.2,1.6),fontsize=7.5,color=TEAL,
            arrowprops=dict(arrowstyle="-|>",color=TEAL,lw=1.2))
ax.text(3.5,7.6,"NMOS diff pair + PMOS active load + NMOS tail (Level-1 models)",ha="center",fontsize=8.5,color=INK,fontweight="bold")
fin(ax,"fig2_stage",(0,8.5),(0,8),fig)

# ---- Fig 3: closed ring topology ----
fig,ax=plt.subplots(figsize=(6.2,6.2))
N=10; R=2.4; cx,cy=3.1,3.1
pts=[(cx+R*np.cos(2*np.pi*k/N+np.pi/2), cy+R*np.sin(2*np.pi*k/N+np.pi/2)) for k in range(N)]
for k in range(N):
    x2,y2=pts[(k+1)%N]; x1,y1=pts[k]
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),arrowprops=dict(arrowstyle="-|>",color=DIG,lw=1.7,shrinkA=14,shrinkB=14))
for k,(x,y) in enumerate(pts):
    ax.add_patch(Circle((x,y),0.34,fc=DIGL,ec=DIG,lw=1.8,zorder=3))
    ax.text(x,y,f"h{k+1}",ha="center",va="center",fontsize=8.5,zorder=4)
ax.text(cx,cy,"CLOSED\nLOOP\nN=10\nstages",ha="center",va="center",fontsize=10,color=DIG,fontweight="bold")
ax.text(cx,cy-R-0.75,"stage 1 signal input = h₁₀  (loop closed)",ha="center",fontsize=8,color=RED,style="italic")
fin(ax,"fig3_ring",(0,6.2),(0,6.4),fig)

# ---- Fig 4: training curves from REAL logs ----
def load_log(name):
    ep,loss,tr,te=[],[],[],[]
    for r in csv.DictReader(open(f"{SRC}/results/{name}_ring_log.csv")):
        ep.append(int(r["epoch"]));loss.append(float(r["loss"]));tr.append(float(r["train_acc"]));te.append(float(r["test_acc"]))
    return ep,loss,tr,te
fig,axs=plt.subplots(1,3,figsize=(12,3.5))
for ax,(name,best) in zip(axs,[("twomoon","0.88"),("circle","1.00"),("2spirals","0.79")]):
    ep,loss,tr,te=load_log(name)
    ax2=ax.twinx()
    l1,=ax.plot(ep,tr,color=DIG,lw=1.6,label="train acc")
    l2,=ax.plot(ep,te,color=TEAL,lw=1.6,label="test acc")
    l3,=ax2.plot(ep,loss,color=RED,lw=1.3,ls="--",label="loss")
    ax.set_title(f"{name}  (best test={best})",fontsize=10,fontweight="bold")
    ax.set_xlabel("epoch");ax.set_ylim(0.3,1.03);ax.grid(alpha=0.3)
    ax2.set_ylabel("CE loss",color=RED,fontsize=8);ax2.tick_params(axis='y',colors=RED,labelsize=7)
    if ax is axs[0]:
        ax.set_ylabel("accuracy");ax.legend([l1,l2,l3],["train acc","test acc","loss"],fontsize=7,loc="center right")
fig.tight_layout();fig.savefig(f"{OUT}/fig4_curves.png",bbox_inches="tight",facecolor="white");plt.close(fig);print("wrote fig4_curves")

# ---- Fig 5: sensitivity heatmap from REAL csv (mean |dV/dparam| over samples) ----
rows=list(csv.DictReader(open(f"{SRC}/results/twomoon_ring_sensitivities.csv")))
nodes=[f"h{j}" for j in range(1,11)]
params=[f"VTH{j}" for j in range(1,11)]+[f"VB{j}" for j in range(1,11)]+[f"VN{j}" for j in range(1,11)]
M=np.zeros((10,30));C=np.zeros((10,30))
ni={n:i for i,n in enumerate(nodes)};pi={p:i for i,p in enumerate(params)}
for r in rows:
    i=ni[r["read_node"]];j=pi[r["param"]];M[i,j]+=abs(float(r["dVnode_dparam"]));C[i,j]+=1
M=M/np.maximum(C,1)
fig,ax=plt.subplots(figsize=(12,3.6))
im=ax.imshow(M,aspect="auto",cmap="viridis")
ax.set_yticks(range(10));ax.set_yticklabels(nodes,fontsize=7)
ax.set_xticks(range(30));ax.set_xticklabels(params,rotation=90,fontsize=6)
for x in [9.5,19.5]: ax.axvline(x,color="white",lw=1.5)
ax.text(4.5,-1.1,"VTH (PMOS load)",ha="center",fontsize=8,color=INK)
ax.text(14.5,-1.1,"VB (tail bias)",ha="center",fontsize=8,color=INK)
ax.text(24.5,-1.1,"VN (reference)",ha="center",fontsize=8,color=INK)
fig.colorbar(im,ax=ax,label="mean |dV(hⱼ,100ns)/dparam|  (40 samples)")
ax.set_title("Transient-adjoint sensitivity magnitudes — twomoon (10 read nodes × 30 circuit params)",fontsize=9.5,fontweight="bold")
fig.tight_layout();fig.savefig(f"{OUT}/fig5_sensitivity.png",bbox_inches="tight",facecolor="white");plt.close(fig);print("wrote fig5_sensitivity")
print("DONE")
