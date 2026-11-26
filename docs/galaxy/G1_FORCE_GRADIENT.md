# G1 collisionless force gradients

G-GRAD checks the force on each particle against minus the derivative of the
total gravitational potential energy with respect to that particle’s position.
The Rust candidate uses isolated boundaries, dimensionless units with
$G=1$, and a common Plummer softening length $\epsilon=1$. Masses and
softening stay fixed. The [original registration](GRAVITY_PARTICLES_SPEC.md#11-prospective-reana-fixtures-and-pass-criteria)
sets strict relative limits of $10^{-7}$ for central differences and
$5\times10^{-13}$ for the independent algebraic derivative.

## Frozen cases

Two distinct particles have masses 2 and 3. The first is at the origin. The
second is at $r(2,-1,2)/3$ for each registered $r/\epsilon$ of 0, 0.01,
0.1, 1, 10 and 100. A seventh case exercises all three terms of the total
energy. It adds unequal masses 2, 3 and 5/4 at $(0,0,0)$, $(1/2,1,-1/4)$ and
$(-3/4,1/4,1/2)$. All momenta vanish. An immutable REANA prerequisite rounds
each rational position once to binary64, captures all seven ASCII inputs,
and resolves the control selectors. The Rust executable consumes those words.
Both references use the same central positions. All 45 Cartesian force
components enter the verdict.

## Independent measurements

For each particle $i$ and axis $a$, shift just $x_{ia}$ by $+h$ or $-h$ in
exact rational arithmetic. Independently sum the entire energy
$U=-\sum_{j<k}Gm_jm_k/(|x_k-x_j|^2+\epsilon^2)^{1/2}$ at each displaced
point. Rational bounds on each square root at 224 fractional bits enclose
the sum. Both endpoints must round to the same binary64 energy word.
The measured force is $(U_- - U_+)/(2h)$ using the two rounded energies.
Differencing the unrounded intervals separately measures truncation and
distinguishes it from the eventual loss of significance in the energy
difference. The energy calculation does not read the Rust potential or force.

The reference for the algebraic derivative is the existing per-particle
GP-2 radical certificate evaluated on the central words. The comparison
reconstructs its enclosure. For a nonzero component, an upper error bound
uses the lower magnitude of that component’s reference interval. The Rust
force must pass the strict algebraic limit separately on every axis.

## Spacing and decision rule

Use $h=H2^{-k}$ for every integer $k$ from 0 through 60. The pair fixtures use
$H=\max(1,r)$ and the three-body case uses $H=1$, in code length units.
For every nonzero component the following witnesses must occur in order.

1. Two successive halvings each reduce the measured error relative to the
   independent algebraic force by a factor between 2.5 and 6.
2. Three consecutive levels put the measured difference below $10^{-7}$
   relative to both the Rust force and the independent derivative, using the
   independent component scale in both comparisons.
3. At a finer level, rounded-energy differencing has a proved error above
   $10^{-7}$ while the unrounded secant is still below it.

The first admissible ordered witnesses are reported and every level is
retained. Decisions use rational bounds. Displayed floating-point error
intervals round outward. At coincident positions the exact derivative is
zero on every axis. The candidate and all 61 rounded differences must be
exactly zero, the displaced energies must be provably even by symmetry,
and the coarsest displacement must change the energy. This case has no
finite relative denominator.

## Execution

The original [nine static comparisons](STATIC_GRAVITY_COMPARISON_RESULTS.md)
identify the compiled Rust executable. Preparation verifies its bytes
and checks the driver, kernel, dependency sources, Rust toolchain and Cargo
lock file against the build revision. One independent REANA workflow runs
each control and each scientific case, with one CPU, 1 GiB of memory and one
thread. The closed source, observed native command, input words, analytic
certificate and both energy words at every spacing are retained.

The original binary is the `gravity.part0000` input from REANA workflow
`94bde6c3-0509-45a4-99f1-c858f5b19f70`. With access to that workspace,
`reana-client download -w 94bde6c3-0509-45a4-99f1-c858f5b19f70 gravity.part0000`
retrieves it. Its SHA256 is
`b7185b92b1c5052f5fc315e2fa8720eae54cb26742ed4b028127449d938f0196`.

Use `scripts/prepare_gravity_gradient.py preflight BINARY DESTINATION` to
stage the prerequisite. Stage the control workflows with `control` and
`--parent` pointing to its acquired output. Stage the scientific workflows
with `case`, the same `--parent`, and `--controls` pointing to the verified
control inventory. G-GRAD covers static collisionless forces. Long orbits,
covariance, physical-unit scaling, gas coupling and M2a have separate gates.

The portable replay checks the registered masses, IDs and once-rounded positions
against the recorded ASCII inputs. The summary gives the exact squared
separation in softening units for each pair alongside its nominal ratio.
The replay bounds the reciprocal radius on a separate 256-bit grid to
reconstruct both displaced energies and the central analytic derivative. It
compares all 5,490 energy words, checks the original Rust force words and
reconstructs the registered convergence and roundoff witnesses. Run
`python3 scripts/review_gravity_gradient.py evidence.tar.gz --output summary.json`
in a REANA workflow. Add `--plot gradient-ladder.png` to render the error curves.
