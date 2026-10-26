"""Synthetic publication boundaries; no native clients or model calls."""
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import integrations, manager_store, setup


class SetupPublicationRecordTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='setup-publication-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        setup.apply(self.root, 'claude', edition='mcp')
        self.config = self.root / '.mcp.json'
        self.receipt = self.root / setup.MANIFEST_PATH
        self.before = self.config.read_bytes(), self.receipt.read_bytes()
        self.python = sys.executable
        changed = patch.object(integrations.sys, 'executable', sys.executable + '-synthetic-moved')
        changed.start()
        self.addCleanup(changed.stop)

    def apply(self):
        return setup.apply(self.root, 'claude', edition='mcp', upgrade=True)

    def replace_foreign(self, content):
        foreign = self.root / 'foreign'
        foreign.write_bytes(content)
        identity = setup._identity(foreign)
        os.replace(foreign, self.config)
        return identity

    def test_interrupt_after_update_helper_return_restores_pair(self):
        original = setup._replace
        interrupted = False
        def after(project, relative, *args):
            nonlocal interrupted
            result = original(project, relative, *args)
            if relative == '.mcp.json' and not interrupted:
                interrupted = True
                raise KeyboardInterrupt('synthetic helper return')
            return result
        with patch.object(setup, '_replace', after), self.assertRaises(KeyboardInterrupt):
            self.apply()
        self.assertEqual((self.config.read_bytes(), self.receipt.read_bytes()), self.before)
        self.assertEqual(list(self.root.rglob('.coprogrammer-setup-*')), [])
        # Explicit user retry, not an automatic retry by setup.
        self.assertTrue(self.apply()['applied'])

    def test_io_error_after_update_helper_return_restores_pair(self):
        original = setup._replace
        failed = False
        def after(project, relative, *args):
            nonlocal failed
            result = original(project, relative, *args)
            if relative == '.mcp.json' and not failed:
                failed = True
                raise OSError('synthetic helper return')
            return result
        with patch.object(setup, '_replace', after), self.assertRaises(RuntimeError):
            self.apply()
        self.assertEqual((self.config.read_bytes(), self.receipt.read_bytes()), self.before)

    def test_same_content_foreign_replacement_after_update_is_preserved(self):
        original = setup._replace
        foreign = []
        def before_receipt(project, relative, *args):
            if relative == setup.MANIFEST_PATH:
                content = self.config.read_bytes()
                foreign.append((content, self.replace_foreign(content)))
                raise KeyboardInterrupt('synthetic receipt interruption')
            return original(project, relative, *args)
        with patch.object(setup, '_replace', before_receipt), self.assertRaises(KeyboardInterrupt):
            self.apply()
        self.assertEqual((self.config.read_bytes(), setup._identity(self.config)), foreign[0])
        self.assertEqual(self.receipt.read_bytes(), self.before[1])

    def test_foreign_replacement_while_rollback_stages_is_preserved(self):
        original, existing = setup._replace, setup._existing
        recovering = False
        foreign = []
        reads = 0
        def before_receipt(project, relative, *args):
            nonlocal recovering
            if relative == setup.MANIFEST_PATH:
                recovering = True
                raise KeyboardInterrupt('synthetic receipt interruption')
            return original(project, relative, *args)
        def race(target):
            nonlocal reads
            data = existing(target)
            if recovering and target == self.config:
                reads += 1
                if reads == 2:  # Final rollback helper content comparison.
                    foreign.append((data, self.replace_foreign(data)))
            return data
        with patch.object(setup, '_replace', before_receipt), patch.object(setup, '_existing', race), self.assertRaises(KeyboardInterrupt):
            self.apply()
        self.assertEqual(len(foreign), 1)
        self.assertEqual((self.config.read_bytes(), setup._identity(self.config)), foreign[0])
        self.assertEqual(self.receipt.read_bytes(), self.before[1])

    def test_failed_publication_does_not_claim_same_content_competitor(self):
        original = setup._replace
        foreign = []
        def before(project, relative, content, *args):
            if relative == '.mcp.json':
                foreign.append((content, self.replace_foreign(content)))
                raise KeyboardInterrupt('before our publication')
            return original(project, relative, content, *args)
        with patch.object(setup, '_replace', before), self.assertRaises(KeyboardInterrupt):
            self.apply()
        self.assertEqual((self.config.read_bytes(), setup._identity(self.config)), foreign[0])

    def test_unconfirmed_publication_inside_primitive_is_retained_for_inspection(self):
        original = manager_store._replace_event_log
        published = []
        def publish_then_interrupt(source, target):
            original(source, target)
            if target == self.config:
                published.append(self.config.read_bytes())
                raise KeyboardInterrupt('primitive did not return confirmation')
        with patch.object(manager_store, '_replace_event_log', publish_then_interrupt), self.assertRaises(KeyboardInterrupt):
            self.apply()
        self.assertEqual(self.config.read_bytes(), published[0])
        self.assertNotEqual(self.config.read_bytes(), self.before[0])
        self.assertEqual(self.receipt.read_bytes(), self.before[1])

    @unittest.skipUnless(os.name == 'posix', 'actual POSIX SIGINT; Windows not verified')
    def test_sigint_cli_after_helper_return_recovers_and_releases_lock(self):
        marker = self.root / 'ready'
        script = '''
import sys, threading
from pathlib import Path
from unittest.mock import patch
from coprogrammer import cli, setup, integrations
root = Path(sys.argv[1])
original = setup._replace
waited = False
def after(project, relative, *args):
    global waited
    result = original(project, relative, *args)
    if relative == '.mcp.json' and not waited:
        waited = True
        (root / 'ready').touch()
        if not threading.Event().wait(10):
            raise RuntimeError('no synthetic SIGINT received')
    return result
with patch.object(integrations.sys, 'executable', sys.executable + '-synthetic-moved'), patch.object(setup, '_replace', after):
    raise SystemExit(cli.main(['setup', '--client', 'claude', '--edition', 'mcp', '--upgrade', '--apply', '--cwd', str(root)]))
'''
        env = dict(os.environ, PYTHONPATH=str(Path(setup.__file__).resolve().parents[1]))
        child = subprocess.Popen([self.python, '-c', script, str(self.root)], cwd=self.root,
                                 env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 8
            while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(), 'CLI did not reach publication boundary')
            child.send_signal(signal.SIGINT)
            stdout, stderr = child.communicate(timeout=10)
            self.assertIn(child.returncode, (-signal.SIGINT, 130))
            self.assertEqual(stdout, b'')
            self.assertIn(b'KeyboardInterrupt', stderr)
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
        self.assertEqual((self.config.read_bytes(), self.receipt.read_bytes()), self.before)
        self.assertTrue(self.apply()['applied'])
