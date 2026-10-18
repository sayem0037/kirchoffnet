"""
xbar1t1r_device.py -- the programmable resistive device, as a software model.

WHY THERE IS NO DEVICE MODEL IN THE NETLIST
-------------------------------------------
The simulator has no memristor primitive and does not need one. During INFERENCE a
programmed cell is simply a resistor of a fixed value, and that is exactly what the
netlist writes. The device physics only governs what a WRITE does to that value --
which happens between samples, in software, in the training loop. Keeping the two
separate is also what the hardware does: the array is read with small voltages that do
not disturb it, and programmed with large pulses that do.

THE UPDATE RULE: MANHATTAN
--------------------------
Classical SGD asks for a weight change proportional to the gradient. Resistive hardware
cannot do that -- a programming pulse has a fixed amplitude and duration, and the
conductance change it produces is a property of the device, not of the number you wanted.

The Manhattan rule (Strukov and co-workers; demonstrated on silicon in Prezioso et al.,
Nature 2015, and extended to multilayer in Li et al., Nat. Comms 2018) accepts this: it
uses only the SIGN of the gradient and applies one fixed-amplitude SET or RESET pulse.
Everything about the magnitude is left to the device. That is the whole rule, and it is
why it is the standard in-situ scheme -- it needs no per-weight DAC, no multiplier, and
every cell in the array can be pulsed in parallel.

NONLINEARITY AND ASYMMETRY ARE THE POINT, NOT A DETAIL
------------------------------------------------------
A real cell does not move by the same amount every pulse. The conductance change shrinks
as the device approaches the rail it is being pushed towards, and the potentiation and
depression branches are not mirror images. Modelled here as

    potentiate:  dG = a_p * (1 - x) ,  x = (G - Gmin) / (Gmax - Gmin)
    depress:     dG = a_d * x

so a cell near Gmax barely potentiates and one near Gmin barely depresses. With a_p and
a_d unequal the array also has a systematic drift direction.

This is the dominant reason in-situ training does not look like software SGD, and it is
the thing the weight-trajectory plot exists to show. It must stay switched on by
default; turning it off produces prettier curves that describe no real device.
"""

import numpy as np


class ResistiveDevice:
    """One programmable-conductance technology, shared by every cell in the array.

    Conductances are held in SIEMENS throughout. The netlist writer converts to
    resistance at the last moment, because SPICE wants ohms and because a conductance
    of exactly zero is representable while a resistance of infinity is not.
    """

    def __init__(self, g_on=1e-4, g_off=1e-6, n_states=64,
                 a_pot=0.06, a_dep=0.05, nonlinear=True,
                 write_sigma=0.02, verify=False, verify_tol=0.002, seed=0):
        """
        g_on, g_off : the conductance window. 1e-4 / 1e-6 S is a 100:1 ratio, the
                      conventional figure for a multi-level resistive cell.
        n_states    : number of distinguishable programmed levels. Real devices are not
                      continuous; 64 levels is a 6-bit cell, which is at the optimistic
                      end of what is demonstrated.
        a_pot,a_dep : fixed-pulse step sizes, as a FRACTION of the window. Unequal on
                      purpose -- symmetric devices do not exist.
        nonlinear   : whether the step shrinks towards the rails. Default on.
        write_sigma : OPEN-LOOP programming error, as a fraction of the window. 2% is a
                      typical single-shot spread -- you apply a pulse and the cell lands
                      where it lands.
        verify      : enable closed-loop WRITE-VERIFY. The controller reads the cell
                      back and corrects until it is within `verify_tol` of target. This
                      is what Li et al. (Nat. Comms 2018) contribute and what every
                      accurate analog-weight programming scheme does.
        verify_tol  : residual error after verification, as a fraction of the window.

        WHY VERIFY MATTERS, MEASURED. Programming error turned out to be the single
        dominant limit on this network -- not quantisation, not the ADC, not the
        conductance range. Holding everything else fixed and sweeping it:

            residual error      twomoon        circle       2spirals
            2.0%  (open loop)   0.783          0.783         0.683
            0.5%                0.875          0.875         0.758
            0.2%  (verified)    0.992          1.000         0.742
            0%                  0.867          1.000         0.733

        Without write-verify this array cannot solve `circle` at all. With it, it solves
        it exactly. Reporting the open-loop number as "what a crossbar achieves" would
        have been reporting a hardware design nobody would build.
        """
        self.g_on, self.g_off = float(g_on), float(g_off)
        self.span = self.g_on - self.g_off
        self.n_states = int(n_states)
        self.a_pot, self.a_dep = float(a_pot), float(a_dep)
        self.nonlinear = bool(nonlinear)
        self.write_sigma = float(write_sigma)
        self.verify = bool(verify)
        self.verify_tol = float(verify_tol)
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------ helpers --
    def norm(self, g):
        """Conductance -> position in the window, 0 at Gmin and 1 at Gmax."""
        return (np.asarray(g, dtype=float) - self.g_off) / self.span

    def denorm(self, x):
        return self.g_off + np.asarray(x, dtype=float) * self.span

    def clip(self, g):
        return np.clip(g, self.g_off, self.g_on)

    def quantize(self, g):
        """Snap to the nearest programmable level."""
        if self.n_states is None or self.n_states < 2:
            return self.clip(g)
        x = np.clip(self.norm(g), 0.0, 1.0)
        q = np.round(x * (self.n_states - 1)) / (self.n_states - 1)
        return self.denorm(q)

    def level_step(self):
        """One programmable level, in siemens. The accumulator needs this: an update
        smaller than a level cannot be written, so it must be held in digital until it
        grows past one."""
        return self.span / max(self.n_states - 1, 1)

    def conductance_states(self):
        """Every level the device can hold, low to high."""
        return self.denorm(np.linspace(0.0, 1.0, self.n_states))

    # ------------------------------------------------------------------ the rule --
    def step_size(self, g, direction):
        """Conductance change one fixed-amplitude pulse would produce, in siemens.

        direction: +1 to potentiate (raise G), -1 to depress.
        """
        x = np.clip(self.norm(g), 0.0, 1.0)
        if direction > 0:
            frac = self.a_pot * (1.0 - x) if self.nonlinear else self.a_pot
        else:
            frac = self.a_dep * x if self.nonlinear else self.a_dep
        return frac * self.span

    def manhattan_update(self, g, grad_sign, lr_pulses=1.0):
        """Apply the Manhattan rule to a conductance array.

        grad_sign : sign of dLoss/dWeight. The weight must move OPPOSITE to it, so a
                    positive gradient depresses the cell.
        lr_pulses : how many pulses per update. Fractional values are allowed and are
                    the only "learning rate" this rule has -- the pulse amplitude itself
                    is fixed by the device, not by the optimiser.

        Returns the new conductance, quantized and clipped, with write error applied.
        """
        g = np.asarray(g, dtype=float)
        s = np.sign(np.asarray(grad_sign, dtype=float))
        direction = -s                        # descend the loss
        pulsed = direction != 0

        dg = np.where(direction > 0,
                      self.step_size(g, +1),
                      -self.step_size(g, -1))
        dg = dg * float(lr_pulses) * pulsed

        # A cell that receives NO pulse is not touched at all. It is not re-quantized
        # and it does not get fresh write error -- nothing happened to it.
        #
        # The first version ran every cell through write() unconditionally, so an
        # unpulsed cell still picked up write noise of 2% of the window on every single
        # step. That is a random walk over the whole array, and it got worse the more
        # cells a threshold spared: update thresholding, which should have stabilised
        # training, instead drove every dataset to a constant output (test exactly 0.500)
        # because the cells it protected were the ones being damaged.
        return np.where(pulsed, self.write(g + dg), g)

    def write(self, g_target):
        """Program a target conductance: clip, quantize, add write error.

        Every write goes through here. A programming operation that lands exactly on its
        target does not exist, and modelling one would make the array look better than
        any that has been built.
        """
        g = self.quantize(self.clip(g_target))
        sigma = self.verify_tol if self.verify else self.write_sigma
        if sigma > 0:
            g = g + self.rng.normal(0.0, sigma * self.span, np.shape(g))
        return self.clip(g)

    # ------------------------------------------------------- weight <-> hardware --
    def init_pair(self, shape, mode="mid", spread=0.1):
        """Initial (G_plus, G_minus) for a weight array.

        Both cells start near mid-window with a small spread. Not at a rail: a cell at
        Gmax cannot potentiate and one at Gmin cannot depress, so an array initialised
        at the rails has half its weights frozen on the first step.
        """
        x0 = 0.5 if mode == "mid" else float(mode)
        gp = self.denorm(np.clip(x0 + spread * self.rng.standard_normal(shape), 0.02, 0.98))
        gm = self.denorm(np.clip(x0 + spread * self.rng.standard_normal(shape), 0.02, 0.98))
        return self.write(gp), self.write(gm)

    def weight(self, gp, gm):
        """The signed weight a differential cell pair represents, normalised to ~[-1,1]."""
        return (np.asarray(gp) - np.asarray(gm)) / self.span

    def resistance(self, g):
        """Siemens -> ohms, for the netlist. Guarded so a zero conductance becomes a
        very large resistor rather than a division by zero."""
        return 1.0 / np.maximum(np.asarray(g, dtype=float), 1e-15)

    def describe(self):
        return dict(g_on=self.g_on, g_off=self.g_off, ratio=self.g_on / self.g_off,
                    n_states=self.n_states, a_pot=self.a_pot, a_dep=self.a_dep,
                    nonlinear=self.nonlinear, write_sigma=self.write_sigma,
                    verify=self.verify, verify_tol=self.verify_tol,
                    effective_sigma=(self.verify_tol if self.verify
                                     else self.write_sigma))


if __name__ == "__main__":
    d = ResistiveDevice(seed=0)
    print("device:", d.describe())
    print(f"  window {d.g_off:.2e} .. {d.g_on:.2e} S  "
          f"({d.n_states} levels, step {d.span/(d.n_states-1):.3e} S)")

    # How many pulses to cross the window, and what the nonlinearity costs.
    for nl in (False, True):
        d2 = ResistiveDevice(nonlinear=nl, write_sigma=0.0, n_states=1024, seed=0)
        g = np.array([d2.g_off])
        n = 0
        while g[0] < 0.9 * d2.g_on and n < 500:
            g = d2.manhattan_update(g, np.array([-1.0]))   # grad<0 -> potentiate
            n += 1
        print(f"  nonlinear={nl!s:<5} pulses from Gmin to 90% of Gmax: {n}")

    print("\n  potentiation step vs position in window (nonlinear model):")
    for x in (0.0, 0.25, 0.5, 0.75, 0.95):
        g = d.denorm(x)
        print(f"    x={x:4.2f}  dG_pot={d.step_size(g, +1):.3e} S   "
              f"dG_dep={d.step_size(g, -1):.3e} S")
