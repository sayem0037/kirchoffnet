"""
dataset.py -- Breast Cancer Wisconsin, reduced to 3 features for the chain.

Outputs STANDARDIZED PCA-3 features (zero mean, unit variance) -- the trainable
software encoder maps these to circuit input-source voltages, so we do NOT
pre-scale to a voltage range here (the encoder learns that mapping).

  load_breast_cancer(): 569 samples, 30 features, y in {0=malignant, 1=benign}.
  -> standardize 30 features -> PCA to 3 -> standardize the 3 components.
  -> class-balanced train/test split.
"""

import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

N_PER_CLASS_TRAIN = 15
N_PER_CLASS_TEST  = 8
SEED = 42


def load_dataset():
    """
    Returns (X_train, y_train, X_test, y_test):
      X_* : (N, 3) standardized PCA features
      y_* : (N,)   integer labels {0, 1}
    """
    data = load_breast_cancer()
    X, y = data.data, data.target

    X_pca = PCA(n_components=3, random_state=SEED).fit_transform(
        StandardScaler().fit_transform(X))
    X_std = StandardScaler().fit_transform(X_pca)   # standardize the 3 components

    rng = np.random.default_rng(SEED)
    tr, te = [], []
    for cls in (0, 1):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        tr.extend(idx[:N_PER_CLASS_TRAIN])
        te.extend(idx[N_PER_CLASS_TRAIN:N_PER_CLASS_TRAIN + N_PER_CLASS_TEST])
    tr = np.array(tr); te = np.array(te)
    rng.shuffle(tr); rng.shuffle(te)

    return (X_std[tr], y[tr].astype(np.int64),
            X_std[te], y[te].astype(np.int64))


if __name__ == "__main__":
    Xtr, ytr, Xte, yte = load_dataset()
    print(f"train {Xtr.shape} ({np.bincount(ytr)}), test {Xte.shape} ({np.bincount(yte)})")
    print("feature means/std (train):", Xtr.mean(0).round(2), Xtr.std(0).round(2))
