# SPDX-License-Identifier: AGPL-3.0-or-later
"""Real offline speech inference and editable-caption integration."""
import json
import os
from pathlib import Path
import threading
import time
from engine import Options, find_concat, prepare, run_ffmpeg

root = Path(__file__).parent.resolve()
output = root / "test-output"
output.mkdir(exist_ok=True)
source = output / "voice-test.mp4"
voice = root.parent / "src/crates/concat-speech/voices/elizabeth-klett.flac"
cancel = threading.Event()
run_ffmpeg(["-f", "lavfi", "-i", "color=c=0x17223a:s=640x360:r=30:d=10", "-i", voice,
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", "-y", source], cancel)
os.utime(source, (time.time() - 10, time.time() - 10))
report = prepare(Options(str(source), str(output), str(find_concat()), captions="Automáticos", language="en"), print, cancel)
assert report["captions"] > 0, report
captions = [clip for clip in report["timeline"]["timeline"]["clips"] if "text" in clip]
assert captions
assert all(clip["duration"] > 0 for clip in captions)
(output / "speech-result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print("SPEECH PASSED", [clip["text"] for clip in captions])
