"""Netlist generation for the closed diff-amp ring, driven entirely by package contents."""
from kring.sim import spice_val


def _scale_w(card, k):
    """Scale the W= field of a device card string such as 'NCH L=650n W=6u' by factor k."""
    out = []
    for tok in card.split():
        if tok.upper().startswith("W="):
            w = spice_val(tok[2:]) * k
            tok = f"W={w * 1e6:.6g}u"
        out.append(tok)
    return " ".join(out)


def build_netlist(circuit, circ_vec, ic_seeds, tstep, tstop, chain=False, chain_in=1.65, mismatch=None):
    """circuit  : package['circuit'] (topology, models, supply, caps, device cards)
    circ_vec : flat list [VTH1..N, VB1..N, VN1..N]
    ic_seeds : list of N initial voltages for h1..hN
    chain    : open the loop - stage 1 senses a fixed DC source (chain_in volts) instead of h_N
    mismatch : {instance name, e.g. 'Md3': relative W scale factor}"""
    if circuit["topology"] != "diffamp_ring_v1":
        raise ValueError(f"unsupported topology {circuit['topology']!r}")
    n = circuit["n_stages"]
    th, vb, vn = circ_vec[:n], circ_vec[n:2 * n], circ_vec[2 * n:3 * n]
    d = circuit["devices"]
    mm = mismatch or {}
    L = ["* kring ring netlist (auto-generated)"] + list(circuit["models"])
    L.append(f"V0 vdd 0 DC {circuit['vdd']!r}")
    for j in range(1, n + 1):
        L.append(f"VTH{j} th{j} 0 DC {float(th[j-1])!r}")
        L.append(f"VB{j} vb{j} 0 DC {float(vb[j-1])!r}")
        L.append(f"VN{j} vn{j} 0 DC {float(vn[j-1])!r}")
    if chain:
        L.append(f"VCIN hin 0 DC {float(chain_in)!r}")

    def card(name, key):
        return _scale_w(d[key], mm[name]) if name in mm else d[key]
    for j in range(1, n + 1):
        vp = ("hin" if chain else f"h{n}") if j == 1 else f"h{j-1}"
        L += [
            f"Md{j}  dm{j} vn{j} tl{j} 0   {card(f'Md{j}', 'md')}",
            f"Ms{j}  h{j}  {vp}  tl{j} 0   {card(f'Ms{j}', 'ms')}",
            f"Mt{j}  tl{j} vb{j} 0    0   {card(f'Mt{j}', 'mt')}",
            f"Mpd{j} dm{j} th{j} vdd  vdd {card(f'Mpd{j}', 'mpd')}",
            f"Mps{j} h{j}  th{j} vdd  vdd {card(f'Mps{j}', 'mps')}",
            f"C{j} h{j} 0 {circuit['cap']}",
        ]
    L.append(".IC " + " ".join(f"V(h{j})={float(ic_seeds[j-1]):.6f}" for j in range(1, n + 1)))
    L += [f".TRAN {tstep} {tstop}", ".END"]
    return "\n".join(L) + "\n"
