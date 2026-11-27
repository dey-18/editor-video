# SPDX-License-Identifier: AGPL-3.0-or-later
"""Local automation over Concat's public MCP API. Originals are never edited."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
import wave

VERSION = "0.1.0"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}
PRESETS = {
    "Suave": (-45, 1.2, 0.25),
    "Normal": (-40, 0.8, 0.18),
    "Fuerte": (-35, 0.5, 0.12),
}


class Cancelled(Exception):
    pass


def check_cancel(event):
    if event.is_set():
        raise Cancelled("Proceso cancelado. El video original está intacto.")


def find_concat() -> Path:
    configured = os.environ.get('ARROBA_ENGINE')
    if configured:
        executable = Path(configured)
        if not executable.is_file():
            raise RuntimeError('El motor de Arroba Editor no está disponible. Reinicia la aplicación.')
        return executable
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Concat/concat.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Concat/concat.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError("Instala Concat 0.2.11 o posterior, o selecciona concat.exe en Ajustes.")


class ConcatClient:
    """One isolated headless session; bounded waits and cancellable pipe reads."""
    def __init__(self, executable: Path, roots: list[Path], cancel=None):
        self.cancel = cancel or threading.Event()
        self.sequence = 0
        self.lines = queue.Queue()
        self.errors = []
        env = os.environ.copy()
        env["CONCAT_MCP_ROOTS"] = os.pathsep.join(str(p.resolve()) for p in roots)
        env.pop("CONCAT_API_ADDRESS", None)
        env.pop("CONCAT_API_TOKEN", None)
        self.process = subprocess.Popen(
            [str(executable), "--mcp", "headless"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", env=env, creationflags=NO_WINDOW,
        )
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._read_errors, daemon=True).start()
        try:
            self.ask("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                   "clientInfo": {"name": "Arroba Editor", "version": VERSION}})
            self._write({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except Exception:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    self.lines.put(json.loads(line))
                except ValueError:
                    self.lines.put({"transportError": "Concat devolvió una respuesta inválida."})
        finally:
            self.lines.put({"transportError": "El proceso de Concat se cerró inesperadamente."})

    def _read_errors(self):
        for line in self.process.stderr:
            self.errors.append(line.strip())
            self.errors[:] = self.errors[-30:]

    def _write(self, value):
        self.process.stdin.write(json.dumps(value, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def ask(self, method, params, timeout=180):
        check_cancel(self.cancel)
        self.sequence += 1
        request_id = self.sequence
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            check_cancel(self.cancel)
            try:
                reply = self.lines.get(timeout=0.2)
            except queue.Empty:
                continue
            if "transportError" in reply:
                raise RuntimeError(reply["transportError"] + "\n" + "\n".join(self.errors[-3:]))
            if reply.get("id") != request_id:
                continue
            if "error" in reply:
                raise RuntimeError(reply["error"].get("message", str(reply["error"])))
            return reply["result"]
        raise TimeoutError(f"Concat no respondió a {method} en {timeout} segundos.")

    def tool(self, tool_name, **arguments):
        result = self.ask("tools/call", {"name": tool_name, "arguments": arguments})
        text = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if result.get("isError"):
            raise RuntimeError(text or f"Concat rechazó {tool_name}.")
        if "structuredContent" in result:
            return result["structuredContent"]
        try:
            return json.loads(text)
        except ValueError:
            return {"text": text}

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def run_ffmpeg(arguments, cancel, timeout=7200):
    import imageio_ffmpeg
    process = subprocess.Popen(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-hide_banner", *map(str, arguments)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        creationflags=NO_WINDOW,
    )
    deadline = time.monotonic() + timeout
    try:
        while True:
            check_cancel(cancel)
            if time.monotonic() > deadline:
                raise TimeoutError("El análisis de audio superó el tiempo máximo.")
            try:
                _, stderr = process.communicate(timeout=0.25)
                break
            except subprocess.TimeoutExpired:
                continue
        log = stderr.decode("utf-8", errors="replace")
        if process.returncode:
            raise RuntimeError("No se pudo procesar el audio.\n" + log[-2000:])
        return log
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def parse_silences(log: str, duration: float):
    intervals = []
    start = None
    for match in re.finditer(r"silence_(start|end):\s*(-?[\d.]+)", log):
        kind, value = match.group(1), float(match.group(2))
        if kind == "start":
            start = max(0.0, value)
        else:
            intervals.append((0.0 if start is None else start, min(duration, value)))
            start = None
    if start is not None:
        intervals.append((start, duration))
    return intervals


def keep_intervals(duration, silences, padding, fps):
    """Remove only interior silence, retaining breathing room and video frame alignment."""
    if not math.isfinite(duration) or duration <= 0 or not math.isfinite(fps) or fps <= 0:
        raise ValueError("El video no tiene una duración o frecuencia válida.")
    cuts = []
    for start, end in sorted(silences):
        # Rounding inward never removes sound outside the detected silence.
        a = math.ceil((max(0, start) + padding) * fps - 1e-8) / fps
        b = math.floor((min(duration, end) - padding) * fps + 1e-8) / fps
        if b > a:
            if cuts and a <= cuts[-1][1]:
                cuts[-1] = (cuts[-1][0], max(b, cuts[-1][1]))
            else:
                cuts.append((a, b))
    kept, cursor = [], 0.0
    for a, b in cuts:
        if a - cursor >= 1 / fps - 1e-8:
            kept.append((cursor, a))
        cursor = b
    if duration - cursor >= 1 / fps - 1e-8:
        kept.append((cursor, duration))
    # Never turn a silent recording into tiny edge fragments without an explanation.
    if not kept or sum(b - a for a, b in kept) < min(0.75, duration * 0.1):
        raise ValueError("El audio está prácticamente en silencio. Elige otra pista o desactiva los cortes.")
    return kept


def assemble_audio(source: Path, target: Path, intervals, cancel):
    """Stream PCM slices; no whole-recording allocation or shell filter quoting."""
    with wave.open(str(source), "rb") as inp, wave.open(str(target), "wb") as out:
        out.setparams(inp.getparams())
        rate, total = inp.getframerate(), inp.getnframes()
        frame_size = inp.getnchannels() * inp.getsampwidth()
        for start, end in intervals:
            first, last = min(round(start * rate), total), min(round(end * rate), total)
            inp.setpos(first)
            remaining = last - first
            while remaining > 0:
                check_cancel(cancel)
                data = inp.readframes(min(remaining, rate * 10))
                if not data:
                    break
                out.writeframesraw(data)
                remaining -= len(data) // frame_size
            # Pad a short audio tail so captions and the video timeline stay aligned.
            missing = round((end - start) * rate) - (last - first)
            if missing > 0:
                out.writeframesraw(b"\0" * missing * frame_size)


def srt_text(captions):
    def stamp(value):
        milliseconds = max(0, round(value * 1000))
        seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"
    return "\n\n".join(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}"
                        for i, c in enumerate(captions, 1)) + "\n"


def read_srt(path):
    text = Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    captions = []
    pattern = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{3})")
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if index is None:
            continue
        match = pattern.fullmatch(lines[index].strip())
        if not match:
            raise ValueError("El SRT contiene una marca de tiempo inválida.")
        nums = list(map(int, match.groups()))
        start = nums[0] * 3600 + nums[1] * 60 + nums[2] + nums[3] / 1000
        end = nums[4] * 3600 + nums[5] * 60 + nums[6] + nums[7] / 1000
        content = "\n".join(lines[index + 1:]).strip()
        if end <= start or not content:
            raise ValueError("El SRT contiene un subtítulo vacío o con duración inválida.")
        captions.append({"start": start, "end": end, "text": content})
    if not captions:
        raise ValueError("No se encontraron subtítulos en el SRT.")
    return captions


def remap_captions(captions, intervals):
    """An imported SRT refers to the original: split it at removed ranges."""
    result, cursor = [], 0.0
    for start, end in intervals:
        for caption in captions:
            a, b = max(start, caption["start"]), min(end, caption["end"])
            if b - a >= 0.04:
                result.append({"start": cursor + a - start, "end": cursor + b - start,
                               "text": caption["text"]})
        cursor += end - start
    return result


def model_path():
    if getattr(sys, "frozen", False):
        bundled = Path(sys.executable).parent / "models/tiny"
        if (bundled / "model.bin").is_file():
            return bundled
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ArrobaEditor/models/tiny"


def download_model(progress, cancel):
    """Explicit UI action, separate from local transcription. Never uploads media."""
    from huggingface_hub import snapshot_download
    check_cancel(cancel)
    progress("Descargando modelo multilingüe Tiny (~75 MB). Solo se necesita una vez.")
    result = snapshot_download("Systran/faster-whisper-tiny", local_dir=str(model_path()),
                               allow_patterns=["model.bin", "config.json", "tokenizer.json", "vocabulary.*"],
                               max_workers=2)
    check_cancel(cancel)
    return result


def transcribe(audio, language, progress, cancel):
    from faster_whisper import WhisperModel
    folder = model_path()
    if not (folder / "model.bin").is_file():
        raise RuntimeError("Descarga primero el modelo de subtítulos con el botón «Descargar modelo».")
    progress("Cargando el modelo local de subtítulos…")
    model = WhisperModel(str(folder), device="cpu", compute_type="int8",
                         cpu_threads=max(1, min(8, (os.cpu_count() or 2) - 1)), local_files_only=True)
    check_cancel(cancel)
    segments, info = model.transcribe(str(audio), language=None if language == "auto" else language,
                                      beam_size=3, vad_filter=True, word_timestamps=True,
                                      condition_on_previous_text=False)
    captions = []
    for segment in segments:
        check_cancel(cancel)
        words = segment.words or []
        if not words:
            if segment.text.strip() and segment.end > segment.start:
                captions.append({"start": segment.start, "end": segment.end, "text": segment.text.strip()})
            continue
        group = []
        for word in words:
            text = "".join(w.word for w in group) + word.word
            if group and (len(text) > 42 or word.end - group[0].start > 4):
                captions.append({"start": group[0].start, "end": group[-1].end,
                                 "text": "".join(w.word for w in group).strip()})
                group = []
            group.append(word)
        if group:
            captions.append({"start": group[0].start, "end": group[-1].end,
                             "text": "".join(w.word for w in group).strip()})
        progress(f"Transcribiendo: {segment.end:.0f} s / {info.duration:.0f} s")
    return [c for c in captions if c["end"] > c["start"] and c["text"]]


@dataclass
class Options:
    source: str
    output: str
    concat: str
    silence: bool = True
    preset: str = "Normal"
    captions: str = "Ninguno"  # Ninguno, Automáticos, SRT
    srt: str = ""
    language: str = "es"
    zoom: bool = False
    audio_track: int = 1  # ordinal, 1-based, not the container's stream index


def prepare(options: Options, progress, cancel):
    source, output = Path(options.source).resolve(), Path(options.output).resolve()
    if not source.is_file() or source.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError("Selecciona un video MP4, MKV, MOV, WebM, AVI o M4V.")
    if options.preset not in PRESETS or options.captions not in {"Ninguno", "Automáticos", "SRT"}:
        raise ValueError("Opciones de edición inválidas.")
    if options.captions == "Automáticos" and not (model_path() / "model.bin").is_file():
        raise ValueError("Descarga primero el modelo de subtítulos o elige «Ninguno» / «SRT».")
    imported = read_srt(options.srt) if options.captions == "SRT" else None
    output.mkdir(parents=True, exist_ok=True)
    before = source.stat()
    if time.time() - before.st_mtime < 3:
        raise ValueError("El video acaba de cambiar. Termina la grabación de OBS y espera unos segundos.")
    warnings = []
    name = "Edicion-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    project = output / name
    project_created = False
    with ConcatClient(Path(options.concat), [output, source.parent], cancel) as client:
        progress("Leyendo video y pistas de audio…")
        media = client.tool("media_probe", path=str(source))
        video = media.get("video")
        if not video:
            raise ValueError("El archivo no contiene una pista de video compatible.")
        duration = float(media.get("duration") or 0)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("No se pudo leer la duración. Comprueba que la grabación haya terminado.")
        fraction = video.get("frameRateFraction")
        rate = Fraction(str(video.get("frameRate") or 30)).limit_denominator(1001)
        if isinstance(fraction, str) and "/" in fraction:
            rate = Fraction(fraction)
        if isinstance(fraction, dict):
            rate = Fraction(fraction.get("num", 30), fraction.get("den", 1))
        fps = float(rate)
        tracks = media.get("audioTracks") or ([media["audio"]] if media.get("audio") else [])
        if tracks and not 1 <= options.audio_track <= len(tracks):
            raise ValueError(f"El video tiene {len(tracks)} pista(s) de audio. Elige una de ellas.")
        if not tracks and (options.silence or options.captions == "Automáticos"):
            raise ValueError("El video no tiene audio. Desactiva los cortes y los subtítulos automáticos.")
        if len(tracks) > 1:
            warnings.append(f"Se utilizó solo la pista de audio {options.audio_track} de {len(tracks)}; las otras no se mezclaron.")
        settings = {"width": video["width"], "height": video["height"], "rateNum": rate.numerator, "rateDen": rate.denominator}
        summary = client.tool("project_create", location=str(output), name=name, video=settings)
        project_created = True
        work = project / "arroba"
        work.mkdir(exist_ok=True)
        raw_audio, edited_audio = work / "original-audio.wav", work / "edited-audio.wav"
        try:
            intervals = [(0.0, duration)]
            detection_log = ""
            if options.silence or options.captions == "Automáticos":
                progress("Extrayendo la voz y analizando el audio…")
                filters = []
                if options.silence:
                    threshold, minimum, padding = PRESETS[options.preset]
                    filters = ["-af", f"aresample=16000,aformat=sample_fmts=s16:channel_layouts=mono,silencedetect=noise={threshold}dB:d={minimum}"]
                detection_log = run_ffmpeg(["-i", source, "-map", f"0:a:{options.audio_track - 1}", "-vn", "-ac", "1", "-ar", "16000",
                            *filters, "-c:a", "pcm_s16le", "-y", raw_audio], cancel)
            if options.silence:
                progress("Detectando silencios y conservando margen alrededor de la voz…")
                threshold, minimum, padding = PRESETS[options.preset]
                intervals = keep_intervals(duration, parse_silences(detection_log, duration), padding, fps)
            check_cancel(cancel)
            after = source.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError("El video cambió durante el análisis. Espera a que OBS termine y vuelve a intentarlo.")
            if len(intervals) > 3000:
                raise ValueError("Se detectaron demasiados cortes. Prueba el modo Suave o una pista con menos ruido.")
            progress(f"Montando {len(intervals)} fragmentos editables…")
            media_id = client.tool("media_import", path=str(project), file=str(source))["createdId"]
            track = summary["timeline"]["tracks"][0]["id"]
            cursor, clip_ids = 0.0, []
            for i, (start, end) in enumerate(intervals):
                check_cancel(cancel)
                clip = client.tool("clip_add", path=str(project), mediaId=media_id, trackId=track, start=cursor)["createdId"]
                # Trim tail first, then head with ripple: timeline position stays at cursor.
                if end < duration - 1e-6:
                    client.tool("clip_trim", path=str(project), clipId=clip, edge="end", delta=end - duration)
                if start > 1e-6:
                    client.tool("clip_trim", path=str(project), clipId=clip, edge="start", delta=start, ripple=True)
                if tracks:
                    stream_index = tracks[options.audio_track - 1].get("index")
                    if stream_index is not None:
                        client.tool("clip_update", path=str(project), clipId=clip, patch={"audioStream": stream_index})
                if options.zoom and i % 2 == 1:
                    client.tool("clip_transform", path=str(project), clipId=clip, scale=1.04)
                cursor += end - start
                clip_ids.append(clip)
                if i % 10 == 0:
                    progress(f"Montando fragmento {i + 1} de {len(intervals)}…")
            captions = []
            if options.captions == "Automáticos":
                assemble_audio(raw_audio, edited_audio, intervals, cancel)
                captions = transcribe(edited_audio, options.language, progress, cancel)
                if not captions:
                    warnings.append("El modelo no detectó palabras. El montaje se guardó sin subtítulos.")
            elif imported is not None:
                captions = remap_captions(imported, intervals)
                if not captions:
                    warnings.append("Ningún subtítulo del SRT coincide con los fragmentos conservados.")
            captions = [{**c, "end": min(c["end"], cursor)} for c in captions if c["start"] < cursor and c["end"] > c["start"]]
            if captions:
                if os.environ.get("ARROBA_AI_CAPTIONS") == "1":
                    from openrouter_ai import correct_captions
                    progress("Corrigiendo el texto de los subtítulos con OpenRouter…")
                    (work / "subtitulos-originales.srt").write_text(srt_text(captions), encoding="utf-8")
                    try:
                        original_captions = [dict(c) for c in captions]
                        captions, review = correct_captions(captions, cancel)
                        changes = [{"index": i, "start": old["start"], "end": old["end"],
                                    "original": old["text"], "corrected": new["text"],
                                    "needsReview": i in review}
                                   for i, (old, new) in enumerate(zip(original_captions, captions))]
                        (work / "correcciones-ia.json").write_text(
                            json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
                        if review:
                            warnings.append(f"La IA marcó {len(review)} subtítulos para revisión.")
                    except RuntimeError as error:
                        warnings.append(str(error))
                progress(f"Añadiendo {len(captions)} subtítulos editables…")
                for offset in range(0, len(captions), 150):
                    client.tool("captions_add", path=str(project), captions=captions[offset:offset + 150],
                                style={"fontSize": 0.04, "fontWeight": 600, "maxWidth": 0.88,
                                       "color": "#ffffff", "background": "#101827cc", "shadow": True})
                (work / "subtitulos.srt").write_text(srt_text(captions), encoding="utf-8")
            client.tool("project_save", path=str(project))
            final = client.tool("timeline_read", path=str(project))
            report = {"version": VERSION, "status": "ready", "source": str(source), "project": str(project),
                      "original_seconds": duration, "edited_seconds": cursor, "removed_seconds": max(0, duration - cursor),
                      "clips": len(clip_ids), "captions": len(captions), "intervals": intervals,
                      "options": asdict(options), "warnings": warnings, "timeline": final}
            (work / "resultado.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            client.tool("project_close", path=str(project), save=True)
            project_created = False
            progress("Edición preparada. Puedes revisarla en Concat o exportar un MP4.")
            return report
        finally:
            # Only generated, known temporary audio files are removed.
            raw_audio.unlink(missing_ok=True)
            edited_audio.unlink(missing_ok=True)
            if project_created:
                # Process shutdown releases project locks; failed runs are explicitly marked.
                (work / "INCOMPLETO.txt").write_text("Proceso interrumpido o fallido. No es una edición terminada. El original está intacto.\n", encoding="utf-8")


def export_project(executable, project, output, progress, cancel):
    project, output = Path(project).resolve(), Path(output).resolve()
    if output.suffix.lower() != ".mp4":
        raise ValueError("La exportación debe tener extensión .mp4.")
    if output.exists():
        raise ValueError("Ese archivo ya existe. Elige otro nombre para conservarlo.")
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.stem + "." + uuid.uuid4().hex[:6] + ".partial.mp4")
    try:
        with ConcatClient(Path(executable), [project.parent, output.parent], cancel) as client:
            try:
                client.tool("project_open", path=str(project))
            except RuntimeError as exc:
                raise RuntimeError("No se pudo abrir el proyecto para exportar. Si está abierto en Concat, guarda y cierra ese proyecto, o exporta desde Concat.\n" + str(exc)) from exc
            job = client.tool("export_start", path=str(project), output=str(partial), codec="h264", preset="fast")["job"]
            while True:
                check_cancel(cancel)
                status = client.tool("export_status", job=job)
                state = status.get("state")
                if state == "done":
                    break
                if state in {"failed", "cancelled"}:
                    raise RuntimeError("No se completó la exportación: " + json.dumps(status, ensure_ascii=False))
                fraction = status.get("fraction") or 0
                progress(f"Exportando: {status.get('stage', 'preparando')} · {fraction * 100:.0f}%")
                cancel.wait(0.5)
            if not partial.is_file() or partial.stat().st_size == 0:
                raise RuntimeError("Concat no produjo un video válido.")
            client.tool("project_close", path=str(project), save=False)
        # On Windows rename refuses an existing destination, including a concurrent creation.
        partial.rename(output)
        return str(output)
    finally:
        partial.unlink(missing_ok=True)
