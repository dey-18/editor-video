# SPDX-License-Identifier: AGPL-3.0-or-later
"""Engine validation of the new reversible clip tools on a disposable project."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from engine import ConcatClient, find_concat

class ClipCommandTests(unittest.TestCase):
    def test_edit_operations_can_be_undone(self):
        root = Path(__file__).resolve().parent
        evidence = root / 'test-output/integration-result.json'
        if not evidence.exists():
            self.skipTest('Generate synthetic fixture with integration_test.py first')
        original = Path(json.loads(evidence.read_text(encoding='utf-8'))['report']['project'])
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / 'project'
            project.mkdir()
            shutil.copy2(original/'concat.json', project/'concat.json')
            with ConcatClient(find_concat(), [Path(folder)]) as client:
                client.tool('project_open', path=str(project))
                before = client.tool('timeline_read', path=str(project))['timeline']['clips']
                clip = next(c for c in before if c.get('media'))['id']
                commands = [{'op': 'trimClip', 'clipId': clip, 'edge': 'end', 'delta': -.2},
                            {'op': 'splitClips', 'clipIds': [clip], 'time': 1},
                            {'op': 'removeClips', 'clipIds': [clip], 'ripple': True},
                            {'op': 'setClipSpeed', 'clipId': clip, 'speed': 1.25}]
                for command in commands:
                    with self.subTest(command=command['op']):
                        client.tool('edit_apply', path=str(project), command=command)
                        after = client.tool('timeline_read', path=str(project))['timeline']['clips']
                        self.assertNotEqual(after, before)
                        client.tool('edit_undo', path=str(project))
                        restored = client.tool('timeline_read', path=str(project))['timeline']['clips']
                        self.assertEqual(restored, before)
                client.tool('project_close', path=str(project), save=False)

if __name__ == '__main__':
    unittest.main()
