"""Synthetic staging pathname replacement; no clients/accounts are invoked."""
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import setup, manager_store


class SetupStagingOwnershipTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='setup-staging-owner-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.target = self.root / 'target'
        self.target.write_bytes(b'old')

    def test_replaced_temporary_name_is_preserved_for_different_and_identical_bytes(self):
        for content in (b'foreign', b'new'):
            with self.subTest(content=content):
                observed = []
                def replace(path, mode):
                    temporary = Path(path)
                    foreign = self.root / 'foreign'
                    foreign.write_bytes(content)
                    identity = setup._identity(foreign)
                    os.replace(foreign, temporary)
                    observed.append((temporary, identity))
                    raise OSError('synthetic staging boundary')
                with patch.object(setup.os, 'chmod', replace), self.assertRaises(OSError):
                    setup._replace(self.root, 'target', b'new', b'old', 0o600)
                temporary, identity = observed[0]
                self.assertTrue(temporary.exists(), 'foreign staging name was removed')
                self.assertEqual((temporary.read_bytes(), setup._identity(temporary)), (content, identity))
                self.assertEqual(self.target.read_bytes(), b'old')

    @unittest.skipUnless(os.name == 'posix', 'symlink fixture requires POSIX support')
    def test_symlink_replacing_staging_name_is_preserved(self):
        foreign = self.root / 'foreign'
        foreign.write_bytes(b'foreign')
        observed = []
        def replace(path, mode):
            temporary = Path(path)
            link = self.root / 'incoming-link'
            link.symlink_to(foreign)
            os.replace(link, temporary)
            observed.append(temporary)
            raise KeyboardInterrupt('synthetic staging boundary')
        with patch.object(setup.os, 'chmod', replace), self.assertRaises(KeyboardInterrupt):
            setup._replace(self.root, 'target', b'new', b'old', 0o600)
        self.assertTrue(observed[0].is_symlink())
        self.assertEqual(foreign.read_bytes(), b'foreign')
        self.assertEqual(self.target.read_bytes(), b'old')

    def test_unavailable_staged_identity_retains_unconfirmed_name(self):
        with patch.object(setup.os, 'fstat', side_effect=OSError('synthetic identity unavailable')):
            with self.assertRaises(OSError):
                setup._replace(self.root, 'target', b'new', b'old', 0o600)
        self.assertEqual(len(list(self.root.glob('.coprogrammer-setup-*'))), 1)
        self.assertEqual(self.target.read_bytes(), b'old')

    def test_owned_temporary_file_still_cleaned_on_normal_failure(self):
        with patch.object(setup.os, 'chmod', side_effect=OSError('synthetic staging failure')):
            with self.assertRaises(OSError):
                setup._replace(self.root, 'target', b'new', b'old', 0o600)
        self.assertEqual(list(self.root.glob('.coprogrammer-setup-*')), [])
        self.assertEqual(self.target.read_bytes(), b'old')

    @unittest.skipUnless(os.name == 'posix', 'actual POSIX SIGINT; Windows native unverified')
    def test_cli_sigint_preserves_foreign_staging_and_releases_lock(self):
        setup.apply(self.root, 'claude', edition='mcp')
        config, receipt = self.root / '.mcp.json', self.root / setup.MANIFEST_PATH
        before = config.read_bytes(), receipt.read_bytes()
        marker = self.root / 'ready'
        script = '''
import os, sys, threading
from pathlib import Path
from unittest.mock import patch
from coprogrammer import cli, setup, integrations
root = Path(sys.argv[1]); original = os.chmod; replaced = False
def boundary(path, mode):
    global replaced
    if not replaced:
        replaced = True
        foreign = root / 'foreign'
        foreign.write_bytes(b'synthetic foreign staging')
        os.replace(foreign, path)
        (root / 'ready').write_text(str(path))
        if not threading.Event().wait(10):
            raise RuntimeError('no synthetic SIGINT received')
    return original(path, mode)
with patch.object(integrations.sys, 'executable', sys.executable + '-synthetic-moved'), patch.object(setup.os, 'chmod', boundary):
    raise SystemExit(cli.main(['setup', '--client', 'claude', '--edition', 'mcp', '--upgrade', '--apply', '--cwd', str(root)]))
'''
        env = dict(os.environ, PYTHONPATH=str(Path(setup.__file__).resolve().parents[1]))
        child = subprocess.Popen([sys.executable, '-c', script, str(self.root)], cwd=self.root,
                                 env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 8
            while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists())
            child.send_signal(signal.SIGINT)
            stdout, stderr = child.communicate(timeout=10)
            self.assertIn(child.returncode, (-signal.SIGINT, 130))
            self.assertEqual(stdout, b'')
            self.assertIn(b'KeyboardInterrupt', stderr)
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
        temporary = Path(marker.read_text())
        self.assertTrue(temporary.exists(), 'CLI cleanup removed foreign staging')
        self.assertEqual(temporary.read_bytes(), b'synthetic foreign staging')
        self.assertEqual((config.read_bytes(), receipt.read_bytes()), before)
        from coprogrammer.cli import event_log_path
        with manager_store.transaction(event_log_path(self.root)):
            pass
