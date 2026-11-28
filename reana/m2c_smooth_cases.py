"""One independent REANA workflow for each physical configuration."""
def cases():
    matrix = {}
    def add(field, motion, steps, boost=0, size=3, threads=2):
        key = f"{field}-{motion}-n{size}-s{steps}-b{boost}-t{threads}"
        matrix[key] = [field, motion, str(steps), str(boost), str(size), str(threads)]
    for steps in (8, 16, 32, 64, 128, 256):
        add("advection", "deforming", steps)
    for field in ("uniform", "advection", "alfven", "low-beta"):
        for boost in (0, 1, 2):
            add(field, "deforming", 16, boost)
    for motion in ("fixed", "comoving"):
        add("advection", motion, 16)
        add("uniform", motion, 16)
    add("advection", "deforming", 16, threads=1)
    add("advection", "deforming", 16, size=4)
    add("alfven", "deforming", 16, size=4)
    return matrix

