# SPDX-License-Identifier: AGPL-3.0-or-later
import unittest
from openrouter_ai import validate_corrections

class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.source = [{'start': 1.2, 'end': 3.4, 'text': 'sonendo de fondo'}]

    def result(self, text, review=False, index=0):
        return {'captions': [{'id': index, 'text': text, 'needsReview': review}]}

    def test_typo_keeps_timing(self):
        rows, flags = validate_corrections(self.source, self.result('Sonando de fondo.'))
        self.assertEqual(rows[0]['text'], 'Sonando de fondo.')
        self.assertEqual((rows[0]['start'], rows[0]['end']), (1.2, 3.4))
        self.assertEqual(flags, [])
        self.assertEqual(self.source[0]['text'], 'sonendo de fondo')

    def test_uncertain_preserves_original(self):
        rows, flags = validate_corrections(self.source, self.result('Sonando de fondo.', True))
        self.assertEqual(rows, self.source)
        self.assertEqual(flags, [0])

    def test_invented_sentence_is_not_applied(self):
        rows, flags = validate_corrections(self.source, self.result('El presidente anunció nuevas inversiones internacionales.'))
        self.assertEqual(rows, self.source)
        self.assertEqual(flags, [0])

    def test_missing_caption_rejected(self):
        with self.assertRaises(ValueError):
            validate_corrections(self.source, {'captions': []})

    def test_changed_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_corrections(self.source, self.result('Sonando de fondo.', index=7))

    def test_empty_text_rejected(self):
        with self.assertRaises(ValueError):
            validate_corrections(self.source, self.result(''))

    def test_missing_review_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_corrections(self.source, {'captions': [{'id': 0, 'text': 'Sonando'}]})

if __name__ == '__main__':
    unittest.main()
