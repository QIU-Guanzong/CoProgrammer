"""Synthetic installer-owned writes only; no clients, accounts or real models."""
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import setup


class AtomicSetupCreateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='setup-create-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.first = self.root / '.mcp.json'

    def apply(self):
        return setup.apply(self.root, 'claude', edition='mcp')

    def matches(self, path, target):
        return path == target or (path.parent == target.parent and
            path.name.startswith('.coprogrammer-setup-' + target.name + '-'))

    def test_partial_new_file_write_never_reaches_final_path(self):
        for relative in ('.mcp.json', setup.MANIFEST_PATH):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                target = root / relative
                original = Path.open
                class PartialWriter:
                    def __init__(self, handle): self.handle = handle
                    def __enter__(self): return self
                    def __exit__(self, *args): return self.handle.__exit__(*args)
                    def __getattr__(self, name): return getattr(self.handle, name)
                    def write(self, data):
                        self.handle.write(data[:7])
                        self.handle.flush()
                        raise OSError('synthetic partial write')
                def fail_write(path, mode='r', *args, **kwargs):
                    handle = original(path, mode, *args, **kwargs)
                    return PartialWriter(handle) if mode == 'xb' and self.matches(path, target) else handle
                with patch.object(Path, 'open', fail_write), self.assertRaisesRegex(RuntimeError, 'rolled back'):
                    setup.apply(root, 'claude', edition='mcp')
                self.assertFalse(target.exists(), 'partial final file survived')
                self.assertEqual(list(root.rglob('.coprogrammer-setup-*')), [])

    def test_rollback_preserves_identical_bytes_in_replacement_file(self):
        original = Path.open
        receipt = self.root / setup.MANIFEST_PATH
        replacement_bytes = []
        def replace_then_fail(path, mode='r', *args, **kwargs):
            if mode == 'xb' and self.matches(path, receipt):
                data = self.first.read_bytes()
                replacement = self.root / 'external-replacement'
                replacement.write_bytes(data)
                self.assertNotEqual(replacement.stat().st_ino, self.first.stat().st_ino)
                os.replace(replacement, self.first)
                replacement_bytes.append(data)
                raise OSError('synthetic receipt failure after external replacement')
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', replace_then_fail), self.assertRaisesRegex(RuntimeError, 'rolled back'):
            self.apply()
        self.assertEqual(len(replacement_bytes), 1)
        self.assertTrue(self.first.exists(), 'rollback deleted independently replaced file')
        self.assertEqual(self.first.read_bytes(), replacement_bytes[0])
        self.assertFalse(receipt.exists())

    def test_publication_exposes_complete_bytes_with_original_creation_mode(self):
        control = self.root / 'mode-control'
        with control.open('xb') as handle:
            handle.write(b'synthetic')
        mode = stat.S_IMODE(control.stat().st_mode)
        link = setup.os.link
        published = []
        def inspect_then_link(source, target):
            self.assertFalse(target.exists())
            data = Path(source).read_bytes()
            self.assertTrue(data)
            self.assertEqual(stat.S_IMODE(Path(source).stat().st_mode), mode)
            result = link(source, target)
            self.assertEqual(target.read_bytes(), data)
            published.append(target)
            return result
        with patch.object(setup.os, 'link', side_effect=inspect_then_link):
            self.assertTrue(self.apply()['applied'])
        self.assertEqual(set(published), {self.first, self.root / setup.MANIFEST_PATH})
        self.assertEqual(list(self.root.rglob('.coprogrammer-setup-*')), [])
        self.assertTrue(self.apply()['applied'])

    def test_competing_creation_is_not_overwritten_or_rolled_back(self):
        for relative in ('.mcp.json', setup.MANIFEST_PATH):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                target = root / relative
                link = setup.os.link
                competitor = []
                def create_competitor(source, destination):
                    if destination == target:
                        # Even identical bytes do not establish ownership.
                        data = Path(source).read_bytes()
                        destination.write_bytes(data)
                        competitor.append(data)
                    return link(source, destination)
                message = 'retained' if relative == setup.MANIFEST_PATH else 'rolled back'
                with patch.object(setup.os, 'link', side_effect=create_competitor), \
                        self.assertRaisesRegex(RuntimeError, message):
                    setup.apply(root, 'claude', edition='mcp')
                self.assertEqual(len(competitor), 1)
                self.assertEqual(target.read_bytes(), competitor[0])
                if relative == setup.MANIFEST_PATH:
                    # A foreign receipt may already refer to these files.
                    self.assertTrue((root / '.mcp.json').exists())
                    self.assertTrue(all(f['status'] == 'unchanged' for f in
                                        setup.preview(root, 'claude', edition='mcp')['files']))
                self.assertEqual(list(root.rglob('.coprogrammer-setup-*')), [])

    def test_staging_fsync_failure_leaves_no_destination(self):
        with patch.object(setup.os, 'fsync', side_effect=OSError('synthetic fsync failure')), \
                self.assertRaisesRegex(RuntimeError, 'rolled back'):
            self.apply()
        self.assertFalse(self.first.exists())
        self.assertFalse((self.root / setup.MANIFEST_PATH).exists())
        self.assertEqual(list(self.root.rglob('.coprogrammer-setup-*')), [])

    def test_unsupported_publication_never_falls_back_to_replace(self):
        with patch.object(setup.os, 'link', side_effect=OSError('synthetic unsupported link')), \
                patch.object(setup, '_replace', side_effect=AssertionError('no unsafe fallback')), \
                self.assertRaisesRegex(RuntimeError, 'rolled back'):
            self.apply()
        self.assertFalse(self.first.exists())
        self.assertFalse((self.root / setup.MANIFEST_PATH).exists())
        self.assertEqual(list(self.root.rglob('.coprogrammer-setup-*')), [])

    def test_rollback_preserves_in_place_edit_to_created_file(self):
        link = setup.os.link
        def edit_then_fail(source, target):
            if target == self.root / setup.MANIFEST_PATH:
                self.first.write_bytes(b'SYNTHETIC_USER_EDIT')
                raise OSError('synthetic receipt publication failure')
            return link(source, target)
        with patch.object(setup.os, 'link', side_effect=edit_then_fail), \
                self.assertRaisesRegex(RuntimeError, 'rolled back'):
            self.apply()
        self.assertEqual(self.first.read_bytes(), b'SYNTHETIC_USER_EDIT')
        self.assertFalse((self.root / setup.MANIFEST_PATH).exists())
        self.assertEqual(list(self.root.rglob('.coprogrammer-setup-*')), [])

    def test_temporary_name_collision_preserves_foreign_file(self):
        with patch.object(setup.uuid, 'uuid4') as unique:
            unique.return_value.hex = 'fixed-synthetic-name'
            temporary = self.root / '.coprogrammer-setup-.mcp.json-fixed-synthetic-name'
            temporary.write_bytes(b'SYNTHETIC_FOREIGN_TEMP')
            with self.assertRaisesRegex(RuntimeError, 'rolled back'):
                self.apply()
        self.assertEqual(temporary.read_bytes(), b'SYNTHETIC_FOREIGN_TEMP')
        self.assertFalse(self.first.exists())
