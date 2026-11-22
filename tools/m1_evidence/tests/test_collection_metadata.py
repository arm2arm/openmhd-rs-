"""Metadata-only collection regressions: each test is a separate REANA case.

No full successful physical packet is synthesized. No numerical reducer, build,
simulation or live transport is invoked; temporary bytes exercise host contracts.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0,str(TOOLS))
import collect_fresh_physics_reference_inputs as collector
import prepare_final_evidence as prepare


def hashed(data):
    return hashlib.sha256(data).hexdigest()


def mock_owner(process):
    owner = mock.Mock()
    owner.process = process
    owner.start.return_value = process
    owner.completed_returncode.return_value = process.returncode
    owner.primary_start_error.return_value = None
    owner.receipt.return_value = dict(state='settled', writers_stopped=True)
    return owner


class CollectionMetadataTests(unittest.TestCase):
    def wave_fixture(self, root):
        source = root/'fresh/raw/fixture/final.csv'
        source.parent.mkdir(parents=True)
        source.write_bytes(b'actual fresh metadata fixture\n')
        view = root/'private/raw/fixture/final.csv'
        view.parent.mkdir(parents=True)
        view.symlink_to(source)
        out = root/'collection/wave_inputs'
        target = out/'fixture/final.csv'
        target.parent.mkdir(parents=True)
        target.symlink_to(view)
        value = hashed(source.read_bytes())
        (out/'input_receipts.json').write_text(json.dumps([
            dict(name='fixture',artifact='final.csv',sha256=value,
                 workflow='fixture-workflow',local_source=str(view),downloaded=False)]))
        runs = {'fixture':{'sha256':{'final.csv':value}}}
        receipt = {'receipts':{'fixture':{
            # Required link to the adapter row above, checked before raw copying.
            'workflow':'fixture-workflow',
            'final_csv_sha256':value,'artifact_manifest_sha256':'manifest-fixture',
            'artifacts':{'outputs/raw/fixture/final.csv':value}}}}
        return source,view,out,target,runs,receipt

    def test_wave_links_materialize_verified_fresh_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source,view,out,target,runs,receipt = self.wave_fixture(root)
            prepare.materialize_wave_inputs(out,root/'private',root/'fresh',runs,receipt)
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_bytes(),source.read_bytes())
            rows = json.loads((out/'input_receipts.json').read_bytes())
            self.assertTrue(rows[0]['materialized'])
            self.assertEqual(rows[0]['source_realpath'],str(source.resolve()))
            self.assertEqual(rows[0]['target_sha256'],hashed(target.read_bytes()))
            self.assertIn('fixture/final.csv',prepare.assert_closed_files(out))
            source.write_bytes(b'changed after materialization')
            self.assertNotEqual(target.read_bytes(),source.read_bytes())

    def test_wave_identical_bytes_wrong_origin_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source,view,out,target,runs,receipt = self.wave_fixture(root)
            unrelated = root/'unrelated.csv'
            unrelated.write_bytes(source.read_bytes())
            target.unlink()
            target.symlink_to(unrelated)
            with self.assertRaises(ValueError):
                prepare.materialize_wave_inputs(out,root/'private',root/'fresh',runs,receipt)
            self.assertTrue(target.is_symlink())

    def test_wave_changed_raw_hash_preserves_failed_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source,view,out,target,runs,receipt = self.wave_fixture(root)
            source.write_bytes(b'wrong fresh bytes')
            with self.assertRaises(ValueError):
                prepare.materialize_wave_inputs(out,root/'private',root/'fresh',runs,receipt)
            self.assertTrue(target.is_symlink())
            self.assertTrue(target.with_name('final.csv.materializing').is_file())
            self.assertFalse((out/'sha256.json').exists())

    def test_closed_collection_rejects_linked_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out,external = root/'out',root/'external'
            out.mkdir()
            external.mkdir()
            (external/'file').write_bytes(b'outside')
            (out/'external').symlink_to(external,target_is_directory=True)
            with self.assertRaises(ValueError):
                prepare.assert_closed_files(out)

    def test_capture_parse_hash_copy_use_same_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'live.json'
            captured = b'{ "generation": 1 }\n'
            source.write_bytes(captured)
            cap = collector.MetadataCapture.take([source])
            self.assertEqual(cap.parsed(source),{'generation':1})
            source.write_bytes(b'{"generation":2}\n')
            out = root/'copy'
            out.mkdir()
            record = cap.export(out,{source:'copied.json'},lambda p:str(p))
            self.assertEqual((out/'copied.json').read_bytes(),captured)
            self.assertEqual(record['files'][str(source)]['sha256'],hashed(captured))
            with self.assertRaises(collector.CaptureChanged):
                cap.unchanged()
            self.assertFalse(record['final_unchanged_check']['passed'])

    def test_capture_retries_unstable_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'metadata.json'
            source.write_bytes(b'{}')
            real = collector.read_once
            calls = []
            def unstable(path):
                calls.append(path)
                if len(calls) == 1:
                    raise collector.CaptureChanged('injected publication race')
                return real(path)
            with mock.patch.object(collector,'read_once',side_effect=unstable):
                cap = collector.MetadataCapture.take([source],attempts=3)
            self.assertEqual([a['outcome'] for a in cap.attempts],['CaptureChanged','stable'])
            self.assertTrue(cap.unchanged()['passed'])

    def test_capture_bounded_failure_never_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'metadata.json'
            source.write_bytes(b'{}')
            with mock.patch.object(collector,'read_once',
                                   side_effect=collector.CaptureChanged('injected')) as reader:
                with self.assertRaises(collector.CaptureChanged):
                    collector.MetadataCapture.take([source],attempts=3)
            self.assertEqual(reader.call_count,3)
            self.assertEqual({p.name for p in Path(tmp).iterdir()},{'metadata.json'})

    def test_capture_retries_semantically_incoherent_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'metadata.json'
            source.write_bytes(b'{}')
            calls = []
            def validate(data):
                calls.append(data)
                if len(calls) == 1:
                    raise collector.CaptureChanged('checkpoint/run mismatch')
            cap = collector.MetadataCapture.take([source],validate=validate)
            self.assertEqual(len(cap.attempts),2)
            self.assertTrue(cap.unchanged()['passed'])

    def test_capture_late_optional_metadata_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source,late = root/'plan.json',root/'runtime.json'
            source.write_bytes(b'{}')
            def expand(data):
                return [late] if late.exists() else []
            cap = collector.MetadataCapture.take([source],expand)
            late.write_bytes(b'{}')
            with self.assertRaises(collector.CaptureChanged):
                cap.unchanged()

    def test_capture_copy_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'original.json'
            source.write_bytes(b'{"observed":1}')
            cap = collector.MetadataCapture.take([source])
            out = root/'out'
            out.mkdir()
            record = cap.export(out,{source:'copied.json'},lambda p:str(p))
            (out/'copied.json').write_bytes(b'{"observed":2}')
            self.assertTrue(cap.unchanged()['passed'])
            with self.assertRaises(ValueError):
                collector.verify_capture_copies(out,record)

    def test_private_view_uses_captured_metadata_and_actual_staged_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original,view = root/'original',root/'private'
            case = original/'case-0000'
            case.mkdir(parents=True)
            expected = hashed(b'actual staged part')
            (case/'payload.json').write_text(json.dumps({'input_sha256':{'part.bin':expected}}))
            (case/'part.bin').write_bytes(b'actual staged part')
            (original/'plan.json').write_text(json.dumps({'cases':[
                {'directory':'case-0000','specification':{'config':{'name':'fixture'}}}]}))
            raw = original/'raw/fixture/final.csv'
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b'actual fresh raw fixture')
            output = original/'download/case-0000/outputs'
            output.mkdir(parents=True)
            (output/'artifacts.sha256.json').write_bytes(b'{}')
            paths = [original/'plan.json',case/'payload.json',output/'artifacts.sha256.json']
            cap = collector.MetadataCapture.take(paths)
            prepare.create_phase_view(cap,original,view)
            self.assertFalse((view/'case-0000/payload.json').is_symlink())
            self.assertTrue((view/'case-0000/part.bin').is_symlink())
            (case/'payload.json').write_bytes(b'{"changed":true}')
            self.assertNotEqual((view/'case-0000/payload.json').read_bytes(),
                                (case/'payload.json').read_bytes())
            (case/'part.bin').write_bytes(b'changed actual staged bytes')
            self.assertEqual((view/'case-0000/part.bin').read_bytes(),b'changed actual staged bytes')
            self.assertNotEqual(hashed((view/'case-0000/part.bin').read_bytes()),expected)
            self.assertEqual((view/'raw/fixture/final.csv').resolve(),raw.resolve())

    def test_command_start_failure_has_durable_attempt_and_logs(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(collector,'secret_values',return_value=[]):
            out = Path(tmp)
            journal = collector.CommandJournal(out)
            def start(argv,**kwargs):
                attempt = json.loads((out/'commands.json').read_bytes())[0]
                self.assertEqual(attempt['outcome'],'running')
                self.assertEqual(attempt['argv'],['missing-command'])
                self.assertTrue((out/attempt['stdout']['path']).is_file())
                raise FileNotFoundError('injected start failure')
            with mock.patch.object(collector.subprocess,'Popen',side_effect=start):
                with self.assertRaises(collector.CommandFailed):
                    journal.run('start-fixture',['missing-command'],out)
            row = json.loads((out/'commands.json').read_bytes())[0]
            self.assertEqual(row['outcome'],'start_failure')
            self.assertIsNone(row['returncode'])
            self.assertIsNotNone(row['finished_utc'])
            self.assertGreaterEqual(row['duration_seconds'],0.)
            for key in ('stdout','stderr'):
                self.assertEqual(row[key]['sha256'],hashed((out/row[key]['path']).read_bytes()))

    def test_command_timeout_retains_partial_logs_and_outcome(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(collector,'secret_values',return_value=[]):
            out = Path(tmp)
            journal = collector.CommandJournal(out)
            process = mock.Mock(returncode=-9)
            owner = mock_owner(process)
            process.communicate.side_effect = [subprocess.TimeoutExpired(['fixture'],.01),
                                               (b'partial stdout\n',b'partial stderr\n')]
            with mock.patch.object(collector,'OwnedCommand',return_value=owner):
                with self.assertRaises(collector.CommandFailed):
                    journal.run('timeout-fixture',['fixture'],out,timeout=.01)
            row = json.loads((out/'commands.json').read_bytes())[0]
            self.assertEqual(row['outcome'],'timeout')
            self.assertEqual(row['returncode'],-9)
            owner.cancel.assert_called_once_with()
            self.assertEqual((out/row['stdout']['path']).read_bytes(),b'partial stdout\n')
            self.assertEqual(row['stderr']['sha256'],hashed(b'partial stderr\n'))

    def test_real_host_timeout_is_finalized(self):
        # A tiny interpreter sleep is host metadata control, not a numerical case.
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(collector,'secret_values',return_value=[]):
            out = Path(tmp)
            journal = collector.CommandJournal(out)
            with self.assertRaises(collector.CommandFailed):
                journal.run('host-timeout',[sys.executable,'-c',
                    'import time; print("partial-host-log",flush=True); time.sleep(30)'],out,timeout=2)
            row = json.loads((out/'commands.json').read_bytes())[0]
            self.assertEqual(row['outcome'],'timeout')
            self.assertIsNotNone(row['finished_utc'])
            self.assertNotEqual(row['returncode'],0)
            self.assertIn(b'partial-host-log',(out/row['stdout']['path']).read_bytes())
            self.assertTrue(row['logs_closed'])
            self.assertTrue(row['ownership']['writers_stopped'])
            self.assertEqual(row['stdout']['sha256'],hashed((out/row['stdout']['path']).read_bytes()))

    def test_transport_receipt_redacts_secrets_preserves_requested_paths(self):
        secret = 'fixture-private-token-123456'
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(collector,'secret_values',return_value=[secret]):
            out = Path(tmp)
            journal = collector.CommandJournal(out,'transport_commands.json','transport_logs')
            process = mock.Mock(returncode=0)
            process.communicate.return_value = ((secret+'\nAuthorization: Bearer '+secret).encode(),b'')
            argv = ['fixture-client','download','-w','fixture-workflow','outputs/raw/fixture/final.csv']
            with mock.patch.object(collector,'OwnedCommand',return_value=mock_owner(process)):
                journal.run('download-fixture',argv,out,workflow='fixture-workflow',
                            requested_paths=['outputs/raw/fixture/final.csv'])
            row = json.loads((out/'transport_commands.json').read_bytes())[0]
            self.assertEqual(row['argv'],argv)
            self.assertEqual(row['workflow'],'fixture-workflow')
            self.assertEqual(row['requested_paths'],['outputs/raw/fixture/final.csv'])
            self.assertEqual(row['outcome'],'success')
            log = (out/row['stdout']['path']).read_text()
            self.assertNotIn(secret,log)
            self.assertIn('[REDACTED]',log)
            self.assertTrue(row['interpreter']['assertions_enabled'])

    def test_command_nonzero_retained_without_success(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(collector,'secret_values',return_value=[]):
            out = Path(tmp)
            journal = collector.CommandJournal(out)
            process = mock.Mock(returncode=7)
            process.communicate.return_value = (b'failed output',b'failed diagnostic')
            with mock.patch.object(collector,'OwnedCommand',return_value=mock_owner(process)):
                with self.assertRaises(collector.CommandFailed):
                    journal.run('nonzero-fixture',['fixture'],out)
            row = json.loads((out/'commands.json').read_bytes())[0]
            self.assertEqual((row['outcome'],row['returncode']),('nonzero',7))

    def test_exited_leader_pipe_descendant_interruption_is_closed(self):
        # Actual subprocesses, injected handled interruption only after the
        # primary leader has exited and its inherited-pipe writer is observed.
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(collector,'secret_values',return_value=[]):
            out = Path(tmp)
            journal = collector.CommandJournal(out)
            child = ('import os,time; from pathlib import Path; '
                     'print("pipe-holder-marker",flush=True); '
                     'Path("writer.pid").write_text(str(os.getpid())); time.sleep(30)')
            leader = ('import subprocess,sys; subprocess.Popen([sys.executable,"-c",'+repr(child)+']); '
                      'print("exited-leader-marker",flush=True)')
            real_start = collector.OwnedCommand.start
            def start(owner):
                process = real_start(owner)
                communicate = process.communicate
                first = True
                def interrupted(*args, **kwargs):
                    nonlocal first
                    if first:
                        first = False
                        deadline = time.monotonic()+8
                        while time.monotonic() < deadline:
                            if ((out/'writer.pid').exists()
                                    and collector.read(owner.path)['primary_returncode'] == 0):
                                raise KeyboardInterrupt('injected after actual leader exit')
                            time.sleep(.02)
                        raise AssertionError('Pipe-holding descendant/leader exit not observed')
                    return communicate(*args, **kwargs)
                process.communicate = interrupted
                return process
            with mock.patch.object(collector.OwnedCommand,'start',new=start):
                with self.assertRaises(collector.CommandFailed):
                    journal.run('exited-leader',[sys.executable,'-c',leader],out,timeout=15)
            row = collector.read(out/'commands.json')[0]
            self.assertEqual((row['outcome'],row['error_type']),('interrupted','KeyboardInterrupt'))
            self.assertTrue(row['logs_closed'])
            self.assertIsNotNone(row['finished_utc'])
            self.assertTrue(row['ownership']['writers_stopped'])
            self.assertIn(b'pipe-holder-marker',(out/row['stdout']['path']).read_bytes())
            members = collector.live_group_members()
            for node in collector.ownership_nodes(out/'command_ownership').values():
                self.assertFalse(members.get(node['guardian_pid']))
            self.assertNotIn(int((out/'writer.pid').read_text()),set().union(*members.values()))

    def test_outer_timeout_stops_separately_grouped_nested_writer(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(collector,'secret_values',return_value=[]):
            out = Path(tmp)
            journal = collector.CommandJournal(out)
            writer = ('import os,time; from pathlib import Path; '
                      'Path("nested-writer.pid").write_text(str(os.getpid())); '
                      'Path("nested-writer.ready").write_text("nested-writer-marker"); '
                      'print("nested-writer-marker",flush=True); time.sleep(30)')
            command = ('import sys; from pathlib import Path; sys.path.insert(0,'+repr(str(TOOLS))+'); '
                       'import collect_fresh_physics_reference_inputs as c; '
                       'print("outer-collector-marker",flush=True); '
                       'c.CommandJournal(Path("nested")).run("nested-transport",'
                       '[sys.executable,"-c",'+repr(writer)+'],Path.cwd(),timeout=25)')
            with self.assertRaises(collector.CommandFailed):
                journal.run('outer-collector',[sys.executable,'-c',command],out,timeout=8)
            row = collector.read(out/'commands.json')[0]
            self.assertEqual(row['outcome'],'timeout')
            self.assertTrue(row['logs_closed'])
            self.assertIn(b'outer-collector-marker',(out/row['stdout']['path']).read_bytes())
            self.assertEqual((out/'nested-writer.ready').read_text(),'nested-writer-marker')
            nodes = collector.ownership_nodes(out/'command_ownership')
            self.assertEqual(len(nodes),2)
            self.assertEqual(len({n['guardian_pid'] for n in nodes.values()}),2)
            self.assertEqual(sum(n['parent_id'] is not None for n in nodes.values()),1)
            members = collector.live_group_members()
            for node in nodes.values():
                self.assertTrue(node['writers_stopped'])
                self.assertFalse(members.get(node['guardian_pid']))
            # Killed nested collectors retain their durable unfinished attempt;
            # the outer timeout receipt supplies its external ownership evidence.
            nested = collector.read(out/'nested/commands.json')[0]
            self.assertEqual(nested['outcome'],'running')
            self.assertIsNone(nested['finished_utc'])
            self.assertNotIn(int((out/'nested-writer.pid').read_text()),set().union(*members.values()))

    def test_failure_envelope_preserves_first_metadata_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a,b,out = root/'a.json',root/'b.json',root/'collection'
            a.write_bytes(b'{"first":true}\n')
            b.write_bytes(b'{"second":true}\n')
            capture = collector.MetadataCapture.take([a,b])
            out.mkdir()
            real_write = Path.write_bytes
            def fail_second(path, data):
                if path == out/'b.json':
                    raise OSError('credential-bearing exception arguments must not be retained')
                return real_write(path,data)
            with self.assertRaises(OSError), mock.patch.object(Path,'write_bytes',new=fail_second):
                with collector.collection_failure_envelope(out) as attempt:
                    attempt['stage'] = 'capture_export'
                    capture.export(out,{a:'a.json',b:'b.json'},str)
            self.assertEqual((out/'a.json').read_bytes(),a.read_bytes())
            self.assertFalse((out/'b.json').exists())
            status = collector.read(out/'collection_status.json')
            self.assertEqual((status['status'],status['error_type']),('failed','OSError'))
            self.assertEqual(status['stage'],'capture_export')
            self.assertFalse(status['full_m1_accepted'])
            self.assertFalse(status['final_ai_output_review_passed'])
            self.assertNotIn('credential-bearing',(out/'collection_status.json').read_text())
            self.assertFalse((out/'sha256.json').exists())

    def test_failed_publication_invalidates_successful_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with self.assertRaises(OSError):
                with collector.collection_failure_envelope(out):
                    collector.write_json(out/'sha256.json',{'partial.txt':'fixture-not-an-evidence-packet'})
                    raise OSError('injected after manifest publication')
            self.assertFalse((out/'sha256.json').exists())
            self.assertTrue((out/'unfinished_sha256.json').is_file())
            self.assertEqual(collector.read(out/'collection_status.json')['status'],'failed')

    def test_uncertain_cleanup_retains_unfinished_attempt(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(collector,'secret_values',return_value=[]):
            out = Path(tmp)
            process = mock.Mock(returncode=None)
            process.communicate.side_effect = subprocess.TimeoutExpired(
                ['fixture'],.01,output=b'unfinished-log-marker\n')
            owner = mock_owner(process)
            owner.cancel.side_effect = collector.CleanupIncomplete('injected uncertain closure')
            owner.receipt.return_value = dict(state='active', writers_stopped=False)
            with self.assertRaises(collector.CleanupIncomplete), \
                    mock.patch.object(collector,'OwnedCommand',return_value=owner):
                with collector.collection_failure_envelope(out):
                    collector.CommandJournal(out).run('uncertain',['fixture'],out,timeout=.01)
            row = collector.read(out/'commands.json')[0]
            self.assertEqual(row['outcome'],'running')
            self.assertIsNone(row['finished_utc'])
            self.assertFalse(row['logs_closed'])
            self.assertTrue(row['external_evidence_required'])
            self.assertIsNone(row['stdout']['sha256'])
            self.assertIn(b'unfinished-log-marker',(out/row['stdout']['path']).read_bytes())
            self.assertTrue(collector.read(out/'collection_status.json')['external_evidence_required'])
            self.assertFalse((out/'sha256.json').exists())
            self.assertTrue(all(call.kwargs.get('timeout') is not None
                                for call in process.communicate.call_args_list))

    def test_failure_envelope_covers_journal_initialization(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'collection'
            out.mkdir()
            real_write = collector.write_json
            def fail_journal(path, value):
                if path.name == 'commands.json':
                    (out/'partial-metadata.json').write_bytes(b'{"retained":true}\n')
                    raise OSError('injected journal initialization failure')
                return real_write(path,value)
            with self.assertRaises(OSError), mock.patch.object(collector,'write_json',side_effect=fail_journal):
                with collector.collection_failure_envelope(out) as attempt:
                    attempt['stage'] = 'journal_initialization'
                    collector.CommandJournal(out)
            self.assertTrue((out/'partial-metadata.json').is_file())
            status = collector.read(out/'collection_status.json')
            self.assertEqual((status['status'],status['error_type']),('failed','OSError'))
            self.assertEqual(status['stage'],'journal_initialization')
            self.assertFalse((out/'sha256.json').exists())

    def test_optimized_flag_rejected_before_argument_or_output_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('prepare_final_evidence.py','collect_fresh_physics_reference_inputs.py'):
                result = subprocess.run([sys.executable,'-O',str(TOOLS/name),'--help'],cwd=tmp,
                    capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),timeout=30)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('optimized Python is forbidden',result.stderr)
                self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_pythonoptimize_environment_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('prepare_final_evidence.py','collect_fresh_physics_reference_inputs.py'):
                result = subprocess.run([sys.executable,str(TOOLS/name),'--help'],cwd=tmp,
                    capture_output=True,text=True,
                    env=dict(os.environ,PYTHONOPTIMIZE='1',PYTHONDONTWRITEBYTECODE='1'),timeout=30)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('optimized Python is forbidden',result.stderr)
                self.assertEqual(list(Path(tmp).iterdir()),[])


if __name__ == '__main__':
    unittest.main()
