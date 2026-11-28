"""One original REANA workflow per fixed input and transport/layout."""
from mpi_matrix import fixed

CONTRACTS = ("routing", "mismatch", "range", "producer-error")
LAYOUTS = ((1, 1), (2, 2), (4, 1), (8, 1))


def cases():
    rows = {}
    for label in ("curl-flux3", "moving-curl3", "swept-jitter", "swept-flip", "periodic-self"):
        mesh = label.startswith("swept-") or label == "periodic-self"
        for mode, r, t in [("serial", 1, 1), *[(m, r, t) for r, t in LAYOUTS for m in ("full", "sparse")]]:
            opts = dict(repeats=3, sweeps=mesh, tracer=mesh)
            if mode != "serial":
                opts["halo"] = mode
            if (label == "swept-flip" and r == 8) or label == "periodic-self":
                opts["empty_owner"] = True
            rows[f"{label}-{mode}-{r}x{t}"] = fixed(label, r, t, mode == "serial", **opts)
    for mode in ("full", "sparse"):
        rows[f"curl-flux3-reverse-{mode}"] = fixed("curl-flux3", 4, 2, repeats=3, reverse=True, halo=mode)
        for selector in CONTRACTS:
            rows[f"contract-{selector}-{mode}"] = dict(family="contract", selector=selector,
                                                        ranks=4, threads=1, repeats=1, halo=mode, timeout=60)
    return rows
