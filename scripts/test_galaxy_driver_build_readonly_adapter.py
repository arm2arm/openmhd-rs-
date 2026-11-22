"""Purpose-path controls only; future independent REANA execution required."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('driver_build_get',
    ROOT / 'tools/galaxy_evidence/driver_build_readonly_adapter.py')
GET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GET)


class DriverBuildReadonlyAdapterTests(unittest.TestCase):
    def test_complete_fixed_build_metadata_and_three_command_inventory(self):
        expected = {'outputs/runtime.json'}
        expected.update(GET.PREFIX + name for name in ('build.json', 'runtime.json', 'export.json', 'files.sha256.json', 'export.failed.json', 'files.failed.sha256.json'))
        expected.update(GET.PREFIX + command + '/' + name
                        for command in ('compiler', 'geometry', 'gravity')
                        for name in ('command.json', 'stdout.txt', 'stderr.txt'))
        self.assertEqual(GET.FIXED, expected)
        self.assertEqual(len(expected), 16)
        for name in expected:
            self.assertEqual(GET.artifact_path(name), name)

    def test_part_boundaries_are_exact_ascii_original_names(self):
        for kind in ('geometry', 'gravity'):
            for index in ('0000', '0001', '0511'):
                name = GET.PREFIX + 'parts/' + kind + '.part' + index
                self.assertEqual(GET.artifact_path(name), name)
            for index in ('0512', '9999', '00000', '0', '٠٠٠٠', '-001'):
                with self.assertRaises(GET.native.base.AdapterError) as caught:
                    GET.artifact_path(GET.PREFIX + 'parts/' + kind + '.part' + index)
                self.assertEqual(caught.exception.code, 'unsafe_remote_path')

    def test_paths_cannot_escape_or_extend_the_selected_build_protocol(self):
        for name in ('/outputs/galaxy-driver-build/build.json',
                     GET.PREFIX + '../runtime.json', GET.PREFIX + 'parts//geometry.part0000',
                     GET.PREFIX + 'parts/geometry.part0000/extra',
                     GET.PREFIX + 'parts/geometry.part0000\n',
                     GET.PREFIX + 'binaries/geometry3-case', GET.PREFIX + 'binaries/gravity-force-case',
                     GET.PREFIX + 'unknown/command.json', 'outputs/galaxy-preflight/export.json',
                     'outputs/reference/reference.json', GET.PREFIX + 'build.json?query=1'):
            with self.assertRaises(GET.native.base.AdapterError) as caught:
                GET.artifact_path(name)
            self.assertEqual(caught.exception.code, 'unsafe_remote_path')

    def test_nonstring_path_types_are_typed_rejections(self):
        for name in (None, True, 0, b'outputs/runtime.json', Path('outputs/runtime.json'), []):
            with self.assertRaises(GET.native.base.AdapterError) as caught:
                GET.artifact_path(name)
            self.assertEqual(caught.exception.code, 'unsafe_remote_path')

    def test_invalid_cli_path_stops_before_settings_or_output_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / 'must-not-exist.bin'
            error_stream = io.StringIO()
            with mock.patch.object(GET.native.base, 'settings_from_private',
                                   side_effect=RuntimeError('UNREACHED_SCHEMA_ONLY_SETTINGS')) as settings:
                with contextlib.redirect_stderr(error_stream):
                    code = GET.main(['download', '--workflow', 'openmhd-build-control.1',
                                     '--path', GET.PREFIX + 'parts/gravity.part0512',
                                     '--output', str(target)])
            self.assertEqual(code, 1)
            self.assertEqual(settings.call_count, 0)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_name(target.name + '.partial').exists())
            self.assertEqual(json.loads(error_stream.getvalue())['code'], 'unsafe_remote_path')

    def test_invalid_client_download_is_rejected_before_server_lookup(self):
        client = GET.native.Client.__new__(GET.native.Client)
        with mock.patch.object(client, 'matching_rows',
                               side_effect=RuntimeError('UNREACHED_SCHEMA_ONLY_LOOKUP')) as lookup:
            with self.assertRaises(GET.native.base.AdapterError) as caught:
                client.download('openmhd-build-control.1', GET.PREFIX + 'parts/gravity.part0512', None)
        self.assertEqual(caught.exception.code, 'unsafe_remote_path')
        self.assertEqual(lookup.call_count, 0)

    def test_allowed_client_part_uses_same_uuid_and_exact_workspace_path(self):
        # This is an inert protocol stub: get records its arguments and never
        # consumes a response, contacts a server or publishes any artifact.
        client = GET.native.Client.__new__(GET.native.Client)
        row = {'id': '11111111-1111-4111-8111-111111111111', 'status': 'finished'}
        name = GET.PREFIX + 'parts/geometry.part0511'
        with mock.patch.object(client, 'matching_rows', return_value=[row]) as lookup:
            with mock.patch.object(client, 'get', return_value=None) as transfer:
                result = client.download('openmhd-build-control.1', name, None)
        self.assertEqual(result, [row['id']])
        self.assertEqual(lookup.call_count, 2)
        self.assertEqual(transfer.call_count, 1)
        args = transfer.call_args.args
        self.assertEqual(args[0], '/api/workflows/' + row['id'] + '/workspace/' + name)
        self.assertEqual(args[1], {})
        self.assertTrue(callable(args[2]))


if __name__ == '__main__':
    unittest.main()
