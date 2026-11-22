# Proposed exact G01 reduction and limits

This note preregisters source for independent review before execution. It is
not an adopted norm, measured error, passing reference or component decision.
The eight numeric names and their `1/10000000000` thresholds remain the exact
ones in the unchanged hashed analytic design. No result, covariance tolerance
or new numerical acceptance condition is inferred from a grammar control.

Candidate words are interpreted exactly as dyadic rationals with integer
significand/exponent arithmetic, including either signed zero and gradual
underflow. This small decoder is explicit new source for review; it calls no
host float/libm conversion or candidate kernel. It is not a second proof of
the reference generator's decoder. Reference rational values are exact.
Radical records retain their supplied signed enclosure; the reducer verifies
containment by squaring with the correct sign ordering against `factor²*q`.
It neither substitutes the observational nearest word nor evaluates a new
square root. All input/reference/design hashes, case metadata and exact
positive topology inventories must agree before numeric observations exist.
The actual execution/source/binary provenance still needs the separate runner.

For candidate exact value x and exact target in [a,b], the absolute error lies
in `[max(a-x,x-b,0),max(abs(x-a),abs(x-b))]`. For nonnegative error [e0,e1]
and an independently positive denominator [d0,d1], the normalized error lies
in `[e0/d1,e1/d0]`. An interval containing a nonpositive normalization bound
rejects: there is no candidate floor or fallback to a nearest reference word.
An upper error at or below the gate passes the arithmetic observation; a
lower error strictly above it fails; a crossing is explicitly unresolved.
Every required observation must pass; unresolved cannot satisfy a gate.

The proposed exact reductions are:

- Cell volume: `abs(Vc-Vref)/Vref`, using each positive exact reference volume.
- Cell centroid: Euclidean norm of the three owner-relative offset errors,
  divided by fixed `Lref=max(actual input side lengths)`. Squared norms are
  compared to the squared unchanged threshold, avoiding a new square root.
- Positive face area: absolute error against its exact/algebraic area,
  divided by that positive independent reference area enclosure.
- Face centroid: Euclidean error divided by Lref. Both canonical left offsets
  and every owner's actual chart centroid enter this maximum. For the latter,
  form `actual generator word + face offset word + chart translation word`
  exactly and compare to that reference incidence's absolute chart centroid.
  This checks right-chart translations and retains both self-face incidences.
- Unit normal: maximum absolute component error in the canonical orientation.
- Integrated central moment: each absolute component error divided by the
  corresponding fixed expected cell volume times Lref squared; J is not J/V.
- Normal closure: Euclidean norm of `sum(sign*A_candidate*n_candidate)` in
  exact rational arithmetic divided by the sum of independent reference face
  areas for that owner, including both self incidences. The supplied positive
  radical area intervals bound the denominator. The candidate's reported
  surface value cannot inflate that denominator. Compare squared quantities.
- Volume closure: `abs(sum(V_candidate)-Vbox)/Vbox`, where Vbox is the product
  of the actual rounded input widths, and first require the independent exact
  reference volume sum equals that same box volume.

The Euclidean centroid choice, inclusion of all incidence charts in the face
centroid maximum and independent reference-surface closure normalization are
explicit prospective definitions. The parent design supplies named maxima
and thresholds but does not completely spell out all those reducer details.
Independent review must decide compatibility before adoption and before any
case execution; none may be silently changed after observing errors. Squared
observations are labelled with their squared norms and thresholds so they
cannot be misreported as unsquared error magnitudes.

Exact persistent cell and full owner/image face-key sets must match. Reference
and candidate signed incidence inventories match per owner without collapsing
self images. The bridge separately requires each face's one or two exact uses,
local-to-persistent owner links and all declared vertex rows. Positive values
are never deleted to repair counts. Input rejection, unmatched topology or an
unresolved enclosure cannot be treated as success of a required fixture.

Covariance, polygon geometry/orientation, radius, plane distance and the other
quality observations remain retained and explicitly unregistered metrics in
this reducer. They have no invented tolerance here. The full source/oracle
validation and later geometry/conditioning/operator/moving gates remain
required. This arithmetic result alone is not all of G01 or M2a acceptance.
Its schema deliberately includes `proposal`; even an all-pass arithmetic
record has `execution_provenance_verified=false, component_accepted=false`.

Twelve plain written arithmetic controls cover exact finite words, subnormal
and overflow exclusions, canonical rationals, signed radical containment,
exact-reference versus rounded-word errors, strictly positive normalization,
inclusive thresholds and unresolved intervals, Euclidean versus axiswise
norms, radical vector uncertainty and complete image keys. They construct no
complete successful physical packet and remain unexecuted. Complete live
252-case reference/candidate integration and sensitivity/negative reductions,
source/import/build prerequisites, actual per-case REANA artifacts, full
acquisition/offline verification and independent numerical-output review are
still missing. No new arithmetic, test, reference or candidate ran locally.
