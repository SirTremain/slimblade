"""Synthetic REA adapter tests: no firmware, compiler, models or network."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rea_bridge as rea


def archive_fixture(duplicate=False, symlink=False, missing=False):
    stream = io.BytesIO()
    names = list(rea.MEMBERS)
    if duplicate:
        names.append(names[0])
    if missing:
        names.pop()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name in names:
            data = name.encode()
            item = tarfile.TarInfo('package/' + name)
            item.size = len(data)
            if symlink:
                item.type = tarfile.SYMTYPE
                item.linkname = '/etc/passwd'
            archive.addfile(item, io.BytesIO(data))
        # Must never extract unrelated or traversal members.
        item = tarfile.TarInfo('../../unexpected')
        item.size = 1
        archive.addfile(item, io.BytesIO(b'x'))
    data = stream.getvalue()
    return data, {'bytes': len(data), 'sha256': rea.digest(data),
        'integrity': 'sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode()}


class FileTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='rea-unit-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_paths_reject_escape_and_symlinks(self):
        (self.root / 'alias').symlink_to('/tmp', target_is_directory=True)
        for path in ('../escape', '/tmp/escape', 'alias/escape', '.'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                rea.safe_path(self.root, path)
        self.assertEqual(rea.safe_path(self.root, 'safe/file'), self.root / 'safe/file')

    def test_tree_pins_bytes_executable_bit_and_internal_file_links(self):
        path = self.root / 'file'
        path.write_bytes(b'one')
        first = rea.tree_digest(self.root)
        path.write_bytes(b'two')
        self.assertNotEqual(first, rea.tree_digest(self.root))
        second = rea.tree_digest(self.root)
        path.chmod(0o700)
        self.assertNotEqual(second, rea.tree_digest(self.root))
        (self.root / 'link').symlink_to('file')
        rea.tree_digest(self.root)
        (self.root / 'bad').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):
            rea.tree_digest(self.root)

    def test_archive_exact_identity_and_only_selected_files(self):
        data, pin = archive_fixture()
        self.assertEqual(set(rea.archive_members(data, pin)), set(rea.MEMBERS))
        for field, value in [('bytes', 1), ('sha256', '0'*64), ('integrity', 'sha512-wrong')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                rea.archive_members(data, dict(pin, **{field: value}))
        for option in ('duplicate', 'symlink', 'missing'):
            data, pin = archive_fixture(**{option: True})
            with self.subTest(option=option), self.assertRaises(ValueError):
                rea.archive_members(data, pin)

    def install_fixture(self):
        data, pin = archive_fixture()
        (self.root / 'archive.tgz').write_bytes(data)
        pin.update(path='archive.tgz', version='fixture')
        config = {'schema_version': 1, 'adapter': 'saved-project-bridge-v1',
                  'archive': pin, 'bridge_directory': 'bridge'}
        (self.root / 'decomp/rea').mkdir(parents=True)
        (self.root / rea.CONFIG).write_text(json.dumps(config))
        return config

    def test_install_idempotent_and_changed_bridge_rejected(self):
        config = self.install_fixture()
        with patch.object(rea.subprocess, 'run') as run, patch.object(rea.urllib.request, 'urlopen') as net:
            self.assertEqual(rea.install(self.root)['status'], 'installed-bridge-only')
            self.assertEqual(rea.install(self.root)['status'], 'already-installed')
            run.assert_not_called()
            net.assert_not_called()
        (self.root / 'bridge/LICENSE').write_text('modified')
        with self.assertRaises(ValueError):
            rea.verify_bridge(self.root, config)

    def test_missing_archive_never_implicitly_fetches(self):
        self.install_fixture()
        (self.root / 'archive.tgz').unlink()
        with patch.object(rea.urllib.request, 'urlopen') as net, self.assertRaises(ValueError):
            rea.install(self.root)
        net.assert_not_called()

    def test_unexpected_directory_symlink_in_bridge_is_rejected(self):
        config = self.install_fixture()
        rea.install(self.root)
        (self.root / 'bridge/extra').symlink_to('/tmp', target_is_directory=True)
        with self.assertRaises(ValueError):
            rea.verify_bridge(self.root, config)

    def test_changed_input_pin_stops_before_process_execution(self):
        config = self.install_fixture()
        rea.install(self.root)
        config['files'] = {'fixture': {'path': 'archive.tgz', 'sha256': '0'*64}}
        with patch.object(rea, 'load_config', return_value=config), \
                patch.object(rea.subprocess, 'run') as run, self.assertRaises(ValueError):
            rea.check(self.root)
        run.assert_not_called()

    def test_endpoint_stops_process_before_cleanup_even_on_error(self):
        seen = []
        with self.assertRaises(RuntimeError):
            with rea.endpoint_directory(lambda: seen.append(endpoint.exists())) as endpoint:
                raise RuntimeError('fixture')
        self.assertEqual(seen, [True])
        self.assertFalse(endpoint.exists())

    def observation_fixture(self):
        relative = '.decomp/rea/runs/fixture'
        directory = self.root / relative
        directory.mkdir(parents=True)
        observation = {'value': {'procedure': {'address': '0x10'}, 'pseudocode': 'hypothesis',
                                'limitations': ['dossier warning'],
                                'facet_availability': {'pseudocode': {'available': True}}},
                       'limitations': ['upstream warning'], 'relationship_coverage': {'status': 'partial'}}
        path = directory / '00000010-analyze_function.json'
        path.write_text(json.dumps(observation))
        report = {'status': 'observed', 'source_project_unchanged': True,
                  'record_kind': 'local-rea-bridge-observations-not-upstream-evidence',
                  'admission': {'sha256': 'a'*64}, 'profile_sha256': 'b'*64,
                  'limitations': ['adapter warning'], 'observations': [
                      {'entry': '0x10', 'method': 'analyze_function', 'path': path.name,
                       'sha256': rea.digest(path.read_bytes())}]}
        (directory / 'report.json').write_text(json.dumps(report))
        return relative, path, report

    def test_retained_view_preserves_caveats_without_reanalysis(self):
        relative, _, _ = self.observation_fixture()
        with patch.object(rea.subprocess, 'Popen') as start:
            view = rea.inspect(self.root, relative, '0x10', 'pseudocode')
            start.assert_not_called()
        self.assertEqual(view['value'], 'hypothesis')
        self.assertEqual(view['dossier_limitations'], ['dossier warning'])
        self.assertEqual(view['upstream_limitations'], ['upstream warning'])
        self.assertEqual(view['adapter_limitations'], ['adapter warning'])
        self.assertEqual(view['relationship_coverage']['status'], 'partial')
        self.assertFalse(view['certified_match'])
        self.assertIn('facets', rea.inspect(self.root, relative, '0x10')['value'])

    def test_retained_view_rejects_changes_failed_runs_and_missing_entries(self):
        relative, path, report = self.observation_fixture()
        with self.assertRaises(ValueError):
            rea.inspect(self.root, relative, '0x11')
        report['status'] = 'failed'
        (path.parent / 'report.json').write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            rea.inspect(self.root, relative, '0x10')
        report['status'] = 'observed'
        (path.parent / 'report.json').write_text(json.dumps(report))
        path.write_text('{}')
        with self.assertRaises(ValueError):
            rea.inspect(self.root, relative, '0x10')


class ProtocolTests(unittest.TestCase):
    def test_selection_is_bounded_exact_unique_inventory_entries(self):
        inventory = {'functions': [{'entry': '0x10'}]}
        self.assertEqual(rea.selected_entries(['0x10'], inventory), [16])
        for values in ([], ['16'], ['0x11'], ['0x10']*2, ['0x10']*9):
            with self.subTest(values=values), self.assertRaises(ValueError):
                rea.selected_entries(values, inventory)

    def test_method_specific_parameters(self):
        self.assertEqual(rea.query_params('analyze_function', 'stock', 16), {'procedure': '0x10'})
        self.assertEqual(rea.query_params('procedure_references', 'stock', 16),
                         {'procedure': '0x10', 'document': 'stock', 'direction': 'outgoing'})
        self.assertEqual(rea.query_params('read_function_instructions', 'stock', 16),
                         {'procedure': '0x10', 'document': 'stock'})
        with self.assertRaises(ValueError):
            rea.query_params('annotate_native_function', 'stock', 16)

    def client(self, reply, deadline=None):
        connection = Mock()
        connection.makefile.return_value = io.BytesIO(reply)
        client = rea.Bridge(connection, 'secret-fixture', deadline or time.monotonic()+10)
        self.addCleanup(client.close)
        return client, connection

    def test_readonly_allowlist_and_wire_identity(self):
        client, connection = self.client(b'{"id":1,"ok":true,"result":{"fixture":true}}\n')
        for method in ('set_address_name', 'annotate_native_function', 'apply_patch', 'arbitrary'):
            with self.assertRaises(ValueError):
                client.call(method, {})
        connection.sendall.assert_not_called()
        self.assertEqual(client.call('ping', {}), {'fixture': True})
        request = json.loads(connection.sendall.call_args.args[0])
        self.assertEqual(request, {'id': 1, 'token': 'secret-fixture', 'method': 'ping', 'params': {}})

    def test_invalid_oversized_truncated_and_rejected_replies(self):
        for reply in (b'{"id":2,"ok":true,"result":{}}\n', b'{}', b'x'*128+b'\n',
                      b'{"id":1,"ok":false,"error":{"message":"secret-fixture"}}\n'):
            client, _ = self.client(reply)
            with self.subTest(reply=reply[:20]), patch.object(rea, 'MAX_REPLY', 100):
                with self.assertRaises(ValueError) as error:
                    client.call('ping', {})
                self.assertNotIn('secret-fixture', str(error.exception))

    def test_expired_request_is_never_sent(self):
        client, connection = self.client(b'', time.monotonic()-1)
        with self.assertRaises(ValueError):
            client.call('ping', {})
        connection.sendall.assert_not_called()

    def test_handshake_preserves_truthful_upstream_mutability(self):
        config = {'baseline_sha256': 'a'*64, 'program': 'stock'}
        value = {'target': {'sha256': 'a'*64, 'name': 'stock', 'language_id': 'ARM:LE:32:v5t',
                           'compiler_spec_id': 'default'},
                 'provider': {'id': 'ghidra', 'version': '12.1.4'}, 'profile_digest': 'profile',
                 'run_id': 'run', 'analysis_timed_out': False, 'capabilities': list(rea.METHODS),
                 'read_only': False}
        rea.validate_handshake(value, config, 'profile', 'run')
        self.assertFalse(value['read_only'])
        for field, changed in [('run_id', 'other'), ('profile_digest', 'other'),
                               ('analysis_timed_out', True), ('capabilities', [])]:
            bad = copy.deepcopy(value)
            bad[field] = changed
            with self.subTest(field=field), self.assertRaises(ValueError):
                rea.validate_handshake(bad, config, 'profile', 'run')
        value['target']['language_id'] = 'ARM:LE:32:v7'
        with self.assertRaises(ValueError):
            rea.validate_handshake(value, config, 'profile', 'run')


class SandboxTests(unittest.TestCase):
    def test_corrected_project_not_generic_import_or_real_home(self):
        config = rea.load_config(ROOT)
        command = rea.sandbox_command(ROOT, config, Path('/tmp/fixture/work'), Path('/tmp/fixture/endpoint'))
        self.assertIn('--unshare-all', command)
        self.assertIn('--clearenv', command)
        self.assertIn('-readOnly', command)
        self.assertIn('-noanalysis', command)
        self.assertNotIn('-import', command)
        self.assertNotIn('--share-net', command)
        self.assertNotIn('--dev-bind', command)
        self.assertNotIn(str(ROOT), command)
        self.assertNotIn(str(ROOT / config['trees']['project']['path']), command)
        self.assertEqual(command.count('CheckReaProject.java'), 2)
        self.assertEqual(command[command.index('--dev')+1], '/dev')
        self.assertNotIn('ReaGhidraPrepareRaw.java', command)

    def test_pinned_checker_is_current(self):
        for name in ('checker', 'hosts'):
            pin = rea.load_config(ROOT)['files'][name]
            self.assertEqual(rea.digest((ROOT / pin['path']).read_bytes()), pin['sha256'])

    def test_watchdog_kills_overdue_child(self):
        process = Mock()
        with patch.object(rea, 'stop') as stop:
            guard = rea.RunGuard(process, Mock(), time.monotonic()-1)
            guard.thread.join(timeout=2)
            guard.close()
            self.assertEqual(guard.violation, 'REA run deadline exceeded')
            stop.assert_called_once_with(process)

    def test_watchdog_kills_excessive_log(self):
        process, log = Mock(), Mock()
        log.stat.return_value.st_size = rea.MAX_REPLY+1
        with patch.object(rea, 'stop') as stop:
            guard = rea.RunGuard(process, log, time.monotonic()+10)
            guard.thread.join(timeout=2)
            guard.close()
            self.assertEqual(guard.violation, 'Ghidra log limit exceeded')
            stop.assert_called_once_with(process)


if __name__ == '__main__':
    unittest.main()
