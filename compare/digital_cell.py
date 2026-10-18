"""
digital_cell.py -- the digital arm's energy and delay, characterised in THIS
simulator rather than quoted from a paper.

WHY NOT JUST CITE pJ/MAC
------------------------
The obvious way to get a digital baseline is to take a published energy-per-MAC
figure and multiply. That number would come from a different process, a
different supply and a different simulator than everything else in this study,
and the comparison would be an apples-to-oranges table with a citation on it.

So the digital datapath is characterised the same way the analog arms are: real
CMOS cells, the same solver, the same 0.35 um cards, the same 3.3 V. What is
NOT simulated is a whole MAC -- a few thousand devices over thousands of cycles
is beyond a pure-Python MNA solver. The split is:

    measured here        INV, NAND2, NOR2: energy and delay as functions of
                         load, from a fit over a load sweep
    composed here        AND2, XOR2, full adder, as networks of those
                         primitives
    counted in           how many of each an MLP inference needs
    digital_mlp.py

PRIMITIVES ARE SIMULATED, COMPOUNDS ARE COMPOSED -- AND WHY
-----------------------------------------------------------
The first version simulated the compound cells directly as multi-stage decks.
Every single-stage gate converged; every cascade failed at the FIRST transient
step, at any time step from 1 ps to 20 ps, under both TR and BE, with and
without explicit initial conditions. The reason is structural: the transient's
initial DC solve seeds nodes at mid-supply (transient_engine.py, a deliberate
choice for this project's bistable ring circuits), and mid-supply is precisely
where a chain of CMOS inverting stages has its maximum small-signal gain, so
Newton is being started at the worst point of a very stiff problem.

Composing from primitives sidesteps that, and is the better model anyway: it
forces the inter-stage load to be written down as an explicit input
capacitance rather than buried inside a deck. Every constant below is either
simulated or derived from the same model card the simulator uses.

LEVEL=2 IS MANDATORY HERE
-------------------------
Every analog netlist in this repo uses LEVEL=1, which has IS_DYNAMIC=False and
no intrinsic capacitance at all -- a LEVEL=1 inverter reports exactly zero
switching energy. LEVEL=2 is charge-conserving and carries gate overlap
(CGSO/CGDO/CGBO) and junction (CJ) capacitance. The simulator defaults all of
those to 0.0 ("Default 0 for purely ideal switching", models/defaults.py), so
the card below sets them explicitly. Gate D is what catches it if they are not.
"""

import argparse
import json
import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import metrics                                  # noqa: E402
import tech                                     # noqa: E402
from simulator_api import run_metered, scratch   # noqa: E402

RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)

VDD = tech.VDD

# 0.35 um cards, LEVEL=2. DC parameters match the LEVEL=1 NCH/PCH the analog
# arms use, so the two arms are built from the same transistor; the
# capacitance terms are what LEVEL=1 lacks and are set explicitly.
TOX = 7.5e-9
CGSO = CGDO = CGBO = 2.0e-10      # F/m of width (overlap)
CJ = 1.0e-3                       # F/m^2 (junction)
EPS_OX = 3.45e-11                 # F/m
COX = EPS_OX / TOX                # F/m^2

CAPS = (f"TOX={TOX:.3e} CGSO={CGSO:.3e} CGDO={CGDO:.3e} CGBO={CGBO:.3e} "
        f"CJ={CJ:.3e} PB=0.8 MJ=0.5 IS=1e-14")
NCH2 = (".MODEL NCH2 NMOS LEVEL=2 VTO=0.531 KP=120u GAMMA=0.4 PHI=0.7 "
        "LAMBDA=0.02 " + CAPS)
PCH2 = (".MODEL PCH2 PMOS LEVEL=2 VTO=-0.71 KP=40u GAMMA=0.4 PHI=0.7 "
        "LAMBDA=0.02 " + CAPS)

WN_M, WP_M, LG_M = 2e-6, 5e-6, 0.35e-6
WN, WP, LG = "2u", "5u", "0.35u"

C_INT = "0.1f"        # internal series-stack node; see note in deck_nand2
TR = 100e-12
PW = 2.0e-9
PER = 4.0e-9

PRIMITIVES = ("inv", "nand2", "nor2")


# ------------------------------------------------------------ cell decks ----
def _preamble(cload):
    return ["* digital cell characterisation -- LEVEL=2, dynamic",
            NCH2, PCH2, "", f"V0 vdd 0 DC {VDD}",
            f"CL out 0 {cload:.6e}", ""]


def _pulse(name, node):
    return (f"{name} {node} 0 PULSE(0.0 {VDD} 0 {TR:.3e} {TR:.3e} "
            f"{PW:.3e} {PER:.3e})")


def deck_inv(cload):
    return _preamble(cload) + [
        _pulse("VA", "a"), "",
        f"MN1 out a 0 0 NCH2 L={LG} W={WN}",
        f"MP1 out a vdd vdd PCH2 L={LG} W={WP}",
    ]


def deck_nand2(cload):
    return _preamble(cload) + [
        _pulse("VA", "a"), f"VB b 0 DC {VDD}", "",
        f"MN1 out a nx 0 NCH2 L={LG} W={WN}",
        f"MN2 nx b 0 0 NCH2 L={LG} W={WN}",
        f"MP1 out a vdd vdd PCH2 L={LG} W={WP}",
        f"MP2 out b vdd vdd PCH2 L={LG} W={WP}",
        # The internal stack node carries only junction capacitance in the
        # model and is otherwise high-impedance, which makes Newton struggle on
        # a fast edge. A real extraction gives it junction plus interconnect
        # capacitance anyway, so this is closer to silicon, not further.
        f"CX nx 0 {C_INT}",
    ]


def deck_nor2(cload):
    return _preamble(cload) + [
        _pulse("VA", "a"), "VB b 0 DC 0", "",
        f"MN1 out a 0 0 NCH2 L={LG} W={WN}",
        f"MN2 out b 0 0 NCH2 L={LG} W={WN}",
        f"MP1 px a vdd vdd PCH2 L={LG} W={WP}",
        # Bulk to vdd, NOT to the stacked source. Tying a PMOS bulk to ground
        # forward-biases its body diode: that version read 11.3 pJ per cycle
        # against the inverter's 0.17 pJ and a nan delay.
        f"MP2 out b px vdd PCH2 L={LG} W={WP}",
        f"CX px 0 {C_INT}",
    ]


DECKS = dict(inv=deck_inv, nand2=deck_nand2, nor2=deck_nor2)
DEVICES = dict(inv=2, nand2=4, nor2=4)

# Compound cells, as networks of primitives.
#   counts : every gate that switches, for energy
#   path   : the critical path, for delay
# XOR2 is 4 NAND2 with a 3-deep critical path; the full adder is two such XORs
# sharing their first NAND plus one more for the carry: 9 gates, 6 deep on the
# sum output, which is the path the accumulation tree waits on.
COMPOUND = dict(
    and2=dict(counts={"nand2": 1, "inv": 1}, path=["nand2", "inv"]),
    xor2=dict(counts={"nand2": 4}, path=["nand2"] * 3),
    fa=dict(counts={"nand2": 9}, path=["nand2"] * 6),
)


# -------------------------------------------------------- input capacitance --
def c_in(cell):
    """Input capacitance of one gate, from the same model card the simulator
    solves with: gate oxide over the driven devices plus their overlaps.

    Derived rather than simulated, but derived from the identical constants --
    so it cannot drift away from what the transistors in the deck actually are.
    """
    n_driven = {"inv": 1, "nand2": 1, "nor2": 1}[cell]   # per input
    c_ox = COX * (WN_M + WP_M) * LG_M
    c_ov = (CGSO + CGDO) * (WN_M + WP_M) + CGBO * LG_M
    return n_driven * (c_ox + c_ov)


# ---------------------------------------------------------- measurement -----
def characterise(cell, cload, tstep=5e-12, cycles=1.0):
    """Energy per switching cycle and propagation delay for one primitive.

    The window is one full period: one rising and one falling output edge. The
    supply delivers C*VDD^2 on the rise and (ideally) nothing on the fall, so
    the per-cycle figure is the honest unit to count with -- an inference
    toggles a node up and back down.

    Only the VDD source is charged. The input source's energy belongs to the
    gate DRIVING this one; counting it here would double-count it in a chain.
    """
    if cell not in DECKS:
        raise KeyError(f"{cell} is a compound cell -- use compose()")

    tstop = PER * cycles
    nl = scratch(f"dig_{cell}")

    res, last = None, None
    for dt in (tstep, tstep / 2.0, tstep / 5.0, tstep * 4.0, tstep * 10.0):
        lines = DECKS[cell](cload) + ["", f".TRAN {dt:.3e} {tstop:.3e}",
                                      "", ".END"]
        with open(nl, "w") as f:
            f.write("\n".join(lines) + "\n")
        try:
            res = run_metered(nl, ["a", "out", "vdd"])
            break
        except RuntimeError as exc:
            last = exc
    if res is None:
        if os.path.exists(nl):
            os.remove(nl)
        raise RuntimeError(f"{cell} @ C={cload:.3e} F did not converge at any "
                           f"time step: {last}")

    inv = metrics.device_inventory(nl)
    e = metrics.energy_j(res, inv, source_names=["V0"])

    t = np.asarray(res.sweep_axis, dtype=float)
    p = metrics.source_power(res, inv, ["V0"])[1]["V0"]
    leak_w = float(np.min(np.abs(p)))
    e_cycle = e["total"] - leak_w * float(t[-1] - t[0])

    d_r = metrics.prop_delay(res, "a", "out", VDD, rising_in=True)
    d_f = metrics.prop_delay(res, "a", "out", VDD, rising_in=False)
    delays = [d for d in (d_r, d_f) if d == d and d > 0]

    if os.path.exists(nl):
        os.remove(nl)

    return dict(cell=cell, cload=cload, devices=DEVICES[cell],
                e_cycle_j=e_cycle, leak_w=leak_w,
                t_pd_s=(float(np.mean(delays)) if delays else float("nan")))


def fit_cell(cell, loads=None, verbose=False):
    """Linear fits E(C) and t_pd(C) for one primitive.

    Both are straight lines in load capacitance to well within the accuracy
    this study needs: E = VDD^2*C + E_internal exactly in theory, and t_pd is
    linear in C for a fixed drive strength.
    """
    loads = loads or [1e-15, 5e-15, 10e-15, 20e-15, 50e-15]
    es, ts, cs = [], [], []
    for c in loads:
        r = characterise(cell, c)
        cs.append(c); es.append(r["e_cycle_j"]); ts.append(r["t_pd_s"])
        if verbose:
            print(f"    {c * 1e15:6.1f} fF  E={r['e_cycle_j'] * 1e15:8.3f} fJ  "
                  f"t={r['t_pd_s'] * 1e12:7.2f} ps")
    cs = np.array(cs)
    e_s, e_0 = np.polyfit(cs, np.array(es), 1)
    t_s, t_0 = np.polyfit(cs, np.array(ts), 1)
    return dict(cell=cell, devices=DEVICES[cell], c_in=c_in(cell),
                e_slope=float(e_s), e_int=float(e_0),
                t_slope=float(t_s), t_0=float(t_0),
                loads=[float(c) for c in cs],
                e_meas=[float(x) for x in es], t_meas=[float(x) for x in ts],
                area_um2=cell_area_um2(cell))


def energy_at(fit, cload):
    return fit["e_slope"] * cload + fit["e_int"]


def delay_at(fit, cload):
    return fit["t_slope"] * cload + fit["t_0"]


def compose(cell, cload, fits):
    """Energy, delay, devices and area of a compound cell.

    Energy sums every gate that switches, each charged at the load it actually
    drives: an internal gate drives one primitive input, the final gate drives
    the external load. Delay walks the critical path on the same basis.
    """
    if cell in fits:
        f = fits[cell]
        return dict(cell=cell, e_cycle_j=energy_at(f, cload),
                    t_pd_s=delay_at(f, cload), devices=f["devices"],
                    area_um2=f["area_um2"])

    spec = COMPOUND[cell]
    path = spec["path"]
    c_last = fits[path[-1]]["c_in"]

    e = 0.0
    for g, n in spec["counts"].items():
        # One gate in the network drives the external load; the rest drive one
        # primitive input each.
        e += energy_at(fits[g], cload)
        e += (n - 1) * energy_at(fits[g], c_last)

    t = 0.0
    for k, g in enumerate(path):
        load = cload if k == len(path) - 1 else fits[path[k + 1]]["c_in"]
        t += delay_at(fits[g], load)

    dev = sum(fits[g]["devices"] * n for g, n in spec["counts"].items())
    area = sum(fits[g]["area_um2"] * n for g, n in spec["counts"].items())
    return dict(cell=cell, e_cycle_j=e, t_pd_s=t, devices=dev, area_um2=area,
                composed_from=spec["counts"], path_depth=len(path))


def cell_area_um2(cell):
    """Drawn area of one primitive, through the same tech.py the analog arms
    use, so an analog um^2 and a digital um^2 mean the same thing."""
    n = DEVICES[cell]
    return (n / 2) * (tech.mos_area(WN_M, LG_M) + tech.mos_area(WP_M, LG_M)) * 1e12


# ---------------------------------------------------------------- Gate D ----
def gate_d(fits):
    """Gate D: switching energy must be real and must scale with load.

    E_cycle(C) must be a straight line in C with slope ~VDD^2 -- the supply
    delivers C*VDD^2 into the load each cycle on top of a constant internal
    term. A slope near zero means the capacitance model is inert and every
    digital energy number in the paper would be fiction.
    """
    print("=" * 72)
    print("Gate D -- digital cell switching energy is real and load-dependent")
    print("=" * 72)
    want = VDD ** 2
    ok_all = True
    for cell, f in fits.items():
        rel = abs(f["e_slope"] - want) / want
        ok = rel < 0.2
        ok_all &= ok
        print(f"\n  {cell}:")
        for c, e, t in zip(f["loads"], f["e_meas"], f["t_meas"]):
            print(f"    {c * 1e15:6.1f} fF  E={e * 1e15:8.3f} fJ  "
                  f"t={t * 1e12:7.2f} ps")
        print(f"    fit E = {f['e_slope']:.3f}*C + {f['e_int'] * 1e15:.2f} fJ")
        print(f"    [{'PASS' if ok else 'FAIL'}] slope {f['e_slope']:.3f} vs "
              f"VDD^2 = {want:.3f}  (rel err {rel * 100:.1f}%)")
    print("\n" + "=" * 72)
    print("Gate D " + ("PASSED -- LEVEL=2 capacitance is active."
                       if ok_all else
                       "FAILED -- energies are not load-dependent; the model "
                       "card is wrong and every digital number is fiction."))
    return 0 if ok_all else 1


def main(a):
    fits = {}
    print(f"characterising primitives at {tech.NODE_NM} nm, {VDD} V")
    for cell in PRIMITIVES:
        print(f"  {cell} ...")
        fits[cell] = fit_cell(cell, verbose=a.verbose)

    if a.gate:
        return gate_d(fits)

    cells = {}
    print(f"\ncells at C_load = {a.cload * 1e15:.1f} fF:")
    for cell in list(PRIMITIVES) + list(COMPOUND):
        r = compose(cell, a.cload, fits)
        r["c_in"] = fits[cell]["c_in"] if cell in fits else fits["nand2"]["c_in"]
        cells[cell] = r
        print(f"  {cell:<6} E={r['e_cycle_j'] * 1e15:9.3f} fJ/cycle   "
              f"t_pd={r['t_pd_s'] * 1e12:7.2f} ps   "
              f"{r['devices']:3d} dev   {r['area_um2']:8.2f} um^2")

    p = os.path.join(RESULTS, "digital_cell_char.json")
    json.dump(dict(vdd=VDD, node_nm=tech.NODE_NM, cload=a.cload,
                   wn=WN, wp=WP, lg=LG, fits=fits, cells=cells),
              open(p, "w"), indent=2)
    print(f"\nsaved -> {p}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cload", type=float, default=10e-15)
    ap.add_argument("--gate", action="store_true", help="run Gate D")
    ap.add_argument("--verbose", action="store_true")
    sys.exit(main(ap.parse_args()))
