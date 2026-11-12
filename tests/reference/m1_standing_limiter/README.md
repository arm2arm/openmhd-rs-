# Standing-wave limiter evidence (issue #26)

Implementing-assistant analysis, not independent scientific review. No gate,
grid, reference or default changes here. M1 remains unaccepted. The
prospective contract is [docs/M1_STANDING_WAVE_PLAN.md](../../../docs/M1_STANDING_WAVE_PLAN.md).

## 1. Localisation in the retained outputs (2026-11-12, no evolution)

`localise.py` reduces eight existing regular fixed-mesh base snapshots of the
stopped `openmhd-m1-pressure-reuse-20261110.1` workflow: the failing standing
ladder (parallel velocity 1) and the passing travelling ladder (parallel
velocity 0). All eight raw SHA256 values match the retained 104-case run map.
It imports no production error routine. At t=1 both families have analytic
phase `2 pi x`.

For each transverse field component it removes the volume-weighted mean and
fundamental mode, then measures where the remaining L1 distortion lies:
within 1/16 box length of that component's **own extrema**, or of the extrema
of the **vector-potential component** whose x-derivative it is (the field
component's zeros). Each window set covers a quarter of the box, so a uniform
distortion gives .25 in both columns.

| Family | N | B L1 | By distortion L1 | near By extrema | near Az extrema |
| --- | ---: | ---: | ---: | ---: | ---: |
| standing | 32 | 4.5796e-3 | 9.613e-4 | .022 | .541 |
| standing | 64 | 1.4957e-3 | 3.590e-4 | .021 | .665 |
| standing | 128 | 4.7879e-4 | 1.267e-4 | .015 | .854 |
| standing | 256 | 1.4997e-4 | 4.532e-5 | .021 | **.936** |
| travelling | 32 | 3.5430e-3 | 7.357e-4 | .427 | .101 |
| travelling | 64 | 1.0392e-3 | 1.610e-4 | .670 | .054 |
| travelling | 128 | 2.7667e-4 | 3.446e-5 | .876 | .036 |
| travelling | 256 | 7.0955e-5 | 7.652e-6 | **.933** | .028 |

Bz behaves the same way (.937 near Ay extrema for the standing wave, .929
near its own extrema for the travelling wave). Two-point slopes between N64
and N256:

| Family | B L1 | By fundamental error | By distortion | Bz distortion |
| --- | ---: | ---: | ---: | ---: |
| standing | 1.659 | 1.959 | **1.493** | **1.426** |
| travelling | 1.936 | 1.978 | 2.198 | 2.143 |

Only odd harmonics are present; even harmonics are at roundoff
(`localisation.json` keeps modes 1–9). At N256 the standing distortion peaks
at 6.3e-4, the travelling one at 9.6e-5 (By) and 1.5e-4 (Bz).

**Reading.** The fundamental converges at second order in both families. The
standing failure is carried by distortion that sits at the extrema of `A`,
converges at about 1.45 and is absent in the travelling family, where the
smaller distortion sits at the field's own extrema. This is what clipping of
the `A` gradients used by the `b · grad(A)` transport would produce, and that
term is active only when fluid moves through the mesh. It is a localisation,
not a controlled demonstration; the controls are registered in the plan.

Reproduce (needs the raw CSVs, which are not duplicated here):

```sh
python3 tests/reference/m1_standing_limiter/localise.py \
  results/reana_remote_m1_pressure_reuse_20261110/source/results/reana_m1-campaign/waves \
  /tmp/localisation.json
```

The four travelling snapshots were downloaded read-only from the stopped
workflow at `source/results/reana_m1-campaign/waves/<case>/final.csv` and
hash-checked. `archive_sha256.json` covers the other files in this directory.
