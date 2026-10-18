"""
trainlog.py -- per-epoch logging of accuracy AND weights.

Nothing in this repo logs weight values per epoch to a flat file. The training scripts
log loss and accuracy; the only full-weight record is a best-so-far JSON checkpoint,
which is a single point rather than a trajectory, or `train_kfq.py --snapshots`, which
buries them in nested JSON. A weight-convergence plot needs the trajectory, so this
writes one.

Two files per run:

  <tag>_log.csv    epoch, loss, train_acc, test_acc, then ONE COLUMN PER WEIGHT.
                   Flushed every epoch, so a run that dies at epoch 14 still leaves 14
                   usable rows -- the pattern train_ring.py uses, for the same reason.
  <tag>_meta.json  config, device parameters, weight names, final state.

For the analog arm the logged values are MEASURED CONDUCTANCES in siemens, i.e. the
actual programmed state of the array, not a software shadow of it. That distinction is
the whole point of plotting them.
"""

import csv
import json
import os

import numpy as np


class TrainLog:
    """Streaming per-epoch logger. One instance per training run."""

    def __init__(self, path_stem, weight_names, meta=None, max_weight_cols=400,
                 resume=False):
        """
        path_stem    : "<dir>/<tag>" -- ".csv"/"_meta.json" are appended
        weight_names : ordered names, one per logged weight
        resume       : append to an existing log instead of starting a new one, keeping
                       its rows (used by a training run restarted from a checkpoint)
        max_weight_cols : a 64x64 array is 4096 columns and makes an unreadable CSV.
                          Past this, a reproducible evenly-spaced SUBSET is logged and
                          the chosen indices are recorded in the meta file, so the plot
                          and the data always agree on which weights those were.
        """
        self.stem = path_stem
        os.makedirs(os.path.dirname(os.path.abspath(path_stem)) or ".", exist_ok=True)

        names = list(weight_names)
        if len(names) > max_weight_cols:
            idx = np.linspace(0, len(names) - 1, max_weight_cols).astype(int)
            idx = np.unique(idx)
        else:
            idx = np.arange(len(names))
        self.idx = idx
        self.names = [names[i] for i in idx]
        self.all_names = names

        self.rows = []
        csv_path = f"{path_stem}_log.csv"
        if resume and os.path.exists(csv_path):
            ep, lo, tr, te, _, _ = load_log(path_stem)
            self.rows = [dict(epoch=int(e), loss=float(a), train=float(b), test=float(c))
                         for e, a, b, c in zip(ep, lo, tr, te)]
            self._f = open(csv_path, "a", newline="")
            self._w = csv.writer(self._f)
        else:
            self._f = open(csv_path, "w", newline="")
            self._w = csv.writer(self._f)
            self._w.writerow(["epoch", "loss", "train_acc", "test_acc"] + self.names)
            self._f.flush()

        self.meta = dict(meta or {})
        self.meta["weight_names"] = self.names
        self.meta["weight_indices"] = [int(i) for i in idx]
        self.meta["n_weights_total"] = len(names)
        self._save_meta()

    def log(self, epoch, loss, train_acc, test_acc, weights):
        """Record one epoch. `weights` is the full flat vector; it is subset here."""
        w = np.asarray(weights, dtype=float).ravel()
        if w.size != len(self.all_names):
            raise ValueError(f"got {w.size} weights, expected {len(self.all_names)}")
        row = [epoch, float(loss), float(train_acc), float(test_acc)] + \
              [float(v) for v in w[self.idx]]
        self._w.writerow(row)
        self._f.flush()
        self.rows.append(dict(epoch=epoch, loss=float(loss),
                              train=float(train_acc), test=float(test_acc)))

    def finish(self, **extra):
        self.meta["log"] = self.rows
        self.meta.update(extra)
        self._save_meta()
        self._f.close()
        return f"{self.stem}_log.csv"

    def _save_meta(self):
        with open(f"{self.stem}_meta.json", "w") as f:
            json.dump(self.meta, f, indent=2, default=_jsonable)


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def load_log(path_stem):
    """Read a run back: (epochs, loss, train, test, weight_matrix, names).

    weight_matrix is (n_epochs, n_logged_weights).
    """
    csv_path = f"{path_stem}_log.csv"
    with open(csv_path) as f:
        rd = csv.reader(f)
        head = next(rd)
        rows = [r for r in rd if r]
    names = head[4:]
    arr = np.array([[float(v) for v in r] for r in rows], dtype=float)
    if arr.size == 0:
        return (np.array([]),) * 4 + (np.zeros((0, len(names))), names)
    return (arr[:, 0].astype(int), arr[:, 1], arr[:, 2], arr[:, 3],
            arr[:, 4:], names)


def load_meta(path_stem):
    with open(f"{path_stem}_meta.json") as f:
        return json.load(f)
