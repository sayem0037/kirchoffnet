"""
measure_existing.py -- hardware metrics for circuits that are already trained.

WHAT THIS IS FOR
----------------
kfabric/ has finished KFQ checkpoints that cost 23 to 86 minutes each to
produce. Nothing in them records energy, latency or area, because no code in
the repo ever computed those. This file adds the measurement WITHOUT retraining
anything: it reads a checkpoint, re-emits the identical netlist through that
arm's own writer at a measurement-grade time grid, and runs metrics.py over it.

The same function measures the crossbar arm, so the two columns are produced by
one code path and cannot drift apart.

THE LATENCY CAVEAT, HANDLED RATHER THAN BURIED
----------------------------------------------
Every netlist in this repo uses C = 0.1 fF on its internal nodes. With the
resistances in play that is a time constant around 1e-13 s, and the docstrings
say plainly that the node is settled long before the 100 ns readout. That is a
deliberate convenience for TRAINING -- it means the gradient never sees a
transient -- but a sub-picosecond settling time is not a publishable latency
figure for silicon, where any real node carries wire and fanout capacitance.

So latency is reported at a STATED load (tech.C_LOAD_DEFAULT, 10 fF) and the
full sweep over C is published next to it, so the scaling is visible instead of
assumed. The 0.1 fF number is reported too, labelled as the intrinsic limit.

ENERGY IS CHARGED OVER THE SETTLING WINDOW
------------------------------------------
Not over the 100 ns the training deck happens to run for. An architecture that
settles in 2 ns should not be billed for 100 ns of idle bias current just
because the trainer left the simulation running -- and one that settles slowly
should not escape being billed for it. Window = (0, t_settle), measured on the
same run.
"""

import argparse
import glob
import importlib.util
import json
import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
KFABRIC = os.path.join(os.path.dirname(BASE), "kfabric")
sys.path.insert(0, BASE)

import metrics                              # noqa: E402
import tech                                 # noqa: E402
import xbar_netlist as XB                   # noqa: E402
from simulator_api import run_metered, scratch   # noqa: E402

RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_kfq = _load("_netlist_kfq", os.path.join(KFABRIC, "netlist_kfq.py"))


# ================================================================= core ======
def measure_netlist(nl, read_nodes, cap_f, periphery=None, tol=0.02,
                    n_tau=60, supply="V0"):
    """Energy, latency, power and area for one written netlist.

    The time grid is chosen from the load: the interesting transient is a few
    RC, so the deck is retimed to resolve it with ~200 points and run out to
    n_tau times the nominal constant. Too coarse and the settling edge is a
    single sample; too fine and a 0.1 fF node needs a femtosecond step.
    """
    inv = metrics.device_inventory(nl)

    # Nominal time constant from the largest resistance actually in the deck
    # against the node load; generous, then measured properly from the waveform.
    r_ref = max([r for _, r in inv["res"]] or [1e5])
    tau = max(r_ref * cap_f, 1e-14)
    tstop = n_tau * tau
    tstep = tstop / 400.0

    res = run_metered(nl, read_nodes, tstep=tstep, tstop=tstop)
    t_set, per_node = metrics.settling_time(res, read_nodes, tol=tol)
    if not (t_set == t_set) or t_set <= 0:
        t_set = tstop

    e = metrics.energy_j(res, inv, t_window=(0.0, t_set))
    e_all = metrics.energy_j(res, inv)
    area = metrics.area_um2(inv, periphery)

    return dict(latency_s=t_set, tau_s=tau, energy=e, energy_full=e_all,
                area=area, devices=sum(inv["counts"].values()),
                counts=dict(inv["counts"]), per_node=per_node,
                window_tstop=tstop)


def _retune_caps(lines, cap_f):
    """Rewrite every node capacitor in a deck to the measurement load.

    Only the 0.1 fF node caps the writers emit are touched; any explicitly
    sized capacitor keeps its value. This is what makes the latency sweep a
    sweep of the LOAD rather than of the circuit.
    """
    out = []
    for ln in lines:
        t = ln.split()
        if t and t[0][0] in "Cc" and len(t) >= 4:
            out.append(f"{t[0]} {t[1]} {t[2]} {cap_f:.6e}")
        else:
            out.append(ln)
    return out


def write_with_cap(write_fn, cap_f, nl, **kw):
    """Emit a netlist through its own writer, then set the node load."""
    n = write_fn(path=nl, **kw)
    with open(nl) as f:
        lines = f.read().splitlines()
    with open(nl, "w") as f:
        f.write("\n".join(_retune_caps(lines, cap_f)) + "\n")
    return n


# ================================================================== arms =====
def measure_kfq(ck, cap_f, sample=0, tol=0.02):
    """Measure a trained KFQ checkpoint from kfabric/results/."""
    d = json.load(open(ck))
    layers = [tuple(t) for t in d["layers"]]
    cfg, th = d["cfg"], {k: float(v) for k, v in d["theta"].items()}

    # Whether this checkpoint has a bias row is a property of WHEN it was
    # trained, not a thing to assume: the iris pilot predates the bias row and
    # carries 100 parameters with no VA{l}_0_{j} entries, so writing its
    # netlist with bias=True raises KeyError on the first missing gate. Read it
    # off the checkpoint instead.
    bias = any(k.startswith("VA") and k.split("_")[1] == "0" for k in th)

    rng = np.random.default_rng(sample)
    xs = rng.uniform(-1, 1, layers[0][0])

    nl = scratch("meas_kfq")
    write_with_cap(_kfq.write_kfq_netlist, cap_f, nl, theta=th, xs=xs,
                   layers=layers, load_r=cfg["load_r"], rd=cfg["rd"],
                   vtail=cfg["vtail"], vcm=cfg["vcm"], swing=cfg["swing"],
                   bias=bias)
    # KFQ converts nothing: the class scores come straight off the last column
    # pair as voltages. That empty periphery is the architectural claim.
    out = measure_netlist(nl, _kfq.read_nodes(layers), cap_f, periphery={},
                          tol=tol)
    out.update(arm="kfq", dataset=d["dataset"], layers=layers, cap_f=cap_f,
               n_params=len(th), converters=dict(adc=0, dac=0))
    if os.path.exists(nl):
        os.remove(nl)
    return out


def measure_xbar(ck, cap_f, sample=0, tol=0.02, adc_bits=8, dac_bits=8):
    """Measure a crossbar checkpoint from compare/results/.

    The converters are charged here and nowhere else: one DAC per driven row
    and one ADC per read column, per layer, per inference.
    """
    import xbar_train as XT

    d = json.load(open(ck))
    layers = [tuple(t) for t in d["layers"]]
    cfg = d["cfg"]
    u = {k: float(v) for k, v in d["u"].items()}
    res_map = XT.u_to_res(u, cfg, d.get("levels"))

    rng = np.random.default_rng(sample)
    xs = rng.uniform(-1, 1, layers[0][0])

    nl = scratch("meas_xbar")
    write_with_cap(XB.write_xbar_netlist, cap_f, nl, res=res_map, xs=xs,
                   layers=layers, rf=cfg["rf"], rd=cfg["rd"],
                   vtail=cfg["vtail"], vref=cfg["vref"], vcm=cfg["vcm"],
                   swing=cfg["swing"], ideal_tia=cfg["ideal_tia"],
                   vota=cfg["vota"])

    conv = XB.converter_counts(layers)
    # Area is charged per converter INSTANCE (ADCs are time-multiplexed across
    # up to 128 columns); energy is charged per CONVERSION, below. These are
    # different numbers and using the conversion count for area overstated the
    # crossbar's footprint by 45%.
    periphery = {"adc": conv["adc_instances"] * tech.adc_area(adc_bits),
                 "dac": conv["dac_instances"] * tech.dac_area(dac_bits)}
    out = measure_netlist(nl, XB.read_nodes(layers), cap_f,
                          periphery=periphery, tol=tol)

    e_conv = (conv["adc"] * tech.adc_energy(adc_bits) +
              conv["dac"] * tech.dac_energy(dac_bits))
    out["energy"]["converters"] = e_conv
    out["energy"]["total_with_conv"] = out["energy"]["total"] + e_conv
    out.update(arm="xbar", dataset=d["dataset"], layers=layers, cap_f=cap_f,
               n_params=len(u), converters=conv,
               adc_bits=adc_bits, dac_bits=dac_bits)
    if os.path.exists(nl):
        os.remove(nl)
    return out


ARMS = dict(kfq=measure_kfq, xbar=measure_xbar)


def default_checkpoint(arm, dataset):
    pats = {"kfq": os.path.join(KFABRIC, "results", f"kfq_{dataset}_*.json"),
            "xbar": os.path.join(RESULTS, f"xbar_*_{dataset}_*.json")}
    hits = sorted(glob.glob(pats[arm]))
    return hits[0] if hits else None


# ================================================================== main =====
def main(a):
    ck = a.checkpoint or default_checkpoint(a.arm, a.dataset)
    if not ck or not os.path.exists(ck):
        print(f"no checkpoint for arm={a.arm} dataset={a.dataset}. "
              f"Train it first, or pass --checkpoint.")
        return 1

    caps = a.caps or [tech.C_LOAD_DEFAULT]
    print(f"{a.arm} | {os.path.basename(ck)}")
    print(f"  {'C_load':>9} {'latency':>11} {'energy':>12} {'power':>11} "
          f"{'area':>12}")

    rows = []
    for c in caps:
        r = ARMS[a.arm](ck, c, sample=a.sample, tol=a.tol)
        rows.append(r)
        e = r["energy"].get("total_with_conv", r["energy"]["total"])
        print(f"  {c * 1e15:7.2f} fF {r['latency_s'] * 1e9:9.4f} ns "
              f"{e * 1e12:10.3f} pJ {r['energy']['p_avg'] * 1e6:9.2f} uW "
              f"{r['area']['total']:10.1f} um^2")

    ref = rows[-1]
    print(f"\n  devices {ref['devices']}   params {ref['n_params']}   "
          f"converters {ref['converters']}")
    print("  area breakdown (um^2): " + "  ".join(
        f"{k}={v:.1f}" for k, v in sorted(ref["area"].items()) if k != "total"))

    p = os.path.join(RESULTS, f"hw_{a.arm}_{a.dataset}_{a.tag}.json")
    json.dump(dict(arm=a.arm, dataset=a.dataset, checkpoint=ck,
                   tech=tech.CARD, rows=rows), open(p, "w"), indent=2)
    print(f"\nsaved -> {p}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=list(ARMS), default="kfq")
    ap.add_argument("--dataset", default="iris")
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--caps", type=float, nargs="+", default=None,
                    help="load capacitances in F; default tech.C_LOAD_DEFAULT")
    ap.add_argument("--sweep", action="store_true",
                    help="use tech.C_LOAD_SWEEP")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--tol", type=float, default=0.02)
    ap.add_argument("--tag", default="run")
    a = ap.parse_args()
    if a.sweep and not a.caps:
        a.caps = list(tech.C_LOAD_SWEEP)
    sys.exit(main(a))
