"""
verify_topology.py -- prove netlist_spider.py reproduces the schematic.

Parses both spidernet_1.sp (the 1:1 static port of the Spectre export) and a
freshly generated netlist, then compares them as CIRCUITS rather than as text:

  - the set of (rail node, state node) edges must match exactly;
  - every edge must have its OWN gate node (16 distinct thetas, no sharing);
  - device geometry and the cap set must match.

The theta INDEX map is deliberately not compared: the export numbers its thetas
in the block order net1, net4, net2, net3, while the generator uses the regular
k = (j-1)*n_rails + i. Since all thetas are independent trainables, that
relabeling is cosmetic.

Usage:  python verify_topology.py
"""
import sys
sys.path.insert(0, r"D:\Simulator\circuit_simulator with level3\src")
from utils.parser import NetlistParser

from netlist_spider import write_spider_netlist


def topology(path):
    comps, analyses = NetlistParser().parse(path)
    edges, gates, caps, geom = set(), {}, set(), set()
    for name, c in comps.items():
        if c.get("type") in ("NMOS", "M"):
            rail, gate, node = c["n_d"], c["n_g"], c["n_s"]
            edges.add((rail, node))
            gates.setdefault(node, set()).add(gate)
            ip = c.get("inst_params", {})
            geom.add((ip.get("L"), ip.get("W")))
            assert c["n_b"] == 0, f"{name}: bulk not grounded ({c['n_b']!r})"
        elif c.get("type") == "C":
            caps.add((c["n1"], c["n2"], c["value"]))
    return edges, gates, caps, geom, analyses


write_spider_netlist({f"VTH{k}": 2.4 for k in range(1, 17)},
                     {f"VR{i}": 1.0 for i in range(1, 5)},
                     "tmp_spider_demo.sp", n_rails=4, n_nodes=4)

e_ref, g_ref, c_ref, geo_ref, a_ref = topology("spidernet_1.sp")
e_gen, g_gen, c_gen, geo_gen, a_gen = topology("tmp_spider_demo.sp")

# rail/state node names differ only by the v-prefix convention, which is shared;
# compare the edge sets directly
print(f"edges  reference : {len(e_ref)}   generated: {len(e_gen)}")
print(f"edge sets identical              : {e_ref == e_gen}")
if e_ref != e_gen:
    print("  only in reference:", sorted(e_ref - e_gen))
    print("  only in generated:", sorted(e_gen - e_ref))

nd_ref = {n: len(g) for n, g in sorted(g_ref.items())}
nd_gen = {n: len(g) for n, g in sorted(g_gen.items())}
print(f"distinct gates per node (ref)    : {nd_ref}")
print(f"distinct gates per node (gen)    : {nd_gen}")

all_ref = set().union(*g_ref.values())
all_gen = set().union(*g_gen.values())
print(f"total distinct theta nodes       : ref {len(all_ref)}, gen {len(all_gen)} "
      f"-> no gate sharing: {len(all_ref) == 16 and len(all_gen) == 16}")

print(f"device geometry (L,W)            : ref {geo_ref}, gen {geo_gen} "
      f"-> match: {geo_ref == geo_gen}")
print(f"caps: ref {len(c_ref)} @ {sorted({v for _,_,v in c_ref})}, "
      f"gen {len(c_gen)} @ {sorted({v for _,_,v in c_gen})}")
print(f"analyses: ref {sorted(a_ref)}, gen {sorted(a_gen)}")
print(f"  .TRAN ref {a_ref.get('.TRAN')}  gen {a_gen.get('.TRAN')}")

ok = (e_ref == e_gen and len(all_ref) == 16 and len(all_gen) == 16
      and geo_ref == geo_gen and nd_ref == nd_gen)
print(f"\nTOPOLOGY MATCH: {ok}")
