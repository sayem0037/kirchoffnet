"""Model package = ONE json file holding everything needed for inference (floats round-trip exactly)."""
import json

FORMAT_VERSION = "kring-1"
REQUIRED = ["format_version", "classes", "preprocessing", "encoder", "circuit",
            "simulation", "readout", "provenance"]


def _check(pkg):
    if pkg.get("format_version") != FORMAT_VERSION:
        raise ValueError(f"unsupported format {pkg.get('format_version')!r}, expected {FORMAT_VERSION}")
    missing = [k for k in REQUIRED if k not in pkg]
    if missing:
        raise ValueError(f"package missing sections: {missing}")


def save_package(pkg, path):
    _check(pkg)
    with open(path, "w") as f:
        json.dump(pkg, f, indent=1)


def load_package(path):
    with open(path) as f:
        pkg = json.load(f)
    _check(pkg)
    return pkg
