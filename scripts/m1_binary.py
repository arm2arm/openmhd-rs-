"""Build once, or explicitly reuse a checksum-verified M1 executable."""
import hashlib
import re
import subprocess


def prepare_binary(root, cargo, expected_sha256=None):
    binary = root/'target/release/vector-potential'
    if expected_sha256 is None:
        subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'openmhd',
                        '--bin', 'vector-potential'], cwd=root, check=True)
    else:
        if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
            raise ValueError('Binary reuse requires a lowercase SHA256 digest')
        if not binary.is_file():
            raise ValueError('Missing prebuilt M1 binary: '+str(binary))
        actual = hashlib.sha256(binary.read_bytes()).hexdigest()
        if actual != expected_sha256:
            raise ValueError('Prebuilt M1 binary checksum mismatch')
    return binary
