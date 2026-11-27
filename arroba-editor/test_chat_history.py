# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from chat_history import append_turn, append_event, read, history_path, transcript

class HistoryTests(unittest.TestCase):
    def test_action_outcomes_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            append_turn('project', 'Cambia el título', 'Propuesta pendiente')
            append_event('project', 'applied', 'Cambio aplicado')
            append_event('project', 'undo', 'Cambio deshecho')
            rows = read('project')
            self.assertEqual([row.get('status') for row in rows[-2:]], ['applied', 'undo'])

    def test_concurrent_outcomes_do_not_overwrite_history(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(append_event, 'project', 'applied', str(i)) for i in range(4)]
                for future in futures:
                    future.result()
            self.assertEqual(len(read('project')), 4)
    def test_saved_turn_survives_reload_and_preserves_unicode(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            append_turn('project-a', '¿Puedes añadir un título?', 'Sí, propuesta pendiente.')
            loaded = read('project-a')
            self.assertEqual(loaded[0]['content'], '¿Puedes añadir un título?')
            self.assertIn('Ruben-bot', transcript(loaded))
            self.assertEqual(read('project-b'), [])

    def test_corrupt_history_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            target = history_path('project-a')
            target.parent.mkdir(parents=True)
            target.write_text('invalid', encoding='utf-8')
            with self.assertRaises(ValueError):
                append_turn('project-a', 'Hola', 'Hola')
            self.assertEqual(target.read_text(), 'invalid')

if __name__ == '__main__':
    unittest.main()
