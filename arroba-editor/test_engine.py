# SPDX-License-Identifier: AGPL-3.0-or-later
import tempfile
from pathlib import Path
import threading
import unittest
import wave

from engine import (Cancelled, assemble_audio, check_cancel, keep_intervals,
                    parse_silences, read_srt, remap_captions, srt_text)


class EditingTests(unittest.TestCase):
    def test_no_silence_preserves_whole_source(self):
        self.assertEqual(keep_intervals(9.5, [], .18, 30), [(0, 9.5)])

    def test_removes_only_silence_and_retains_padding(self):
        kept = keep_intervals(10, [(3, 6)], .2, 30)
        self.assertAlmostEqual(kept[0][1], 3.2)
        self.assertAlmostEqual(kept[1][0], 5.8)
        self.assertAlmostEqual(sum(b - a for a, b in kept), 7.4)

    def test_fractional_frame_rate_is_aligned(self):
        fps = 30000 / 1001
        kept = keep_intervals(15, [(2.37, 4.19)], .18, fps)
        self.assertAlmostEqual(kept[0][1] * fps, round(kept[0][1] * fps))
        self.assertGreaterEqual(kept[0][1], 2.37 + .18)
        self.assertLessEqual(kept[1][0], 4.19 - .18)

    def test_all_silence_is_actionable_error(self):
        with self.assertRaisesRegex(ValueError, "silencio"):
            keep_intervals(20, [(0, 20)], .18, 30)

    def test_overlapping_silences_merge(self):
        kept = keep_intervals(10, [(2, 5), (4, 7)], 0, 30)
        self.assertEqual(kept, [(0, 2), (7, 10)])

    def test_trailing_silence_parser(self):
        self.assertEqual(parse_silences("silence_start: 3\nsilence_end: 5 | silence_duration: 2\nsilence_start: 8", 10), [(3, 5), (8, 10)])

    def test_imported_srt_moves_after_cut(self):
        captions = [{"start": 0, "end": 1, "text": "Inicio"}, {"start": 6, "end": 8, "text": "Después"}]
        result = remap_captions(captions, [(0, 2), (5, 10)])
        self.assertEqual(result[1], {"start": 3, "end": 5, "text": "Después"})

    def test_srt_crossing_cut_stays_inside_kept_timeline(self):
        result = remap_captions([{"start": 1, "end": 7, "text": "Cruce"}], [(0, 2), (5, 10)])
        self.assertEqual([(c["start"], c["end"]) for c in result], [(1, 2), (2, 4)])

    def test_srt_unicode_and_millisecond_carry(self):
        captions = [{"start": 59.9996, "end": 62.5, "text": "¿Cómo estás?\nOlá!"}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sub.srt"
            path.write_text(srt_text(captions), encoding="utf-8")
            result = read_srt(path)
        self.assertEqual(result[0]["start"], 60)
        self.assertEqual(result[0]["text"], captions[0]["text"])

    def test_audio_concatenation_uses_source_ranges(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "input.wav", Path(folder) / "out.wav"
            with wave.open(str(source), "wb") as audio:
                audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                audio.writeframes(b"\x01\x00" * 16000 + b"\x02\x00" * 16000 + b"\x03\x00" * 16000)
            assemble_audio(source, target, [(0, 1), (2, 3)], threading.Event())
            with wave.open(str(target), "rb") as audio:
                self.assertEqual(audio.getnframes(), 32000)
                self.assertEqual(audio.readframes(16000), b"\x01\x00" * 16000)
                self.assertEqual(audio.readframes(16000), b"\x03\x00" * 16000)

    def test_cancellation(self):
        event = threading.Event()
        event.set()
        with self.assertRaises(Cancelled):
            check_cancel(event)


if __name__ == "__main__":
    unittest.main()
