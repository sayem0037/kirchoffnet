# Evidence record

## Existing implementation

The relevant current files are `../netlist_kfq.py`, `../train_kfq.py`, `../kfq_spec.py`, `../simulator_api.py` and `../gradcheck_kfq.py`. Other files describe earlier ARC/KRC architectures and should not be treated as KFQ evidence solely because they share a directory.

- KFQ represents inputs with held differential voltage sources.
- Its synapses have four NMOS devices, gate-bias weights and source-connected input rows.
- Neurons are resistively loaded differential pairs with a tail transistor.
- Final scores use last-layer column differences.
- The custom simulator adapter requests sensitivities; its present implementation substitutes zero when a sensitivity is unavailable. A paper validation adapter should instead report missing derivatives explicitly.
- `kfq_spec.py` documents per-layer bias/load sizing. Its narrative failure numbers are not independently reproduced by creating this folder.

## Existing gradient reports inspected on 2026-10-18

| File under original results/ | Reported pass flag | Interpretation |
|---|---|---|
| gradcheck_kfq_0.1f_50n.json | true | Pass under that script's selected criterion and tested configuration |
| gradcheck_kfq_10f_50n.json | true | Same limited interpretation |
| gradcheck_kfq_10f_10n.json | false | Unresolved configuration-dependent gradient discrepancy |

These are existing custom-simulator/Level-1 reports, not newly executed SKY130 experiments. Their source hashes and compact summaries are captured separately in `existing_evidence_snapshot.json` when generated. A pass flag does not establish PDK accuracy, all-input validity or a physical speed result. The script selects the perturbation size with best median relative error; retain all perturbation results and verify a convergence plateau before paper claims.

## Ring evidence is separate

`../../toy2d_serial_diff/kring/README.md` and its legacy validation report document failures in the older ring adjoint and release frozen-ring models with trained readouts. This is not proof that KFQ's gradients are always wrong. Do not combine ring and KFQ validation results.

## New work in this folder

Literature synthesis and experiment design are completed research preparation. SKY130 setup, device tests and any subsequent circuit experiments must state their own completion status in `sky130/README.md` and their result files. No classification, novelty, energy or silicon result follows merely from downloading models.
