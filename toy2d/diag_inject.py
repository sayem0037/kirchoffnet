import numpy as np
from sklearn.linear_model import LogisticRegression
from netlist_writer import write_chain_netlist
from simulator_api import eval_chain
from dataset import load_dataset
from common import N_BLOCKS, CIRCUIT_INIT, READ

def enc(x, s, scheme):
    if scheme=="A":  # current: 2 refs
        return {"VIN":1.65,"VREF1":1.0+s*x[0],"VREF2":1.0+s*x[1],"VREF3":1.0,"VREF4":1.0}
    if scheme=="B":  # both features across all 4 refs
        return {"VIN":1.65,"VREF1":1.0+s*x[0],"VREF2":1.0+s*x[1],"VREF3":1.0+s*x[1],"VREF4":1.0+s*x[0]}
    if scheme=="C":  # drive VIN too (around midrail)
        return {"VIN":1.65+s*x[0],"VREF1":1.0+s*x[1],"VREF2":1.0+s*x[0],"VREF3":1.0+s*x[1],"VREF4":1.0+s*x[0]}

def state(X,s,scheme):
    S=[]
    for i in range(len(X)):
        write_chain_netlist(CIRCUIT_INIT, enc(X[i],s,scheme), "tmp_inj.sp", n_blocks=N_BLOCKS)
        v=eval_chain("tmp_inj.sp", READ); S.append([v[n] for n in READ])
    return np.array(S)

for name in ("twomoon","circle"):
    Xtr,ytr,Xte,yte=load_dataset(name)
    print(f"--- {name} (raw ceiling {LogisticRegression(max_iter=2000).fit(Xtr,ytr).score(Xtr,ytr):.2f}) ---")
    for scheme in ("A","B","C"):
        for s in (0.3,0.5,0.8):
            Str=state(Xtr,s,scheme); Ste=state(Xte,s,scheme)
            nd=[len(set(np.round(Str[:,j],2))) for j in range(4)]
            lr=LogisticRegression(max_iter=2000).fit(Str,ytr)
            print(f"  scheme {scheme} s={s}: state-sep train {lr.score(Str,ytr):.2f} test {lr.score(Ste,yte):.2f}  distinct{nd}")
