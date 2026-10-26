"""Synthetic installer interruptions; no native clients or model calls."""
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import integrations, setup


class SetupInterruptionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='setup-interrupt-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.config = self.root / '.mcp.json'
        self.receipt = self.root / setup.MANIFEST_PATH

    def apply(self):
        return setup.apply(self.root, 'claude', edition='mcp', upgrade=True)

    def test_interrupted_upgrade_restores_receipt_pair_and_allows_explicit_retry(self):
        self.apply()
        old_config, old_receipt = self.config.read_bytes(), self.receipt.read_bytes()
        replace = setup._replace
        def interrupt_receipt(root, relative, *args):
            if relative == setup.MANIFEST_PATH:
                raise KeyboardInterrupt
            return replace(root, relative, *args)
        with patch.object(integrations.sys, 'executable', integrations.sys.executable + '-synthetic-moved'):
            with patch.object(setup, '_replace', side_effect=interrupt_receipt), self.assertRaises(KeyboardInterrupt):
                self.apply()
            self.assertEqual(self.config.read_bytes(), old_config)
            self.assertEqual(self.receipt.read_bytes(), old_receipt)
            self.assertTrue(setup.preview(self.root, 'claude', edition='mcp', upgrade=True)['can_apply'])
            self.assertTrue(self.apply()['applied'])
            self.assertNotEqual(self.config.read_bytes(), old_config)
        self.assertEqual(list(self.root.rglob('.coprogrammer-setup-*')), [])

    def test_interrupted_new_install_removes_only_completed_owned_files(self):
        link = setup.os.link
        def interrupt_receipt(source, target):
            if target == self.receipt:
                raise KeyboardInterrupt
            return link(source, target)
        with patch.object(setup.os, 'link', side_effect=interrupt_receipt), self.assertRaises(KeyboardInterrupt):
            self.apply()
        self.assertFalse(self.config.exists())
        self.assertFalse(self.receipt.exists())
        self.assertEqual(list(self.root.rglob('.coprogrammer-setup-*')), [])
        self.assertTrue(self.apply()['applied'])

    def test_interruption_preserves_external_edits_and_replacements(self):
        for replace_identical in (False, True):
            with self.subTest(replace_identical=replace_identical), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                target = root / '.mcp.json'
                link = setup.os.link
                expected = []
                def interrupt_receipt(source, destination):
                    if destination == root / setup.MANIFEST_PATH:
                        if replace_identical:
                            data = target.read_bytes()
                            replacement = root / 'replacement'
                            replacement.write_bytes(data)
                            os.replace(replacement, target)
                        else:
                            data = b'SYNTHETIC_USER_EDIT'
                            target.write_bytes(data)
                        expected.append(data)
                        raise KeyboardInterrupt
                    return link(source, destination)
                with patch.object(setup.os, 'link', side_effect=interrupt_receipt), self.assertRaises(KeyboardInterrupt):
                    setup.apply(root, 'claude', edition='mcp')
                self.assertEqual(target.read_bytes(), expected[0])
                self.assertFalse((root / setup.MANIFEST_PATH).exists())

    def test_interrupted_upgrade_preserves_user_edit_and_old_receipt(self):
        self.apply()
        old_receipt = self.receipt.read_bytes()
        replace = setup._replace
        def interrupt_receipt(root, relative, *args):
            if relative == setup.MANIFEST_PATH:
                self.config.write_bytes(b'SYNTHETIC_USER_EDIT')
                raise KeyboardInterrupt
            return replace(root, relative, *args)
        with patch.object(integrations.sys, 'executable', integrations.sys.executable + '-synthetic-moved'):
            with patch.object(setup, '_replace', side_effect=interrupt_receipt), self.assertRaises(KeyboardInterrupt):
                self.apply()
            self.assertEqual(self.config.read_bytes(), b'SYNTHETIC_USER_EDIT')
            self.assertEqual(self.receipt.read_bytes(), old_receipt)
            self.assertFalse(setup.preview(self.root, 'claude', edition='mcp', upgrade=True)['can_apply'])

    def test_interrupt_after_receipt_publication_preserves_committed_pair(self):
        for upgrade in (False, True):
            with self.subTest(upgrade=upgrade), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                if upgrade:
                    setup.apply(root, 'claude', edition='mcp')
                helper_name = '_replace' if upgrade else '_create'
                helper = getattr(setup, helper_name)
                def publish_then_interrupt(root, relative, *args):
                    result = helper(root, relative, *args)
                    if relative == setup.MANIFEST_PATH:
                        raise KeyboardInterrupt
                    return result
                with patch.object(integrations.sys, 'executable', integrations.sys.executable + '-synthetic-moved'):
                    with patch.object(setup, helper_name, side_effect=publish_then_interrupt), self.assertRaises(KeyboardInterrupt):
                        setup.apply(root, 'claude', edition='mcp', upgrade=True)
                    plan = setup.preview(root, 'claude', edition='mcp', upgrade=True)
                    self.assertTrue(plan['can_apply'])
                    self.assertTrue(all(item['status'] == 'unchanged' for item in plan['files']))
                    self.assertTrue((root / setup.MANIFEST_PATH).exists())

    def test_unknown_receipt_state_preserves_completed_writes(self):
        link, existing = setup.os.link, setup._existing
        interrupted = False
        def interrupt_receipt(source, destination):
            nonlocal interrupted
            if destination == self.receipt:
                interrupted = True
                raise KeyboardInterrupt
            return link(source, destination)
        def unavailable(target):
            if interrupted and target == self.receipt:
                raise OSError('synthetic unreadable receipt')
            return existing(target)
        with patch.object(setup.os, 'link', side_effect=interrupt_receipt), \
                patch.object(setup, '_existing', side_effect=unavailable), self.assertRaises(KeyboardInterrupt):
            self.apply()
        self.assertTrue(self.config.is_file())
        self.assertFalse(self.receipt.exists())

    def test_second_interrupt_during_recovery_is_not_swallowed(self):
        self.apply()
        old_config = self.config.read_bytes()
        replace = setup._replace
        interrupted = False
        calls = []
        def interrupt(root, relative, *args):
            nonlocal interrupted
            calls.append(relative)
            if relative == setup.MANIFEST_PATH:
                interrupted = True
                raise KeyboardInterrupt('first')
            if interrupted:
                raise KeyboardInterrupt('second')
            return replace(root, relative, *args)
        with patch.object(integrations.sys, 'executable', integrations.sys.executable + '-synthetic-moved'):
            with patch.object(setup, '_replace', side_effect=interrupt), self.assertRaisesRegex(KeyboardInterrupt, 'second'):
                self.apply()
        self.assertEqual(calls, ['.mcp.json', setup.MANIFEST_PATH, '.mcp.json'])
        self.assertNotEqual(self.config.read_bytes(), old_config)

    @unittest.skipUnless(os.name == 'posix', 'actual POSIX SIGINT; Windows native signals not verified')
    def test_sigint_cli_restores_upgrade_and_releases_manager_lock(self):
        self.apply()
        before = self.config.read_bytes(), self.receipt.read_bytes()
        marker = self.root / 'ready'
        script = '''
import sys, threading
from pathlib import Path
from unittest.mock import patch
from coprogrammer import cli, integrations, setup
root = Path(sys.argv[1])
replace = setup._replace
def wait_for_interrupt(project, relative, *args):
    if relative == setup.MANIFEST_PATH:
        (root / 'ready').touch()
        if not threading.Event().wait(10):
            raise RuntimeError('fixture did not receive SIGINT')
    return replace(project, relative, *args)
with patch.object(integrations.sys, 'executable', sys.executable + '-synthetic-moved'), patch.object(setup, '_replace', side_effect=wait_for_interrupt):
    raise SystemExit(cli.main(['setup', '--client', 'claude', '--edition', 'mcp', '--upgrade', '--apply', '--cwd', str(root)]))
'''
        env = dict(os.environ, PYTHONPATH=str(Path(setup.__file__).resolve().parents[1]))
        process = subprocess.Popen([sys.executable, '-c', script, str(self.root)],
                                   cwd=self.root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 8
            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(), 'synthetic CLI did not reach receipt boundary')
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=10)
            self.assertIn(process.returncode, (-signal.SIGINT, 130))
            self.assertEqual(stdout, b'')
            self.assertIn(b'KeyboardInterrupt', stderr)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
        self.assertEqual((self.config.read_bytes(), self.receipt.read_bytes()), before)
        self.assertEqual(list(self.root.rglob('.coprogrammer-setup-*')), [])
        self.assertTrue(self.apply()['applied'])
