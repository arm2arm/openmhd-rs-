# Measured Alfvén error components (issue #7)

Read-only postprocessing of the completed REANA medium packet: 32 waves at
t=0,.25,1. All 96 original snapshot hashes match their execution records;
each independently recomputed relative B L2 norm matches the registered norm
within relative 5e-10 / absolute 1e-15. The orthogonal identity below closes
within relative 5e-10 / absolute 1e-22 in every snapshot. These are analysis
consistency checks on measured data, not new MHD evolutions or a new gate.

For amplitude A=.1, mean Bx=1, analytic phase
theta=2pi[x+(1-v_parallel-boost_x)t], define q=(Bz+i By)/A,
e=exp(i theta), c=<q conjugate(e)>_V. Angle brackets denote the
cell-volume-weighted mean divided by total volume. Since |e|=1, projection
onto e gives this exact squared-error decomposition:

```text
(B L2 / A)^2 = (|c|-1)^2                         amplitude
             + 4 |c| sin(arg(c)/2)^2           phase
             + <|q-c e|^2>_V                   orthogonal remainder
             + <((Bx-1)/A)^2>_V                longitudinal
```

On irregular cells the remainder is not a resolved Fourier spectrum. This
L2 decomposition does not replace the preregistered L1 convergence fit.

At N64 on fixed meshes, **phase accounts for 65–84% of final squared B
error**. Much of the amplitude deficit already exists in the initial discrete
curl. This identifies the leading error component, not its algorithmic cause.
It does not establish that phase is the only obstruction to fine-grid
acceptance or that the candidate's spatial order is sufficient.

| Mesh / wave | Initial amplitude deficit (%) | Final deficit (%) | Final phase (mrad) | Phase share of squared B error (%) |
| --- | ---: | ---: | ---: | ---: |
| Regular / travelling | .37838 | .44301 | -8.58905 | 65.092 |
| Regular / standing | .37838 | .43237 | -12.95186 | 67.015 |
| Jitter .15 / travelling | .45502 | .55094 | -9.34398 | 65.438 |
| Jitter .15 / standing | .45502 | .52805 | -13.91346 | 83.665 |

[Plot](../../../../docs/images/m1_completion/medium_wave_error_components.png).
The measured report contains all 32 wave configurations and all three times,
including both boosts and motion families. It records original execution
provenance, runs and snapshot hashes, analysis source hash, norms, component
fractions and identity residuals. The original raw files remain at the REANA
and local locations listed in the [parent evidence record](../README.md).

Reproduce from complete original raw files, then render the compact report:

```sh
python3 scripts/analyze_alfven_modes.py <original-waves_medium-directory> <fresh-measurements.json>
python3 scripts/plot_alfven_modes.py tests/reference/m1_reana_bounded/wave_modes/measurements.json.gz docs/images/m1_completion/medium_wave_error_components.png
```

No solver, thresholds, initial conditions or frozen REANA inputs change.
N128 calibration checkpoints and unfinished runs are excluded from this packet.
