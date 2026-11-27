# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from agent_context import catalogue, project_summary, describe, effects_context

class ContextTests(unittest.TestCase):
    def test_effect_index_remains_complete_details_are_relevant(self):
        effects = [{'id': 'blur', 'name': 'Blur', 'kind': 'effect', 'params': [1]},
                   {'id': 'shake', 'name': 'Shake', 'kind': 'effect', 'params': [2]}]
        context = effects_context(effects, 'Añade desenfoque')
        self.assertEqual(len(context['index']), 2)
        self.assertEqual([e['id'] for e in context['details']], ['blur'])
    def test_summary_omits_source_paths_and_inactive_timelines(self):
        view = {'project': {'activeTimelineId': 't1', 'timelines': [{'id': 't1'}, {'id': 't2'}],
                'media': [{'id': 'm1', 'name': 'video', 'path': 'C:/private/video.mp4'}]}}
        result = project_summary(view)
        self.assertEqual(result['timeline']['id'], 't1')
        self.assertNotIn('path', result['media'][0])

    def test_catalogue_reused_until_executable_changes(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            exe = Path(folder) / 'editor.exe'
            exe.write_bytes(b'test')
            client = MagicMock()
            client.ask.return_value = {'tools': []}
            client.tool.return_value = []
            with patch('agent_context.find_concat', return_value=exe), patch('agent_context.ConcatClient') as factory:
                factory.return_value.__enter__.return_value = client
                catalogue(); catalogue()
                self.assertEqual(factory.call_count, 1)
                exe.write_bytes(b'new-version')
                catalogue()
                self.assertEqual(factory.call_count, 2)

    def test_title_proposal_readable(self):
        text = describe('title_add', {'start': 2, 'duration': 3, 'style': {'content': 'Hola'}})
        self.assertIn('Hola', text)
        self.assertIn('3 s', text)
        self.assertNotIn('title_add', text)

if __name__ == '__main__':
    unittest.main()
