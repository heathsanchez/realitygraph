import tempfile
import unittest
import zipfile
from pathlib import Path

from realitygraph.submission_wrapper import build_submission


class SubmissionWrapperTests(unittest.TestCase):
    def test_build_submission_wraps_existing_main_and_patch_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source'
            patch = root / 'patch'
            source.mkdir()
            patch.mkdir()
            (source / 'main.py').write_text("print('base')\n")
            (source / 'asset.txt').write_text('asset')
            (patch / 'model.json').write_text('{"anchor":{},"residual":{}}')
            (patch / 'parkinson_runtime_patch.py').write_text('# patch\n')
            (patch / 'realitygraph').mkdir()
            (patch / 'realitygraph' / '__init__.py').write_text('')
            (patch / 'realitygraph' / 'helper.py').write_text('# helper\n')
            out = root / 'submission.zip'

            build_submission(source, patch, out, already_parent=False)

            with zipfile.ZipFile(out) as zf:
                names = set(zf.namelist())
                self.assertIn('main.py', names)
                self.assertIn('base_main.py', names)
                self.assertIn('asset.txt', names)
                self.assertIn('model.json', names)
                self.assertIn('parkinson_runtime_patch.py', names)
                self.assertIn('realitygraph/helper.py', names)
                wrapper = zf.read('main.py').decode()
                self.assertIn('ALREADY_PARENT = False', wrapper)
                self.assertIn('already_parent=ALREADY_PARENT', wrapper)
                self.assertIn('base_main.py', wrapper)
                self.assertIn('submission.csv', wrapper)

    def test_missing_source_main_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source'
            patch = root / 'patch'
            source.mkdir()
            patch.mkdir()
            with self.assertRaises(FileNotFoundError):
                build_submission(source, patch, root / 'out.zip')


if __name__ == '__main__':
    unittest.main()
