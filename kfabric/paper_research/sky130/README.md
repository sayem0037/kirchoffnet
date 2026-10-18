# SKY130 simulation study

Requested technology: open SkyWater SKY130. This directory is for a simulation subset and reproducible characterization, not a full layout/DRC/LVS PDK installation.

Official sources:

- https://skywater-pdk.readthedocs.io/en/main/sim.html
- https://skywater-pdk.readthedocs.io/en/main/rules/device-details.html
- https://github.com/google/skywater-pdk-libs-sky130_fd_pr
- https://ngspice.sourceforge.io/docs.html

Setup status and actual results will be recorded here after execution. Use explicit model commits and preserve upstream licensing. Never label a transformed or simplified device card as an unchanged foundry model.

The original 3.3 V KFQ biases cannot be copied directly onto 1.8 V devices. Select a documented device family and redesign the operating point. Initial characterization can use the 1.8 V NMOS family at a 1.8 V supply; its results do not establish equivalence to the original 3.3 V design.
