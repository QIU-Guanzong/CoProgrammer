"""Synthetic simultaneous cancellation/cleanup failures; no model calls."""
import errno
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import integrations, manager_store, setup


class SetupCleanupInterruptionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='setup-cleanup-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.config = self.root / '.mcp.json'
        self.receipt = self.root / setup.MANIFEST_PATH

    def apply(self):
        return setup.apply(self.root, 'claude', edition='mcp', upgrade=True)

    def test_create_preserves_interrupt_and_cleanup_cause_without_retry(self):
        interrupted = KeyboardInterrupt('synthetic cancellation')
        cleanup = OSError(errno.EACCES, 'synthetic cleanup failure')
        link, unlink = setup.os.link, Path.unlink
        publishes, cleanups = [], []
        def publish(source, destination):
            publishes.append(destination)
            if destination == self.receipt:
                raise interrupted
            return link(source, destination)
        def remove(path, *args, **kwargs):
            if path.parent == self.receipt.parent and path.name.startswith('.coprogrammer-setup-'):
                cleanups.append(path)
                raise cleanup
            return unlink(path, *args, **kwargs)
        with patch.object(setup.os, 'link', publish), patch.object(Path, 'unlink', remove), self.assertRaises(KeyboardInterrupt) as caught:
            self.apply()
        self.assertIs(caught.exception, interrupted)
        self.assertIs(caught.exception.__cause__, cleanup)
        self.assertEqual(publishes, [self.config, self.receipt])
        self.assertEqual(len(cleanups), 1)
        self.assertTrue(cleanups[0].is_file())
        self.assertFalse(self.config.exists())
        self.assertFalse(self.receipt.exists())

    def test_upgrade_recovers_old_pair_when_receipt_cleanup_fails(self):
        self.apply()
        before = self.config.read_bytes(), self.receipt.read_bytes()
        interrupted = KeyboardInterrupt('synthetic cancellation')
        cleanup = OSError(errno.EACCES, 'synthetic cleanup failure')
        replace, unlink = manager_store._replace_event_log, Path.unlink
        cleanups = []
        def publish(source, destination):
            if destination == self.receipt:
                raise interrupted
            return replace(source, destination)
        def remove(path, *args, **kwargs):
            if path.parent == self.receipt.parent and path.name.startswith('.coprogrammer-setup-'):
                cleanups.append(path)
                raise cleanup
            return unlink(path, *args, **kwargs)
        with patch.object(integrations.sys, 'executable', integrations.sys.executable + '-synthetic-moved'):
            with patch.object(manager_store, '_replace_event_log', publish), patch.object(Path, 'unlink', remove), self.assertRaises(KeyboardInterrupt) as caught:
                self.apply()
        self.assertIs(caught.exception, interrupted)
        self.assertIs(caught.exception.__cause__, cleanup)
        self.assertEqual((self.config.read_bytes(), self.receipt.read_bytes()), before)
        self.assertEqual(len(cleanups), 1)
        self.assertTrue(cleanups[0].is_file())

    def test_cleanup_error_without_interrupt_still_fails_application(self):
        unlink = Path.unlink
        cleanups = []
        def remove(path, *args, **kwargs):
            if path.name.startswith('.coprogrammer-setup-'):
                cleanups.append(path)
                raise OSError(errno.EACCES, 'synthetic ordinary cleanup failure')
            return unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', remove), self.assertRaises(RuntimeError) as caught:
            self.apply()
        self.assertIsInstance(caught.exception.__cause__, OSError)
        self.assertEqual(len(cleanups), 1)
        # The failed staging unlink leaves an observed alias. Retain both
        # names rather than infer that the shared inode is safe to remove.
        self.assertTrue(self.config.exists())
        self.assertEqual(setup._identity(self.config), setup._identity(cleanups[0]))
        self.assertEqual(self.config.read_bytes(), cleanups[0].read_bytes())
        self.assertEqual(self.config.stat().st_nlink, 2)
        self.assertFalse(self.receipt.exists())
        self.assertTrue(cleanups[0].is_file())

    def test_prior_interrupt_cause_or_context_remains_reachable(self):
        for upgrade in (False, True):
            for explicit in (False, True, None):
                with self.subTest(upgrade=upgrade, explicit=explicit), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    receipt = root / setup.MANIFEST_PATH
                    if upgrade:
                        setup.apply(root, 'claude', edition='mcp')
                    prior = ValueError('synthetic original reason')
                    interrupted = KeyboardInterrupt('synthetic cancellation')
                    cleanup = OSError(errno.EACCES, 'synthetic cleanup failure')
                    owner, method = (manager_store, '_replace_event_log') if upgrade else (setup.os, 'link')
                    publish, unlink = getattr(owner, method), Path.unlink
                    def interrupt(source, destination):
                        if destination == receipt:
                            try:
                                raise prior
                            except ValueError:
                                if explicit is None:
                                    raise interrupted from None
                                if explicit:
                                    raise interrupted from prior
                                raise interrupted
                        return publish(source, destination)
                    def remove(path, *args, **kwargs):
                        if path.parent == receipt.parent and path.name.startswith('.coprogrammer-setup-'):
                            raise cleanup
                        return unlink(path, *args, **kwargs)
                    with patch.object(integrations.sys, 'executable', integrations.sys.executable + '-synthetic-moved'):
                        with patch.object(owner, method, interrupt), patch.object(Path, 'unlink', remove), self.assertRaises(KeyboardInterrupt) as caught:
                            setup.apply(root, 'claude', edition='mcp', upgrade=True)
                    self.assertIs(caught.exception, interrupted)
                    self.assertIs(caught.exception.__cause__, cleanup)
                    self.assertIs(cleanup.__context__, None if explicit is None else prior)

    def test_second_interrupt_during_cleanup_still_stops_recovery(self):
        link, unlink = setup.os.link, Path.unlink
        first, second = KeyboardInterrupt('first'), KeyboardInterrupt('second')
        def publish(source, destination):
            if destination == self.receipt:
                raise first
            return link(source, destination)
        def remove(path, *args, **kwargs):
            if path.parent == self.receipt.parent and path.name.startswith('.coprogrammer-setup-'):
                raise second
            return unlink(path, *args, **kwargs)
        with patch.object(setup.os, 'link', publish), patch.object(Path, 'unlink', remove), self.assertRaises(KeyboardInterrupt) as caught:
            self.apply()
        self.assertIs(caught.exception, second)

    def test_combined_failure_does_not_erase_concurrent_user_edit(self):
        link, unlink = setup.os.link, Path.unlink
        def publish(source, destination):
            if destination == self.receipt:
                self.config.write_bytes(b'SYNTHETIC_USER_EDIT')
                raise KeyboardInterrupt
            return link(source, destination)
        def remove(path, *args, **kwargs):
            if path.parent == self.receipt.parent and path.name.startswith('.coprogrammer-setup-'):
                raise OSError(errno.EACCES, 'synthetic cleanup failure')
            return unlink(path, *args, **kwargs)
        with patch.object(setup.os, 'link', publish), patch.object(Path, 'unlink', remove), self.assertRaises(KeyboardInterrupt):
            self.apply()
        self.assertEqual(self.config.read_bytes(), b'SYNTHETIC_USER_EDIT')
        self.assertFalse(self.receipt.exists())

    @unittest.skipUnless(os.name == 'posix', 'actual POSIX SIGINT; Windows native signals unverified')
    def test_real_sigint_cli_exit_is_not_converted_to_write_failure(self):
        script = '''
import errno, signal, sys
from pathlib import Path
from unittest.mock import patch
from coprogrammer import cli, setup
root = Path(sys.argv[1])
receipt = root / setup.MANIFEST_PATH
link, unlink = setup.os.link, Path.unlink
def publish(source, destination):
    if destination == receipt:
        signal.raise_signal(signal.SIGINT)
    return link(source, destination)
def remove(path, *args, **kwargs):
    if path.parent == receipt.parent and path.name.startswith('.coprogrammer-setup-'):
        raise OSError(errno.EACCES, 'SYNTHETIC_CLEANUP_FAILURE')
    return unlink(path, *args, **kwargs)
with patch.object(setup.os, 'link', publish), patch.object(Path, 'unlink', remove):
    raise SystemExit(cli.main(['setup', '--client', 'claude', '--edition', 'mcp', '--apply', '--cwd', str(root)]))
'''
        env = dict(os.environ, PYTHONPATH=str(Path(setup.__file__).resolve().parents[1]))
        result = subprocess.run([sys.executable, '-c', script, str(self.root)],
                                cwd=self.root, env=env, capture_output=True, timeout=10)
        self.assertIn(result.returncode, (-signal.SIGINT, 130))
        self.assertEqual(result.stdout, b'')
        self.assertIn(b'KeyboardInterrupt', result.stderr)
        self.assertIn(b'SYNTHETIC_CLEANUP_FAILURE', result.stderr)
        self.assertFalse(self.config.exists())
        self.assertFalse(self.receipt.exists())
        self.assertEqual(len(list(self.root.rglob('.coprogrammer-setup-*'))), 1)
