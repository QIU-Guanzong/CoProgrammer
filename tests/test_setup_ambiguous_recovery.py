"""Synthetic ambiguous publication/ownership failures; no model calls."""
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


class SetupAmbiguousRecoveryTests(unittest.TestCase):
    def fixture(self, upgrade):
        directory = tempfile.TemporaryDirectory(prefix='setup-ambiguous-')
        self.addCleanup(directory.cleanup)
        root = Path(directory.name).resolve()
        if upgrade:
            setup.apply(root, 'claude', edition='mcp')
        return root

    def changed_client(self):
        return patch.object(integrations.sys, 'executable', sys.executable + '-synthetic-moved')

    def test_receipt_published_then_error_preserves_matching_files(self):
        for upgrade in (False, True):
            for error in (OSError, RuntimeError):
                with self.subTest(upgrade=upgrade, error=error):
                    root = self.fixture(upgrade)
                    receipt = root / setup.MANIFEST_PATH
                    owner, name = (manager_store, '_replace_event_log') if upgrade else (setup.os, 'link')
                    original = getattr(owner, name)
                    failure = error('synthetic error after successful publication')
                    def after(source, destination):
                        original(source, destination)
                        if destination == receipt:
                            raise failure
                    with self.changed_client(), patch.object(owner, name, after):
                        with self.assertRaises(RuntimeError) as caught:
                            setup.apply(root, 'claude', edition='mcp', upgrade=True)
                        self.assertIs(caught.exception.__cause__, failure)
                        plan = setup.preview(root, 'claude', edition='mcp', upgrade=True)
                        self.assertTrue(all(f['status'] == 'unchanged' for f in plan['files']))
                        self.assertTrue(plan['can_apply'])
                        self.assertTrue(receipt.exists())
                        self.assertIn('retained', str(caught.exception))

    def test_unreadable_receipt_after_io_error_preserves_outputs(self):
        for upgrade in (False, True):
            with self.subTest(upgrade=upgrade):
                root = self.fixture(upgrade)
                receipt, config = root / setup.MANIFEST_PATH, root / '.mcp.json'
                helper_name = '_replace' if upgrade else '_create'
                helper, existing = getattr(setup, helper_name), setup._existing
                failed = False
                published = []
                def fail(project, relative, *args):
                    nonlocal failed
                    if relative == setup.MANIFEST_PATH:
                        published.append(config.read_bytes())
                        failed = True
                        raise OSError('synthetic receipt failure')
                    return helper(project, relative, *args)
                def unknown(target):
                    if failed and target == receipt:
                        raise OSError('synthetic unreadable receipt')
                    return existing(target)
                with self.changed_client(), patch.object(setup, helper_name, fail), patch.object(setup, '_existing', unknown):
                    with self.assertRaises(RuntimeError) as caught:
                        setup.apply(root, 'claude', edition='mcp', upgrade=True)
                self.assertTrue(config.exists(), 'recovery removed output under an unknown receipt')
                self.assertEqual(config.read_bytes(), published[0])
                self.assertIn('retained', str(caught.exception))

    def test_unchanged_receipt_still_allows_normal_rollback(self):
        for upgrade in (False, True):
            with self.subTest(upgrade=upgrade):
                root = self.fixture(upgrade)
                config = root / '.mcp.json'
                before = config.read_bytes() if upgrade else None
                helper_name = '_replace' if upgrade else '_create'
                helper = getattr(setup, helper_name)
                def fail(project, relative, *args):
                    if relative == setup.MANIFEST_PATH:
                        raise OSError('synthetic failure before receipt publication')
                    return helper(project, relative, *args)
                with self.changed_client(), patch.object(setup, helper_name, fail):
                    with self.assertRaisesRegex(RuntimeError, 'rolled back'):
                        setup.apply(root, 'claude', edition='mcp', upgrade=True)
                self.assertEqual(config.read_bytes() if config.exists() else None, before)

    def test_relinked_target_with_surviving_alias_is_retained(self):
        for upgrade in (False, True):
            with self.subTest(upgrade=upgrade):
                root = self.fixture(upgrade)
                config, alias = root / '.mcp.json', root / 'foreign-alias'
                helper_name = '_replace' if upgrade else '_create'
                helper = getattr(setup, helper_name)
                expected = []
                def before_receipt(project, relative, *args):
                    if relative == setup.MANIFEST_PATH:
                        os.link(config, alias)
                        config.unlink()
                        os.link(alias, config)
                        expected.append((config.read_bytes(), setup._identity(config)))
                        raise KeyboardInterrupt('synthetic competing hard-link owner')
                    return helper(project, relative, *args)
                with self.changed_client(), patch.object(setup, helper_name, before_receipt):
                    with self.assertRaises(KeyboardInterrupt):
                        setup.apply(root, 'claude', edition='mcp', upgrade=True)
                self.assertTrue(config.exists(), 'recovery removed the competing name')
                self.assertEqual((config.read_bytes(), setup._identity(config)), expected[0])
                self.assertEqual((alias.read_bytes(), setup._identity(alias)), expected[0])

    def test_link_added_during_recovery_comparison_is_retained(self):
        for upgrade in (False, True):
            with self.subTest(upgrade=upgrade):
                root = self.fixture(upgrade)
                config, alias = root / '.mcp.json', root / 'foreign-alias'
                helper_name = '_replace' if upgrade else '_create'
                helper, existing = getattr(setup, helper_name), setup._existing
                recovering = False
                reads = 0
                expected = []
                def before_receipt(project, relative, *args):
                    nonlocal recovering
                    if relative == setup.MANIFEST_PATH:
                        recovering = True
                        raise KeyboardInterrupt('synthetic recovery')
                    return helper(project, relative, *args)
                def late_link(target):
                    nonlocal reads
                    data = existing(target)
                    if recovering and target == config:
                        reads += 1
                        if reads == (2 if upgrade else 1):
                            os.link(config, alias)
                            expected.append((data, setup._identity(config)))
                    return data
                with self.changed_client(), patch.object(setup, helper_name, before_receipt), patch.object(setup, '_existing', late_link):
                    with self.assertRaises(KeyboardInterrupt):
                        setup.apply(root, 'claude', edition='mcp', upgrade=True)
                self.assertEqual(len(expected), 1)
                self.assertTrue(config.exists(), 'recovery removed a shared target')
                self.assertEqual((config.read_bytes(), setup._identity(config)), expected[0])
                self.assertEqual(alias.read_bytes(), expected[0][0])

    @unittest.skipUnless(os.name == 'posix', 'POSIX SIGINT; Windows native signals unverified')
    def test_sigint_cli_retains_relinked_target_and_releases_lock(self):
        root = self.fixture(True)
        marker = root / 'ready'
        script = '''
import os, sys, threading
from pathlib import Path
from unittest.mock import patch
from coprogrammer import cli, integrations, setup
root = Path(sys.argv[1]); config = root / '.mcp.json'; alias = root / 'foreign-alias'
original = setup._replace
def before_receipt(project, relative, *args):
    if relative == setup.MANIFEST_PATH:
        os.link(config, alias); config.unlink(); os.link(alias, config)
        (root / 'ready').touch()
        if not threading.Event().wait(10):
            raise RuntimeError('no synthetic SIGINT received')
    return original(project, relative, *args)
with patch.object(integrations.sys, 'executable', sys.executable + '-synthetic-moved'), patch.object(setup, '_replace', before_receipt):
    raise SystemExit(cli.main(['setup', '--client', 'claude', '--edition', 'mcp', '--upgrade', '--apply', '--cwd', str(root)]))
'''
        env = dict(os.environ, PYTHONPATH=str(Path(setup.__file__).resolve().parents[1]))
        child = subprocess.Popen([sys.executable, '-c', script, str(root)], cwd=root,
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
        config, alias = root / '.mcp.json', root / 'foreign-alias'
        self.assertEqual((config.read_bytes(), setup._identity(config)), (alias.read_bytes(), setup._identity(alias)))
        # Acquire the same Manager lock without retrying any installation.
        from coprogrammer.cli import event_log_path
        with manager_store.transaction(event_log_path(root)):
            pass
