import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from m1_binary import prepare_binary


class PrebuiltBinary(unittest.TestCase):
    def test_verified_reuse_never_invokes_cargo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root/'target/release/vector-potential'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'exact preflight executable fixture')
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            with patch('m1_binary.subprocess.run') as cargo:
                self.assertEqual(prepare_binary(root, 'cargo', digest), binary)
                cargo.assert_not_called()

    def test_wrong_missing_and_malformed_reuse_fail_without_building(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root/'target/release/vector-potential'
            binary.parent.mkdir(parents=True)
            with patch('m1_binary.subprocess.run') as cargo:
                with self.assertRaisesRegex(ValueError, 'Missing prebuilt'):
                    prepare_binary(root, 'cargo', '0'*64)
                binary.write_bytes(b'changed executable')
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    prepare_binary(root, 'cargo', '0'*64)
                for digest in ('', 'abc', 'G'*64, 'A'*64):
                    with self.assertRaisesRegex(ValueError, 'SHA256'):
                        prepare_binary(root, 'cargo', digest)
                cargo.assert_not_called()

    def test_standalone_build_keeps_original_cargo_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('m1_binary.subprocess.run') as cargo:
                self.assertEqual(prepare_binary(root, 'cargo'), root/'target/release/vector-potential')
                cargo.assert_called_once_with(
                    ['cargo', 'build', '--release', '--locked', '-p', 'openmhd',
                     '--bin', 'vector-potential'], cwd=root, check=True)


if __name__ == '__main__':
    unittest.main()
