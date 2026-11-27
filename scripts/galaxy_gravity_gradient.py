"""Compare the Rust force with central differences of an independent total potential."""
from fractions import Fraction
from itertools import combinations
import math
import struct

from galaxy_gravity_compare import Certificates, sqrt_bounds, word as decode_word

FD_LIMIT = Fraction(1, 10**7)
ALGEBRA_LIMIT = Fraction(5, 10**13)
HALVINGS = 60
RATIOS = {"r0": "0", "r001": "0.01", "r01": "0.1", "r1": "1", "r10": "10", "r100": "100"}
CASE_NAMES = (*RATIOS, "three-body")


def word(value):
    return struct.pack(">d", float(value)).hex()


def fixture(name):
    """Round each specified rational coordinate once, before any force evaluation."""
    zero = (Fraction(0),) * 3
    if name == "three-body":
        particles = [(2, zero), (3, (Fraction(1, 2), 1, Fraction(-1, 4))),
                     (Fraction(5, 4), (Fraction(-3, 4), Fraction(1, 4), Fraction(1, 2)))]
    else:
        radius = Fraction(RATIOS[name])
        particles = [(2, zero), (3, tuple(radius * i / 3 for i in (2, -1, 2)))]
    lines = ["openmhd-gravity-force-input-v1", "case G1-GRAD-" + name,
             "stage static-force-snapshot", "clock 0000000000000000 0", "backend 0",
             "units dimensionless-g1", "softening " + word(1) + " 0", f"count {len(particles)}"]
    for index, (mass, position) in enumerate(particles, 1):
        kind = "star" if index == 2 else "dm"
        fields = [f"{1:016x}{index:016x}", kind, "0", "0", "0",
                  *map(word, (mass, *position, 0, 0, 0))]
        lines.append("particle " + " ".join(fields))
    return ("\n".join([*lines, "end", ""])).encode("ascii")


def potential(physical, particle_id, axis, displacement):
    """Enclose U at an exact displaced point, summing each unordered pair once."""
    points = []
    for source in physical.sources:
        position = list(source.position)
        if source.payload == particle_id:
            position[axis] += displacement
        points.append((position, source.mass))
    lower = upper = Fraction(0)
    for (x, m), (y, n) in combinations(points, 2):
        squared = physical.epsilon**2 + sum((a - b)**2 for a, b in zip(x, y))
        r_lo, r_hi = sqrt_bounds(squared, 224)
        coefficient = -physical.g * m * n
        lower += coefficient / r_lo
        upper += coefficient / r_hi
    # Two-sided proof of correct rounding of the entire displaced energy.
    if word(lower) != word(upper):
        raise ArithmeticError("Displaced energy does not have a certified binary64 rounding")
    return lower, upper, Fraction.from_float(float(lower))


def relative_error(value, reference):
    """Lower and upper bounds on the absolute difference divided by |reference|."""
    lo, hi = reference
    if lo <= 0 <= hi:
        raise ValueError("Nonzero force component required for a relative error")
    a, b = value
    return (max(a - hi, lo - b, 0) / max(abs(lo), abs(hi)),
            max(abs(a - hi), abs(b - lo)) / min(abs(lo), abs(hi)))


def outer(bounds):
    """Compact outward-rounded display bounds. All verdicts use exact fractions."""
    lo, hi = bounds
    return [max(0., math.nextafter(float(lo), -math.inf)), math.nextafter(float(hi), math.inf)]


def witnesses(curve):
    """Return the first chronological truncation, three-level plateau and roundoff witnesses."""
    def quadratic(i):
        coarse, fine = curve[i]["rounded_error"], curve[i+1]["rounded_error"]
        return fine[0] > 0 and coarse[0] >= Fraction(5, 2) * fine[1] and coarse[1] <= 6 * fine[0]
    count = len(curve)
    truncation = next((i for i in range(count-2) if quadratic(i) and quadratic(i+1)), None)
    plateau = None
    roundoff = None
    if truncation is not None:
        plateau = next((i for i in range(truncation+2, count-2)
                        if all(max(r["rounded_error"][1], r["rust_error"]) < FD_LIMIT
                               for r in curve[i:i+3])), None)
    if plateau is not None:
        roundoff = next((i for i in range(plateau+3, count)
                         if curve[i]["rounded_error"][0] > FD_LIMIT
                         and curve[i]["secant_error"][1] < FD_LIMIT), None)
    return dict(truncation_start=truncation, plateau_start=plateau, roundoff=roundoff)


def coordinate(physical, particle_id, axis, rust_force, certificate, scale):
    reference, structural_zero = certificate
    if structural_zero and reference != (0, 0):
        raise ValueError("Structural zero requires an exact zero certificate")
    algebra = None if structural_zero else relative_error((rust_force, rust_force), reference)
    denominator = None if structural_zero else min(abs(x) for x in reference)
    baseline = potential(physical, particle_id, axis, 0)[2]
    # Coincident coordinates give identical squared distances term by term for either sign of h.
    center = next(p for p in physical.sources if p.payload == particle_id)
    exact_even = all(p.position[axis] == center.position[axis] for p in physical.sources)
    coarse_energy_changes = False
    rows = []
    curve = []
    for k in range(HALVINGS+1):
        h = scale / (1 << k)
        plus = potential(physical, particle_id, axis, h)
        minus = potential(physical, particle_id, axis, -h)
        fd = (minus[2] - plus[2]) / (2*h)
        secant = ((minus[0] - plus[1]) / (2*h), (minus[1] - plus[0]) / (2*h))
        row = dict(k=k, h_word=word(h), U_plus=word(plus[2]), U_minus=word(minus[2]), force_fd=float(fd))
        if structural_zero:
            exact_even &= plus[:2] == minus[:2] and fd == 0 and secant[0] <= 0 <= secant[1]
            if k == 0:
                coarse_energy_changes = plus[2] != baseline
        else:
            rounded_error = relative_error((fd, fd), reference)
            secant_error = relative_error(secant, reference)
            rust_error = abs(fd - rust_force) / denominator
            curve.append(dict(rounded_error=rounded_error, secant_error=secant_error, rust_error=rust_error))
            row.update(fd_vs_algebra=outer(rounded_error), exact_secant_vs_algebra=outer(secant_error),
                       fd_vs_rust_upper=outer((0,rust_error))[1])
        rows.append(row)
    result = dict(id=particle_id, axis="xyz"[axis], rust_force_word=word(rust_force),
                  structural_zero=structural_zero, levels=rows)
    if structural_zero:
        result.update(exact_even=exact_even, coarse_energy_changes=coarse_energy_changes,
                      passed=bool(exact_even and coarse_energy_changes and rust_force == 0))
    else:
        proof = witnesses(curve)
        result.update(algebra_relative=outer(algebra), witness=proof,
                      passed=algebra[1] < ALGEBRA_LIMIT and all(i is not None for i in proof.values()))
    return result


def compare(name, physical, evaluation, analytic):
    if name not in CASE_NAMES or physical.epsilon != 1 or physical.g != 1:
        raise ValueError("Registered code units and common softening required")
    samples = {r["id"]: r["force"] for r in evaluation["samples"]}
    expected = analytic["samples_by_particle_id"]
    if set(samples) != set(expected) or set(samples) != {p.payload for p in physical.sources}:
        raise ValueError("Rust and reference particle identities disagree")
    scale = max(Fraction(1), Fraction(RATIOS.get(name, "1")))
    certs = Certificates()
    results = []
    for p in physical.sources:
        for axis in range(3):
            certificate = certs.read(expected[p.payload]["force"][axis])
            results.append(coordinate(physical, p.payload, axis, decode_word(samples[p.payload][axis]),
                                      certificate, scale))
    return dict(schema="openmhd.gravity-gradient.v1", case=name, coordinates=results,
                particles=len(samples), pair_count=len(physical.sources)*(len(physical.sources)-1)//2,
                halvings=HALVINGS, fd_limit=str(FD_LIMIT), algebra_limit=str(ALGEBRA_LIMIT),
                passed=all(r["passed"] for r in results), full_g1_accepted=False)
