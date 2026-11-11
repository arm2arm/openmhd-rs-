# Standing-wave error localisation, 2026-11-11

This independent, read-only analysis uses completed outputs from the stopped
`openmhd-m1-pressure-reuse-20261110.1` workflow. It launches no evolution and
changes no numerical method or gate. All **12 raw final CSV hashes** match the
immutable 104-case checkpoint retained in `runs.json.gz`.

## Timestep control at N64

Compare each standing fixed-mesh solution with the same-grid `dt=2.5e-5`
solution, using persistent IDs, matching geometry and volume-weighted vector
B norms. All four requested timestep caps are actually reached.

| Mesh | B L1 error against analytic wave, dt=4e-4 | B L1 difference to dt=2.5e-5 | Difference / analytic error |
| --- | ---: | ---: | ---: |
| Regular | 0.001495753851763179 | 1.4494103318658212e-8 | 9.690166133667458e-6 |
| Jitter .15 | 0.0014925057812240352 | 2.2754484657530662e-8 | 1.524582681272379e-5 |

The time-refinement difference is about **0.001–0.0015%** of the analytic
error. Thus at N64, timestep error is not the dominant contribution to this
standing-wave failure. This does not by itself prove the cause at N256, or
establish general temporal accuracy. Full B, vector A and phi differences at
all three coarser caps are retained in `reduction.json`.

## Regular-mesh mode decomposition

For each transverse component, compute sine/cosine coefficients
`2 sum_i V_i q_i sin/cos(2 pi m x_i)`, for modes 1 through 9. Remove only the
fundamental mode from By/Bz, then measure the remaining transverse vector L1.
The regular fixed unit-square mesh provides the uniform periodic quadrature.

| N | Transverse B L1 after removing the fundamental |
| --- | ---: |
| 32 | 0.0014477408096092966 |
| 64 | 0.0005913505618844358 |
| 128 | 0.00022035073036094543 |
| 256 | 0.00008007729533453757 |

The finest-three slope of that residual is **1.4422742421**. This identifies
distortion beyond amplitude/phase error in the fundamental as a slowly
converging part of the solution. It is a diagnostic norm, not a replacement
for the registered total B L1 convergence gate (which still fails at 1.6591
for this regular-mesh family).

The next bounded control should isolate the effects of limiting and spatial
fluid/A reconstruction. A limiter-related cause is a hypothesis, not an
established result. Disabling a limiter for a smooth diagnostic would not
justify disabling it for shocks or changing the production default. The
conservative update, positivity gates and historical failures must be retained.

## Reproduction

```sh
python3 tests/reference/m1_pressure_campaign/standing_diagnosis/reduce.py \
  results/reana_remote_m1_pressure_reuse_20261110/source/results/reana_m1-campaign/waves \
  /tmp/standing-diagnosis.json
```

The standard-library reducer imports no production numerical/error routines.
It checks configuration, completion, positive states, IDs, times, finite values,
volumes and every raw hash before measuring. Raw CSVs remain locally at the
path above and remotely under `source/results/reana_m1-campaign/waves/`; they
are not duplicated in this compact archive. `archive_sha256.json` covers every
other archive member. This is implementing-assistant analysis, not a separate
scientific review or M1 acceptance.
