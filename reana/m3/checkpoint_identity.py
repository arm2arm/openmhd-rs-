"""Compare v2 parallel MHD checkpoints across executable builds using the Rust wire format."""
import hashlib
import json
from pathlib import Path

MAGIC = b"OPENMHD-RESTART\0"
HASH_SIZE = 32
HEADER_SIZE = 32
CONTROL_ERRORS = {
    "changed-state": "different saved state",
    "changed-source": "different numerical source or build",
    "wrong-executable": "wrong executable fingerprint",
    "damaged-checksum": "checkpoint checksum",
    "wrong-length": "checkpoint payload length",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def state(data, executable):
    """Decode the envelope and the first two length-prefixed digests."""
    require(len(data) > HEADER_SIZE + 80 + HASH_SIZE and data[:16] == MAGIC, "checkpoint header")
    require(int.from_bytes(data[16:24], "little") == 2, "checkpoint version")
    payload = data[HEADER_SIZE:-HASH_SIZE]
    require(int.from_bytes(data[24:32], "little") == len(payload), "checkpoint payload length")
    require(bytes.fromhex(sha(data[:-HASH_SIZE])) == data[-HASH_SIZE:], "checkpoint checksum")
    require(int.from_bytes(payload[:8], "little") == HASH_SIZE and
            int.from_bytes(payload[40:48], "little") == HASH_SIZE, "fingerprint lengths")
    require(payload[48:80].hex() == executable, "wrong executable fingerprint")
    return payload[8:40], payload[80:]


def compare(original, current, original_exe, current_exe):
    """Check both executable hashes and compare every remaining payload byte."""
    original_source, original_state = state(original, original_exe)
    current_source, current_state = state(current, current_exe)
    require(original_source == current_source, "different numerical source or build")
    require(original_state == current_state, "different saved state")
    return {
        "original_sha256": sha(original), "current_sha256": sha(current),
        "original_executable": original_exe, "current_executable": current_exe,
        "numerical_build": original_source.hex(), "state_sha256": sha(original_state),
        "state_bytes": len(original_state),
    }


def run(request, original, current):
    require(request["schema"] == "openmhd.m3-build-bound-checkpoint.v1", "checkpoint comparison schema")
    require(sha(original) == request["original_sha256"] and sha(current) == request["current_sha256"],
            "different acquired checkpoint")
    old_exe, new_exe = request["original_executable"], request["current_executable"]
    require(old_exe != new_exe, "expected two distinct executables")
    result = compare(original, current, old_exe, new_exe)
    control = request["control"]
    if control == "observed":
        return {"request": request, "comparison": result}

    # Change a single field of a copy of the actual new checkpoint. For payload
    # changes, recompute the envelope digest so it cannot mask the intended error.
    offsets = {"changed-state": HEADER_SIZE + 80, "changed-source": HEADER_SIZE + 8,
               "wrong-executable": HEADER_SIZE + 48, "damaged-checksum": -1, "wrong-length": 24}
    changed = bytearray(current)
    changed[offsets[control]] ^= 1
    if control != "damaged-checksum":
        changed[-HASH_SIZE:] = hashlib.sha256(changed[:-HASH_SIZE]).digest()
    try:
        compare(original, bytes(changed), old_exe, new_exe)
    except ValueError as exc:
        if str(exc) != CONTROL_ERRORS[control]:
            raise
        return {"request": request, "comparison": result, "rejected": str(exc)}
    raise ValueError("changed checkpoint accepted")


if __name__ == "__main__":
    request = json.loads(Path("request.json").read_bytes())
    result = run(request, Path("original.bin").read_bytes(), Path("current.bin").read_bytes())
    Path("comparison-result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
