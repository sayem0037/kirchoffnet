"""Shared circuit config + 2-feature encoder for the toy2d scripts."""
import numpy as np
from netlist_writer import theta_names, vbias_names, input_source_names, output_nodes

N_BLOCKS = 4
CIRCUIT_INIT = {**{n: 1.7 for n in theta_names(N_BLOCKS)},
                **{n: 0.8 for n in vbias_names(N_BLOCKS)}}
CIRC_NAMES = theta_names(N_BLOCKS) + vbias_names(N_BLOCKS)
INPUT_SRCS = input_source_names(N_BLOCKS)
READ = output_nodes(N_BLOCKS)
ALL_SENS = CIRC_NAMES + INPUT_SRCS
BOUNDS = [(0.0, 3.0)] * len(theta_names(N_BLOCKS)) + [(0.72, 1.10)] * len(vbias_names(N_BLOCKS))


ENC_SWING = 0.5   # chosen by diag_inject.py sweep


def encode(x):
    """2 features driven across VIN + all references ("scheme C") so both features
    strongly drive every stage -> all read-nodes analog and all params live.
    (diag_inject.py: this lifts twomoon circuit-state separability to the raw
    0.93 ceiling with 4/4 analog nodes.)"""
    s = ENC_SWING
    return {"VIN":   1.65 + s * float(x[0]),
            "VREF1": 1.0 + s * float(x[1]),
            "VREF2": 1.0 + s * float(x[0]),
            "VREF3": 1.0 + s * float(x[1]),
            "VREF4": 1.0 + s * float(x[0])}
