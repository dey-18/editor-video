# SPDX-License-Identifier: AGPL-3.0-or-later
"""Real event protocol and cancellation, using only synthetic footage."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class WorkerEventTests(unittest.TestCase):
    def run_worker(self, cancelled):
        root = Path(__file__).resolve().parent
        source = root / 'test-output/grabación de prueba.mkv'
        if not source.exists():
            self.skipTest('Run integration_test.py to generate synthetic media first')
        with tempfile.TemporaryDirectory() as folder:
            flag = Path(folder) / 'cancel.flag'
            if cancelled:
                flag.write_text('cancel')
            options = {'cancelFile': str(flag), 'captions': False, 'silence': True,
                       'preset': 'Normal', 'audioTrack': 1, 'language': 'es'}
            result = subprocess.run([sys.executable, str(root/'worker.py'), str(source), folder, '--events'],
                       input=json.dumps(options), text=True, encoding='utf-8', capture_output=True,
                       timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
            events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            return result.returncode, events

    def test_progress_and_summary(self):
        code, events = self.run_worker(False)
        self.assertEqual(code, 0, events)
        self.assertTrue(any('progress' in event for event in events))
        self.assertIn('project', events[-1])
        self.assertIn('2 fragmentos', events[-1]['summary'])

    def test_cancel_does_not_report_success(self):
        code, events = self.run_worker(True)
        self.assertNotEqual(code, 0, events)
        self.assertIn('error', events[-1])
        self.assertFalse(any('project' in event for event in events))

if __name__ == '__main__':
    unittest.main()
