# SPDX-License-Identifier: AGPL-3.0-or-later
"""Actual Concat/FFmpeg integration, synthetic media only. Leaves evidence in test-output."""
import hashlib
import json
import os
from pathlib import Path
import threading
import time

from engine import ConcatClient, Options, export_project, find_concat, prepare, run_ffmpeg

root = Path(__file__).parent.resolve() / "test-output"
root.mkdir(exist_ok=True)
cancel = threading.Event()
source = root / "grabación de prueba.mkv"
run_ffmpeg(["-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=10",
            "-f", "lavfi", "-i", r"aevalsrc=if(between(t\,3\,6)\,0\,0.3*sin(2*PI*440*t)):s=48000:d=10",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "pcm_s16le", "-y", source], cancel)
os.utime(source, (time.time() - 10, time.time() - 10))
original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
srt = root / "prueba.srt"
srt.write_text("1\n00:00:00,500 --> 00:00:02,000\nPrimera parte\n\n2\n00:00:06,500 --> 00:00:08,000\nDespués del silencio\n", encoding="utf-8")
report = prepare(Options(str(source), str(root), str(find_concat()), captions="SRT", srt=str(srt), zoom=True), print, cancel)
clips = [clip for clip in report["timeline"]["timeline"]["clips"] if clip.get("media")]
assert report["clips"] == 2, report
assert report["captions"] == 2, report
assert 2.5 < report["removed_seconds"] < 2.8, report
assert abs(clips[1]["start"] - (clips[0]["start"] + clips[0]["duration"])) < .001, clips
assert clips[1]["sourceStart"] > 5.7, clips
assert clips[1]["scale"] == 1.04, clips
assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
output = Path(report["project"]) / "test-export.mp4"
export_project(find_concat(), report["project"], output, print, cancel)
with ConcatClient(find_concat(), [root]) as client:
    probe = client.tool("media_probe", path=str(output))
assert output.stat().st_size > 10000
assert abs(probe["duration"] - report["edited_seconds"]) < .15, probe
assert probe["audio"], probe
try:
    export_project(find_concat(), report["project"], output, print, cancel)
    raise AssertionError("Existing export must never be overwritten")
except ValueError:
    pass
(root / "integration-result.json").write_text(json.dumps({"passed": True, "report": report, "export": str(output), "probe": probe}, indent=2, ensure_ascii=False), encoding="utf-8")
print("INTEGRATION PASSED", output)
