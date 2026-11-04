# Conservative state/face-flux evidence for issue #4

Generated on 2026-11-04 from clean revision `c18664d3b8accb1048db9d456c3a68d58141973a` with:

```sh
python3 scripts/run_core_flux_validation.py
```

See [the numerical setup, predeclared gates and measured explanation](../../../docs/CORE_FLUX_VALIDATION.md). `summary.csv` contains all diagnostics and L1/L2 errors. `provenance.json` records source/output hashes, commands, toolchain and the independent Athena++ reference. The four compressed CSVs contain the full periodic profiles at t=.1 for total N512/1024/2048 and the N512 joint fluid/grid boost of +2.

The profiles evolve conservative induction directly; they contain no A/curl, gauge or dynamic Voronoi integration. The Athena reference is separately archived in `../external_mhd/`. Its implementation and spatial reconstruction differ from the Rust driver, and its finite-resolution uncertainty is reported separately.
