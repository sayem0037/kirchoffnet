# Peer-Review Report and Author Response

**Manuscript:** *Hardware-in-the-Loop Training of a Closed-Loop Analog Differential-Amplifier Ring as a KirchhoffNet Classifier via a Transient-Adjoint Gradient*

**Reviewer:** Reviewer #2 (Associate Editor's senior reviewer; ~25 years in analog/mixed-signal IC design, EDA sensitivity analysis, and, more recently, analog compute for ML).

**Recommendation on first read:** Major revision. The manuscript is honest and technically sound in its core mechanism, and the closed-loop, `.IC`-seeded formulation is a genuinely faithful transistor-level realization of the KirchhoffNet idea — that is its strength and the reason I am not recommending rejection. However, as first submitted the paper risked being read as claiming an analog classifier trained by a circuit adjoint achieves the reported accuracies, when the evidence points elsewhere. My concerns below must be addressed before the contribution can be stated defensibly. The revised manuscript (v2) addresses them; my confirmations are noted inline.

---

## Summary of the submission

The authors instantiate KirchhoffNet [7] as a ring of ten CMOS differential-amplifier stages, closed on itself, in a real SPICE simulator with a backward transient-adjoint sensitivity engine. Data enter as initial conditions on the ring's storage nodes; the ring evolves 100 ns; the same nodes are read and classified by a linear soft-max read-out. Thirty per-stage bias parameters are trained through the adjoint. Reported test accuracies on twomoon/circle/2spirals are 0.88/1.00/0.79.

The idea is sound and the honesty of the write-up is above the norm for this area. My job is to ensure the claims match the evidence and that the experimental rigor meets *Transactions* standard.

---

## Major concerns

**M1 — Attribution of performance (the central issue).** The Results section presents 0.88/1.00/0.79 without, at first, quantifying how much of this comes from the *circuit* versus the *linear read-out*. In analog-ML papers this is the single most common overclaim. If the trained circuit parameters barely move, the paper is really reporting the performance of a linear read-out on a fixed random nonlinear reservoir, which is a very different (and much older) contribution. The authors must report the parameter displacement and a frozen-vs-trained ablation *in the main text*, and must state the attribution in the abstract.

> **Author response (resolved).** We agree; this was our own foremost concern. The abstract now states plainly that "a co-trained linear read-out supplies most of this accuracy." Section VIII-A reports the parameter displacement (third-decimal, e.g. VTH₁ 1.7000→1.7008) and adds **Table III**, an explicit frozen-vs-trained ablation over a shared read-out, showing the trained ring is within noise of the frozen ring. The contribution is reframed throughout as *methodological* — that the parameters are trainable and the loop is stable — not as an accuracy result. *Reviewer: confirmed; this is now stated correctly and prominently.*

**M2 — Missing baselines.** A reader cannot judge 0.88/1.00/0.79 without a linear baseline and a sense of task difficulty. Please give the raw-feature linear-classifier numbers and note where a trivial MLP lands, so the tasks' easiness is explicit and the ring's contribution is contextualized.

> **Author response (resolved).** Section VII-A now labels the "raw features" column of Table I as exactly a logistic-regression baseline and adds the calibration that a small two-layer MLP separates all three tasks at or near 1.00, so the benchmarks are explicitly framed as easy and the comparison as controlled (frozen vs. trained pipeline) rather than a hard-benchmark result. *Reviewer: confirmed.*

**M3 — Statistical rigor.** Forty training / twenty-four test samples and a single seed cannot support point accuracies to two decimals without error bars. Either add multiple seeds/splits with variance, or explicitly downgrade the numbers to "indicative" and remove any language implying statistical significance.

> **Author response (partially resolved, honestly scoped).** Because each sample is a full circuit solve, a multi-seed study was outside this study's compute budget; rather than fabricate variance we have explicitly downgraded all accuracies to "indicative," stated the single-seed/no-error-bar limitation in both Section VI and Section VIII-C, and removed significance-implying language. *Reviewer: acceptable for a methodological note of this scope, given the explicit disclosure; I would require the multi-seed study for a full-length paper.*

**M4 — Adjoint-gradient validation.** The entire training signal is the simulator's transient adjoint. For a *Transactions* audience the adjoint should be validated against finite-difference perturbation on at least a few parameters, to rule out a systematic gradient error masked by the read-out's ability to compensate.

> **Author response (acknowledged, deferred).** We have added this as named future work in Section VIII-C and note that the smoke test currently validates only non-degeneracy (finite, non-zero, banded sensitivities; Fig. 5), not numerical agreement with finite differences. We agree this is the most important missing validation and do not claim gradient correctness beyond internal consistency. *Reviewer: the honest disclosure is acceptable; I have flagged it to the editor as a condition for any stronger claim.*

**M5 — Degeneracy claim needs to be shown, not asserted.** The paper mentions a checkpoint that "logged perfect accuracy but was degenerate." This is actually one of the more interesting findings and must be documented concretely (how many points re-converged, what the guard changed), or removed.

> **Author response (resolved).** Section VIII-B now documents it concretely: the circle checkpoint re-converged on ~15/64 points despite a logged-perfect accuracy; the cause (loss-only acceptance admitting non-convergent steps because failed samples are skipped) is explained; and the convergence term in Eq. (6) — retain ≥95% convergent train samples — is shown to resolve it, with 2spirals remaining 64/64. *Reviewer: confirmed; this is now a genuine contribution rather than an aside.*

**M6 — Hardware framing vs. absence of energy/latency.** The title and motivation invoke hardware efficiency, yet no energy or latency is measured. Either measure/estimate an end-to-end figure (including `.IC` seeding and read-out) or explicitly bound the claim.

> **Author response (resolved by scoping).** Sections VIII-C and IX now state explicitly that no chip is fabricated and no energy/latency is measured, and identify state seeding and nanosecond read-out as costs that could dominate the budget the paradigm seeks to save. The title says "hardware-in-the-loop training," which is accurate — the loop is trained through a circuit simulator — and no efficiency claim is made. *Reviewer: confirmed; the scoping is now unambiguous.*

---

## Minor concerns

**m1 — Eq. (2) rigor.** The $I_{\text{load}}-I_{\text{sig}}$ form glosses the diff-pair current split. Add a sentence clarifying it is a lumped representation and that the simulator solves the exact device equations.

> *Resolved:* a clarifying sentence was added after Eq. (2). *Reviewer: confirmed.*

**m2 — "Among the first" claim.** Soften or support. *Resolved:* retained only with "to our knowledge," Section II-B.

**m3 — Reproducibility / simulator portability.** The hard-coded proprietary simulator path limits reproducibility. *Resolved:* acknowledged in Section VIII-D with a stated path to an open adjoint-capable simulator.

**m4 — Level-1 models.** Note that second-order device effects are absent and could change the operating point in silicon. *Resolved:* stated in Section VIII-C.

**m5 — Figure legibility.** Ensure the sensitivity heatmap's parameter axis and the stage schematic's node labels are readable at print size. *Reviewer: acceptable in v2.*

**m6 — Read-out standardization leakage.** Confirm that $(\mu,\sigma)$ are computed from the *initial* ring state only (no test leakage). *Confirmed by authors:* statistics are measured once from the untrained ring on the training set (Section IV), not refit.

---

## Assessment of novelty and significance

The novelty is not accuracy; it is the demonstration that a **closed-loop, transistor-level** KirchhoffNet with **initial-condition input** can be trained through a **real transient adjoint** with a **convergence-guarded** recipe, plus the clear documentation of the degeneracy failure mode. With the attribution corrected (M1) and the claims scoped (M6), this is a legitimate, if modest, methodological contribution suitable for a short paper or correspondence, and a useful stepping stone toward the physical realization the KirchhoffNet authors themselves flagged as open. I would not accept it as a full-length paper without M3 (multi-seed) and M4 (adjoint validation), but as a scoped methodological note the revised manuscript is publishable.

**Revised recommendation after v2:** Accept as a short paper / correspondence, conditional on the editor's tolerance for the single-seed evaluation, which the authors now disclose rather than disguise.

---

## Editor-facing checklist

| Concern | Severity | Status in v2 |
|---|---|---|
| M1 Performance attribution | Blocking | Resolved (abstract + Table III) |
| M2 Baselines / task difficulty | Major | Resolved |
| M3 Statistical rigor | Major | Scoped/disclosed (multi-seed deferred) |
| M4 Adjoint vs finite-difference | Major | Disclosed as future work |
| M5 Degeneracy documented | Major | Resolved (Section VIII-B) |
| M6 Hardware claim vs no energy | Major | Resolved by scoping |
| m1–m6 Minor | Minor | Resolved / confirmed |

The distinguishing merit of this manuscript is that its authors did the reviewer's hardest job for them: they refused to let the headline accuracies stand for more than they are worth. That candor is why the paper reaches a publishable state after one revision rather than several.
