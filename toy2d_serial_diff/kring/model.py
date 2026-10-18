"""KRingModel.predict(points): the complete pipeline, no training code, no machine paths."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import numpy as np

from .netlist import build_netlist
from .package import load_package
from .sim import simulate, fingerprint, sim_src_dir, spice_val

FAIL = -1


@dataclass
class Prediction:
    label: np.ndarray    # (n,) int, -1 where status != "ok"
    proba: np.ndarray    # (n, C) float, NaN rows where status != "ok"
    status: list         # per sample: ok | invalid_input | no_convergence | nonfinite | incomplete | error
    state: np.ndarray    # (n, N) raw final ring voltages (NaN on failure)

    @property
    def ok(self):
        return np.array([s == "ok" for s in self.status])


def _softmax(z):
    z = z - z.max(-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(-1, keepdims=True)


def _worker(args):
    pkg, x, sim_src = args
    return KRingModel(pkg, sim_src)._predict_one(x)


def _state_worker(args):
    pkg, x, sim_src, cv = args
    m = KRingModel(pkg, sim_src)
    r = simulate(m.netlist(x, circ_vec=cv), m.nodes, m.tstop, sim_src=sim_src)
    if r["status"] != "ok":
        return np.full(m.n, np.nan), r["status"]
    return np.array(r["v"]), "ok"


class KRingModel:
    def __init__(self, pkg, sim_src=None):
        self.pkg = pkg
        self.sim_src = sim_src_dir(sim_src)
        self.n = pkg["circuit"]["n_stages"]
        self.nodes = [f"h{j}" for j in range(1, self.n + 1)]
        e, p, r = pkg["encoder"], pkg["preprocessing"], pkg["readout"]
        self.in_mean, self.in_std = np.array(p["mean"]), np.array(p["std"])
        self.eW, self.eb = np.array(e["W"]), np.array(e["b"])
        self.mu, self.sd = np.array(r["state_mean"]), np.array(r["state_std"])
        self.Wout, self.bout = np.array(r["W"]), np.array(r["b"])
        self.sim = pkg["simulation"]
        self.tstop = spice_val(self.sim["tstop"])

    @classmethod
    def load(cls, path, sim_src=None, check_fingerprint=True):
        m = cls(load_package(path), sim_src)
        want = m.pkg["simulation"].get("simulator_fingerprint")
        if check_fingerprint and want and fingerprint(m.sim_src) != want:
            raise RuntimeError("simulator fingerprint differs from the one the package was "
                               "validated with; pass check_fingerprint=False to override")
        return m

    # ---- pipeline pieces (also used by validation / training) ----
    def encode(self, x):
        z = (np.asarray(x, float) - self.in_mean) / self.in_std
        e = self.pkg["encoder"]
        return np.clip(e["center"] + self.eW @ z + self.eb, e["vlo"], e["vhi"])

    def netlist(self, x, tstep=None, circ_vec=None, tstop=None, ic=None, **opts):
        """opts: chain / chain_in / mismatch, forwarded to build_netlist. ic overrides the encoded IC."""
        cv = self.pkg["circuit"]["params"] if circ_vec is None else circ_vec
        return build_netlist(self.pkg["circuit"], cv, self.encode(x) if ic is None else ic,
                             tstep or self.sim["tstep"], tstop or self.sim["tstop"], **opts)

    def readout(self, state):
        return _softmax(((np.asarray(state) - self.mu) / self.sd) @ self.Wout.T + self.bout)

    def _predict_one(self, x):
        C = len(self.pkg["classes"])
        bad = dict(label=FAIL, proba=np.full(C, np.nan), state=np.full(self.n, np.nan))
        x = np.asarray(x, float)
        if x.shape != self.in_mean.shape or not np.all(np.isfinite(x)):
            return dict(status="invalid_input", **bad)
        r = simulate(self.netlist(x), self.nodes, self.tstop, sim_src=self.sim_src)
        if r["status"] != "ok":
            return dict(status=r["status"], **bad)
        s = np.array(r["v"])
        p = self.readout(s)
        return dict(status="ok", label=int(p.argmax()), proba=p, state=s)

    def states(self, points, circ_vec=None, workers=1):
        """Raw final ring voltages for a batch (NaN rows + status on failure). Used by training
        and baselines; circ_vec overrides the packaged circuit parameters."""
        P = np.atleast_2d(np.asarray(points, float))
        jobs = [(self.pkg, x, self.sim_src, circ_vec) for x in P]
        if workers > 1:
            with ProcessPoolExecutor(workers) as ex:
                rows = list(ex.map(_state_worker, jobs, chunksize=2))
        else:
            rows = [_state_worker(j) for j in jobs]
        return np.array([r[0] for r in rows]), [r[1] for r in rows]

    def predict(self, points, workers=1):
        P = np.atleast_2d(np.asarray(points, float))
        if workers > 1:
            with ProcessPoolExecutor(workers) as ex:
                rows = list(ex.map(_worker, [(self.pkg, x, self.sim_src) for x in P]))
        else:
            rows = [self._predict_one(x) for x in P]
        return Prediction(label=np.array([r["label"] for r in rows]),
                          proba=np.array([r["proba"] for r in rows]),
                          status=[r["status"] for r in rows],
                          state=np.array([r["state"] for r in rows]))
