"""Prepare small datasets for the circuit classifier.

Each point has two coordinates and a label: 0 or 1.
load_dataset() creates points, scales them, and picks 40 training + 24 test points.
"""

import numpy as np
from sklearn.datasets import make_moons, make_circles
from sklearn.preprocessing import StandardScaler

N_PER_CLASS_TRAIN = 20
N_PER_CLASS_TEST = 12
SEED = 42
DATASETS = ("twomoon", "circle", "2spirals")


def _make_spirals(n):
    """Create one spiral labeled 0 and its mirror image labeled 1."""
    rng = np.random.default_rng(SEED)
    points_per_spiral = n // 2

    # As the angle grows, the distance from the center also grows.
    angle = np.sqrt(rng.random((points_per_spiral, 1))) * 540 * (2 * np.pi) / 360
    x = -np.cos(angle) * angle + rng.random((points_per_spiral, 1)) * 0.5
    y = np.sin(angle) * angle + rng.random((points_per_spiral, 1)) * 0.5

    first_spiral = np.hstack((x, y))
    second_spiral = -first_spiral
    points = np.vstack((first_spiral, second_spiral)) / 3.0
    points += rng.standard_normal(points.shape) * 0.1

    labels = np.concatenate([
        np.zeros(points_per_spiral, dtype=int),
        np.ones(points_per_spiral, dtype=int),
    ])
    return points, labels


def _raw(name, n=4096):
    """Create unscaled points and their class labels."""
    if name == "twomoon":
        return make_moons(n_samples=n, noise=0.1, random_state=SEED)
    if name == "circle":
        return make_circles(n_samples=n, noise=0.06, factor=0.5, random_state=SEED)
    if name == "2spirals":
        return _make_spirals(n)
    raise ValueError(f"unknown dataset {name!r}; choose from {DATASETS}")


def load_dataset(name="twomoon"):
    """Return training points, training labels, test points, and test labels.

    Points are rows of [x, y] coordinates. Labels are 0 or 1.
    """
    # 1. Create the chosen dataset.
    points, labels = _raw(name)

    # 2. Scale each coordinate: (value - average) / standard deviation.
    # Keep the original scaling so existing experiment results stay reproducible.
    # For new evaluations, fit and save a scaler using only the training points.
    points = StandardScaler().fit_transform(points)

    # 3. Pick equal numbers of class 0 and class 1 points.
    rng = np.random.default_rng(SEED)
    train_indices = []
    test_indices = []
    train_end = N_PER_CLASS_TRAIN
    test_end = train_end + N_PER_CLASS_TEST

    for class_label in (0, 1):
        class_indices = np.where(labels == class_label)[0]
        rng.shuffle(class_indices)
        train_indices.extend(class_indices[:train_end])
        test_indices.extend(class_indices[train_end:test_end])

    # 4. Mix the classes within each group.
    train_indices = np.array(train_indices)
    test_indices = np.array(test_indices)
    rng.shuffle(train_indices)
    rng.shuffle(test_indices)

    # 5. Return the four arrays expected by the training scripts.
    train_points = points[train_indices]
    train_labels = labels[train_indices].astype(np.int64)
    test_points = points[test_indices]
    test_labels = labels[test_indices].astype(np.int64)
    return train_points, train_labels, test_points, test_labels


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="twomoon", choices=DATASETS)
    args = parser.parse_args()

    train_points, train_labels, test_points, test_labels = load_dataset(args.dataset)
    print(f"Dataset: {args.dataset}")
    print(f"Training: {len(train_points)} points; class counts: {np.bincount(train_labels)}")
    print(f"Test: {len(test_points)} points; class counts: {np.bincount(test_labels)}")

    x = train_points[:, 0]
    y = train_points[:, 1]
    print(f"Training coordinate ranges: x [{x.min():.2f}, {x.max():.2f}], "
          f"y [{y.min():.2f}, {y.max():.2f}]")
