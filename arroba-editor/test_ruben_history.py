# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from ruben_plan import plan
from chat_history import append_turn

class RubenHistoryTests(unittest.TestCase):
    def test_open_restores_history_without_network(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            append_turn('project-a', 'Pon un título', 'Propuesta pendiente de aplicar.')
            with patch('ruben_plan.load', side_effect=AssertionError('Must not access provider')):
                result = plan({'projectPath': 'project-a', 'instruction': '', 'snapshot': {}})
            self.assertEqual(result['history'][0]['content'], 'Pon un título')
            self.assertEqual(result['commands'], [])

    def test_same_name_different_paths_stay_separate(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            append_turn('C:/a/project', 'Mensaje privado A', 'Respuesta A')
            result = plan({'projectPath': 'C:/b/project', 'instruction': '', 'snapshot': {}})
            self.assertEqual(result['history'], [])

    def test_previous_build_history_migrates_without_loss(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            snapshot = {'settings': {'name': 'Mi video'}, 'project': {'media': [{'path': 'C:/videos/uno.mp4'}]}}
            legacy = json.dumps({'name': 'Mi video', 'media': ['C:/videos/uno.mp4']}, sort_keys=True)
            append_turn(legacy, 'Hola anterior', 'Respuesta guardada')
            result = plan({'projectPath': 'C:/proyectos/uno', 'instruction': '', 'snapshot': snapshot})
            self.assertEqual(result['history'][0]['content'], 'Hola anterior')
            result = plan({'projectPath': 'C:/proyectos/uno', 'instruction': '', 'snapshot': snapshot})
            self.assertEqual(len(result['history']), 2)

if __name__ == '__main__':
    unittest.main()
