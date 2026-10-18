"""
tech.py -- the technology card. One file, one node, one set of constants.

Every number in the paper's Area and Energy columns traces back to a constant
here. Nothing downstream is allowed to hard-code a device dimension, a sheet
resistance or a pJ figure: if a reviewer disputes a number, there is exactly
one place to change it and re-run.

WHY 350 nm. The circuits were not invented for this comparison -- they already
exist, and their geometries pin the node. kfabric/netlist_kfq.py sizes synapses
at L=1u/W=4u and pairs at L=1u/W=8u; toy2d/netlist_wide.py uses L=650n and
L=2u; toy2d_spidernet/ is a direct port of a Cadence cell from library
"Neur_Sam_350" with L=350n. VDD is 3.3 V everywhere. That is a 0.35 um process,
so the card is 0.35 um. Re-targeting to a modern node would mean re-sizing
every circuit, which is a different paper.

PROVENANCE. Each constant carries a `src` tag:
    "geom"  -- fixed by the netlists already in this repo
    "proc"  -- typical 0.35 um foundry value; order-of-magnitude, stated openly
    "lit"   -- taken from published work, cited in the string
No constant is silently invented. The `proc` and `lit` entries are the ones a
reviewer may argue with, and they are deliberately few.
"""

# ---------------------------------------------------------------- supply ----
VDD = 3.3                 # V      src=geom  (every netlist in the repo)
NODE_NM = 350             # nm     src=geom
L_MIN = 0.35e-6           # m      src=geom

# ------------------------------------------------------------ transistor ----
# First-order drawn area of one MOSFET:
#     A = (W + 2*GATE_ENC) * (L + 2*SD_EXT)
# SD_EXT is the source/drain diffusion run on each side of the gate (contact +
# enclosure + spacing), taken as 3 * L_MIN, which is the usual minimum-pitch
# figure. GATE_ENC is poly-over-active enclosure on the width edges.
GATE_ENC = 0.30e-6        # m      src=proc
SD_EXT = 3.0 * L_MIN      # m      src=proc  (1.05 um each side)

# ------------------------------------------------------------- resistors ----
# The crossbar weights are conductances. In a 0.35 um process the realistic
# vehicle for a kOhm-to-MOhm passive weight is a high-resistance poly module,
# not silicided poly (~5 Ohm/sq), which would need absurd length.
#     A = n_squares * W_RES^2,   n_squares = R / R_SHEET_POLY
R_SHEET_POLY = 1.0e3      # ohm/sq  src=proc  (hi-res poly module)
W_RES = 1.0e-6            # m       src=proc  (min resistor width)

# ------------------------------------------------------------ capacitors ----
C_DENSITY = 1.0e-15 / 1e-12   # F/m^2  src=proc  (1 fF/um^2 MIM)

# --------------------------------------------------------------- storage ----
# Weight/activation storage for the digital arm. Area is a 6T bitcell; access
# energy is per bit read out of the array including its decode and bitline
# swing. This is the one digital number NOT characterised in-simulator -- an
# SRAM macro is not a cell -- so it is flagged as literature and kept separate
# in the reported breakdown.
A_SRAM_BITCELL = 36.0e-12     # m^2    src=proc  (6T @ 0.35 um)
E_SRAM_READ_BIT = 0.5e-12     # J/bit  src=lit   Horowitz, ISSCC 2014 digest,
                              #        scaled to 0.35 um / 3.3 V

# -------------------------------------------------------------- converters --
# ADCs dominate every published analog-crossbar energy budget, which is exactly
# why the crossbar arm must carry them and the KFQ arm must not. Walden form:
#     E_conv = FOM * 2^bits
# so the cost doubles per bit. Area is a flat per-instance figure.
FOM_ADC = 100e-15         # J/conv-step  src=lit  Murmann ADC survey, 0.35 um era
FOM_DAC = 20e-15          # J/conv-step  src=lit  (DACs are the cheaper side)
A_ADC_8B = 20000e-12      # m^2  src=lit  8-bit SAR @ 0.35 um
A_DAC_8B = 2000e-12       # m^2  src=lit

# ------------------------------------------------------------- load model ----
# The netlists in this repo all use C=0.1f, which gives tau ~ 1e-13 s. That is
# a numerical convenience, not a load: it makes the node settle long before the
# 100 ns readout so training never sees a transient. It is NOT a defensible
# latency figure, so latency is reported at a stated realistic load instead and
# the sweep is published alongside it.
C_LOAD_DEFAULT = 10e-15   # F  src=proc  (10 fF: a short local wire + fanout)
C_LOAD_SWEEP = [0.1e-15, 1e-15, 10e-15, 100e-15]


# =========================================================================
# Area helpers -- every arm's area column goes through these three functions.
# =========================================================================
def mos_area(w_m, l_m):
    """Drawn area of one MOSFET, in m^2."""
    return (w_m + 2.0 * GATE_ENC) * (l_m + 2.0 * SD_EXT)


def res_area(r_ohm):
    """Area of one poly resistor of the given value, in m^2."""
    if r_ohm <= 0.0:
        return 0.0
    return (r_ohm / R_SHEET_POLY) * (W_RES ** 2)


def cap_area(c_f):
    """Area of one MIM capacitor of the given value, in m^2."""
    if c_f <= 0.0:
        return 0.0
    return c_f / C_DENSITY


def adc_energy(bits):
    """Energy of one analog-to-digital conversion, in J."""
    return FOM_ADC * (2.0 ** bits)


def dac_energy(bits):
    """Energy of one digital-to-analog conversion, in J."""
    return FOM_DAC * (2.0 ** bits)


def adc_area(bits):
    """Area of one ADC instance, in m^2 (scaled off the 8-bit reference)."""
    return A_ADC_8B * (2.0 ** (bits - 8)) ** 0.5


def dac_area(bits):
    """Area of one DAC instance, in m^2."""
    return A_DAC_8B * (2.0 ** (bits - 8)) ** 0.5


CARD = dict(node_nm=NODE_NM, vdd=VDD, l_min=L_MIN, gate_enc=GATE_ENC,
            sd_ext=SD_EXT, r_sheet_poly=R_SHEET_POLY, w_res=W_RES,
            c_density=C_DENSITY, a_sram_bitcell=A_SRAM_BITCELL,
            e_sram_read_bit=E_SRAM_READ_BIT, fom_adc=FOM_ADC,
            fom_dac=FOM_DAC, a_adc_8b=A_ADC_8B, a_dac_8b=A_DAC_8B,
            c_load_default=C_LOAD_DEFAULT)

if __name__ == "__main__":
    print(f"technology card: {NODE_NM} nm, VDD = {VDD} V")
    print(f"  one KFQ synapse NMOS (W=4u, L=1u) : "
          f"{mos_area(4e-6, 1e-6)*1e12:8.2f} um^2")
    print(f"  one 20k load resistor             : "
          f"{res_area(20e3)*1e12:8.2f} um^2")
    print(f"  one 0.1 fF node cap               : "
          f"{cap_area(0.1e-15)*1e12:8.4f} um^2")
    print(f"  one 8-bit ADC conversion          : {adc_energy(8)*1e12:8.2f} pJ")
    print(f"  one 8-bit DAC conversion          : {dac_energy(8)*1e12:8.2f} pJ")
