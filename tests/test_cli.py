import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from meninx_proofkit.cli import ProofError, main, write_atomic


class ProofkitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'delivery'
        self.root.mkdir()
        (self.root / 'file.txt').write_text('abc', encoding='utf-8')
        self.manifest = self.base / 'manifest.json'

    def create(self):
        return main(['create', str(self.root), '-o', str(self.manifest)])

    def verify(self):
        return main(['verify', str(self.root), str(self.manifest)])

    def test_reproducible_and_same_size_tampering(self):
        self.assertEqual(self.create(), 0)
        original = self.manifest.read_bytes()
        self.assertEqual(main(['create', str(self.root), '-o', str(self.manifest), '--force']), 0)
        self.assertEqual(original, self.manifest.read_bytes())
        self.assertEqual(self.verify(), 0)
        (self.root / 'file.txt').write_text('xyz', encoding='utf-8')
        self.assertEqual(self.verify(), 1)

    def test_missing_unexpected(self):
        self.create()
        (self.root / 'file.txt').unlink()
        (self.root / 'other').touch()
        self.assertEqual(self.verify(), 1)

    def test_traversal_and_duplicate(self):
        self.create()
        data = json.loads(self.manifest.read_text())
        data['files'][0]['path'] = '../escape'
        self.manifest.write_text(json.dumps(data))
        self.assertEqual(self.verify(), 2)
        data['files'][0]['path'] = 'file.txt'
        data['files'].append(data['files'][0])
        self.manifest.write_text(json.dumps(data))
        self.assertEqual(self.verify(), 2)

    def test_collision_and_inside_output(self):
        self.create()
        old = self.manifest.read_bytes()
        self.assertEqual(self.create(), 2)
        self.assertEqual(old, self.manifest.read_bytes())
        self.assertEqual(main(['create', str(self.root), '-o', str(self.root / 'x')]), 2)
        self.assertFalse((self.root / 'x').exists())

    def test_symlink_rejected(self):
        try:
            (self.root / 'link').symlink_to(self.root / 'file.txt')
        except OSError:
            self.skipTest('symlinks unavailable')
        self.assertEqual(self.create(), 2)

    def test_atomic_failure_keeps_existing_file(self):
        self.manifest.write_text('old')
        with patch('meninx_proofkit.cli.os.replace', side_effect=OSError('failure')):
            with self.assertRaises(OSError):
                write_atomic(self.manifest, 'new', True)
        self.assertEqual(self.manifest.read_text(), 'old')
        self.assertEqual(list(self.base.glob('.proofkit-*')), [])

    @unittest.skipIf(os.name == 'nt', 'filenames are invalid on Windows')
    def test_invalid_names_preserve_existing_output_with_force(self):
        for invalid in ('bad:name', 'bad\\name'):
            path = self.root / invalid
            path.touch()
            self.manifest.write_text('trusted original')
            self.assertEqual(main(['create', str(self.root), '-o', str(self.manifest), '--force']), 2)
            self.assertEqual(self.manifest.read_text(), 'trusted original')
            path.unlink()

    def test_normalized_root_and_inside_manifest(self):
        (self.base / 'x').mkdir()
        root = self.base / 'x' / '..' / 'delivery'
        inside = self.root / 'manifest.json'
        self.assertEqual(main(['create', str(root), '-o', str(inside)]), 2)
        self.assertFalse(inside.exists())
        inside.write_text('{}')
        self.assertEqual(main(['verify', str(root), str(inside)]), 2)

    def test_duplicate_json_key_is_rejected(self):
        self.manifest.write_text('{"version": 1, "version": 1, "algorithm": "sha256", "files": []}')
        self.assertEqual(self.verify(), 2)

    def test_dot_is_not_a_file_path(self):
        self.create()
        data = json.loads(self.manifest.read_text())
        data['files'][0]['path'] = '.'
        self.manifest.write_text(json.dumps(data))
        self.assertEqual(self.verify(), 2)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO unsupported')
    def test_manifest_fifo_is_rejected(self):
        os.mkfifo(self.manifest)
        self.assertEqual(self.verify(), 2)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO unsupported')
    def test_special_file_rejected(self):
        os.mkfifo(self.root / 'pipe')
        self.assertEqual(self.create(), 2)


if __name__ == '__main__':
    unittest.main()
