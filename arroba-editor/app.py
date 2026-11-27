# SPDX-License-Identifier: AGPL-3.0-or-later
"""Arroba Editor: a small desktop workflow backed by the installed Concat engine."""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback

from engine import (Cancelled, Options, PRESETS, VERSION, VIDEO_EXTENSIONS,
                    download_model, export_project, find_concat, model_path, prepare)

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ArrobaEditor"
BG, PANEL, TEXT, MUTED, ACCENT = "#0d1320", "#182234", "#eef3fc", "#a7b7cc", "#88e0b0"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Arroba Editor · {VERSION} · Vista previa")
        self.geometry("1000x900")
        self.minsize(1000, 900)
        self.configure(bg=BG)
        self.queue = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.result = None
        self.config_values = self.read_config()
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar(value=self.config_values.get("output", str(Path.home() / "Videos/Arroba Editor")))
        self.obs_path = self.config_values.get("obs", "")
        try:
            default_concat = str(find_concat())
        except RuntimeError:
            default_concat = ""
        self.concat_path = self.config_values.get("concat", default_concat)
        self.srt_path = ""
        self.silence = tk.BooleanVar(value=True)
        self.preset = tk.StringVar(value="Normal")
        self.caption_mode = tk.StringVar(value="Automáticos" if (model_path() / "model.bin").is_file() else "Ninguno")
        self.language = tk.StringVar(value="Español")
        self.track = tk.StringVar(value="1")
        self.zoom = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Elige una grabación terminada para empezar.")
        self.summary = tk.StringVar(value="Tu edición aparecerá aquí")
        self.detail = tk.StringVar(value="Cortes y subtítulos editables. El archivo original se conserva.")
        self.controls = []
        self.make_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(150, self.poll)

    def read_config(self):
        try:
            return json.loads((CONFIG_DIR / "settings.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save_config(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            (CONFIG_DIR / "settings.json").write_text(json.dumps({"output": self.output_path.get(), "obs": self.obs_path,
                                                                   "concat": self.concat_path}, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            self.status.set(f"No se pudieron guardar las preferencias: {exc}")

    def label(self, parent, text=None, size=11, color=TEXT, **kwargs):
        return tk.Label(parent, text=text, font=("Segoe UI", size), bg=parent.cget("bg"), fg=color, **kwargs)

    def button(self, parent, text, command, primary=False, register=True):
        button = tk.Button(parent, text=text, command=command, font=("Segoe UI", 10, "bold"),
                           bg=ACCENT if primary else "#26364f", fg=BG if primary else TEXT,
                           activebackground="#b0efcd" if primary else "#354961", activeforeground=BG if primary else TEXT,
                           relief="flat", padx=16, pady=9, cursor="hand2", borderwidth=0,
                           disabledforeground="#758399")
        if register:
            self.controls.append(button)
        return button

    def make_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground="#edf1f7", padding=5)
        style.configure("TProgressbar", troughcolor=PANEL, background=ACCENT, borderwidth=0)
        main = tk.Frame(self, bg=BG, padx=30, pady=20)
        main.pack(fill="both", expand=True)
        header = tk.Frame(main, bg=BG)
        header.pack(fill="x")
        self.label(header, "@  ARROBA EDITOR", 21).pack(side="left")
        self.button(header, "Ayuda y código fuente", self.about).pack(side="right")
        self.label(main, "De grabación a primer montaje, en un solo paso.", 12, MUTED).pack(anchor="w", pady=(4, 17))

        source = tk.Frame(main, bg=PANEL, padx=18, pady=13)
        source.pack(fill="x")
        self.label(source, "01   TU GRABACIÓN", 10, ACCENT).pack(anchor="w")
        row = tk.Frame(source, bg=PANEL)
        row.pack(fill="x", pady=(10, 6))
        entry = tk.Entry(row, textvariable=self.input_path, font=("Segoe UI", 11), bg="#101827", fg=TEXT,
                         insertbackground=TEXT, relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 12))
        self.controls.append(entry)
        self.button(row, "Elegir video", self.choose_video, primary=True).pack(side="right")
        row = tk.Frame(source, bg=PANEL)
        row.pack(fill="x")
        self.button(row, "Carpeta OBS…", self.choose_obs).pack(side="left")
        self.button(row, "Usar último video", self.latest).pack(side="left", padx=8)
        self.label(row, "MP4 · MKV · MOV · WebM", 10, MUTED).pack(side="right")

        actions = tk.Frame(main, bg=PANEL, padx=18, pady=13)
        actions.pack(fill="x", pady=12)
        self.label(actions, "02   LO QUE QUIERES AUTOMATIZAR", 10, ACCENT).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        def check(text, variable, row, col):
            widget = tk.Checkbutton(actions, text=text, variable=variable, bg=PANEL, fg=TEXT, selectcolor=BG,
                                    activebackground=PANEL, activeforeground=TEXT, font=("Segoe UI", 11))
            widget.grid(row=row, column=col, sticky="w", pady=4)
            self.controls.append(widget)
        def combo(variable, values, row, col, width=17):
            widget = ttk.Combobox(actions, textvariable=variable, values=values, state="readonly", width=width)
            widget.grid(row=row, column=col, sticky="w", padx=(12, 20), pady=4)
            self.controls.append(widget)
            return widget
        check("Quitar silencios", self.silence, 1, 0)
        combo(self.preset, list(PRESETS), 1, 1)
        self.label(actions, "Pista de audio", 10, MUTED).grid(row=1, column=2, sticky="w")
        combo(self.track, [str(n) for n in range(1, 9)], 1, 3, 5)
        self.label(actions, "Subtítulos", 11).grid(row=2, column=0, sticky="w", padx=4)
        combo(self.caption_mode, ["Ninguno", "Automáticos", "SRT"], 2, 1)
        combo(self.language, ["Español", "Português", "English", "Detectar"], 2, 2, 13)
        self.button(actions, "Elegir SRT…", self.choose_srt).grid(row=2, column=3, sticky="w")
        check("Zoom alterno suave (4 %)", self.zoom, 3, 0)
        self.model_button = self.button(actions, "Modelo instalado ✓" if (model_path() / "model.bin").is_file() else "Descargar modelo (~75 MB)", self.get_model)
        self.model_button.grid(row=3, column=1, columnspan=3, sticky="e", pady=4)
        self.label(actions, "La pista elegida se usa para analizar y exportar. Los subtítulos se generan en este equipo.", 9, MUTED).grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 0))

        output = tk.Frame(main, bg=BG)
        output.pack(fill="x", pady=(0, 8))
        self.label(output, "Guardar proyectos en:", 10, MUTED).pack(side="left")
        self.label(output, textvariable=self.output_path, size=10, color=MUTED, anchor="w").pack(side="left", fill="x", expand=True, padx=8)
        self.button(output, "Cambiar…", self.choose_output).pack(side="right")
        row = tk.Frame(main, bg=BG)
        row.pack(fill="x")
        self.start_button = self.button(row, "Preparar edición automática", self.start, primary=True)
        self.start_button.pack(side="left")
        self.cancel_button = self.button(row, "Cancelar", self.cancel_work, register=False)
        self.cancel_button.pack(side="left", padx=10)
        self.cancel_button.configure(state="disabled")
        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.pack(fill="x", pady=(12, 5))
        self.label(main, textvariable=self.status, size=10, color=MUTED, anchor="w", wraplength=900, justify="left").pack(fill="x")

        result = tk.Frame(main, bg=PANEL, padx=18, pady=13)
        result.pack(fill="both", expand=True, pady=(12, 0))
        self.label(result, "03   REVISAR Y EXPORTAR", 10, ACCENT).pack(anchor="w")
        self.label(result, textvariable=self.summary, size=15, anchor="w").pack(fill="x", pady=(8, 3))
        self.label(result, textvariable=self.detail, size=10, color=MUTED, wraplength=850, justify="left", anchor="w").pack(fill="x")
        row = tk.Frame(result, bg=PANEL)
        row.pack(fill="x", pady=(12, 0))
        self.review_button = self.button(row, "Revisar en Concat", self.review, register=False)
        self.review_button.pack(side="left")
        self.export_button = self.button(row, "Exportar MP4…", self.export, primary=True, register=False)
        self.export_button.pack(side="left", padx=8)
        self.folder_button = self.button(row, "Abrir carpeta", self.open_project_folder, register=False)
        self.folder_button.pack(side="left")
        for widget in (self.review_button, self.export_button, self.folder_button):
            widget.configure(state="disabled")

    def choose_video(self):
        path = filedialog.askopenfilename(title="Selecciona una grabación terminada", filetypes=[("Videos", "*.mp4 *.mkv *.mov *.webm *.avi *.m4v"), ("Todos", "*.*")])
        if path:
            self.input_path.set(path)

    def choose_obs(self):
        path = filedialog.askdirectory(title="Carpeta donde OBS guarda tus grabaciones", initialdir=self.obs_path or str(Path.home()))
        if path:
            self.obs_path = path
            self.save_config()
            self.status.set("Carpeta guardada. Usa «Usar último video» cuando termine tu grabación.")

    def latest(self):
        if not self.obs_path:
            self.choose_obs()
        if not self.obs_path:
            return
        try:
            videos = [p for p in Path(self.obs_path).iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
            if not videos:
                raise ValueError("No hay videos compatibles en esa carpeta.")
            self.input_path.set(str(max(videos, key=lambda p: p.stat().st_mtime)))
            self.status.set("Último video seleccionado. Comprueba que OBS haya terminado de grabar.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Carpeta de grabaciones", str(exc))

    def choose_srt(self):
        path = filedialog.askopenfilename(title="SRT sincronizado con el video original", filetypes=[("Subtítulos SRT", "*.srt")])
        if path:
            self.srt_path = path
            self.caption_mode.set("SRT")
            self.status.set("SRT: " + Path(path).name + " · Se ajustará a los cortes.")

    def choose_output(self):
        path = filedialog.askdirectory(title="Carpeta para guardar los nuevos proyectos")
        if path:
            self.output_path.set(path)
            self.save_config()

    def ensure_concat(self):
        if Path(self.concat_path).is_file():
            return True
        path = filedialog.askopenfilename(title="Selecciona el concat.exe instalado", filetypes=[("Concat", "concat.exe")])
        if path:
            self.concat_path = path
            self.save_config()
            return True
        return False

    def set_busy(self, value):
        self.busy = value
        for widget in self.controls:
            widget.configure(state="disabled" if value else ("readonly" if isinstance(widget, ttk.Combobox) else "normal"))
        for widget in (self.review_button, self.export_button, self.folder_button):
            widget.configure(state="normal" if self.result and not value else "disabled")
        self.cancel_button.configure(state="normal" if value else "disabled")
        if value:
            self.progress.start(12)
        else:
            self.progress.stop()

    def work(self, kind, function):
        self.cancel = threading.Event()
        self.set_busy(True)
        def run():
            try:
                value = function(lambda message: self.queue.put(("progress", message)), self.cancel)
                self.queue.put((kind, value))
            except Cancelled as exc:
                self.queue.put(("cancelled", str(exc)))
            except Exception as exc:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                (CONFIG_DIR / "last-error.log").write_text(traceback.format_exc(), encoding="utf-8")
                self.queue.put(("error", str(exc)))
        threading.Thread(target=run, daemon=True).start()

    def start(self):
        if not self.input_path.get().strip():
            messagebox.showinfo("Elige un video", "Selecciona primero una grabación terminada.")
            return
        if not self.ensure_concat():
            return
        if self.caption_mode.get() == "SRT" and not self.srt_path:
            self.choose_srt()
            if not self.srt_path:
                return
        options = Options(source=self.input_path.get().strip(), output=self.output_path.get(), concat=self.concat_path,
                          silence=self.silence.get(), preset=self.preset.get(), captions=self.caption_mode.get(),
                          srt=self.srt_path, language={"Español": "es", "Português": "pt", "English": "en", "Detectar": "auto"}[self.language.get()],
                          zoom=self.zoom.get(), audio_track=int(self.track.get()))
        self.save_config()
        self.work("prepared", lambda progress, cancel: prepare(options, progress, cancel))

    def get_model(self):
        if (model_path() / "model.bin").is_file():
            self.caption_mode.set("Automáticos")
            self.status.set("Modelo local listo. Subtítulos automáticos activados.")
            return
        self.work("model", download_model)

    def cancel_work(self):
        self.cancel.set()
        self.cancel_button.configure(state="disabled")
        self.status.set("Cancelación solicitada. Esperando a que termine la operación actual…")

    def review(self):
        if self.result:
            try:
                subprocess.Popen([self.concat_path, "--project", self.result["project"]], creationflags=subprocess.CREATE_NO_WINDOW)
                self.status.set("Proyecto abierto para revisar. Guarda los cambios en Concat antes de exportar.")
            except OSError as exc:
                messagebox.showerror("No se pudo abrir Concat", str(exc))

    def export(self):
        if not self.result:
            return
        path = filedialog.asksaveasfilename(title="Exportar a un nuevo MP4", initialdir=self.result["project"],
                                          initialfile="video-editado.mp4", defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if path:
            project = self.result["project"]
            self.work("exported", lambda progress, cancel: export_project(self.concat_path, project, path, progress, cancel))

    def open_project_folder(self):
        if self.result:
            os.startfile(self.result["project"])

    def poll(self):
        try:
            while True:
                kind, value = self.queue.get_nowait()
                if kind == "progress":
                    self.status.set(value)
                    continue
                if kind == "prepared":
                    self.result = value
                    self.summary.set(f"{value['original_seconds']:.0f} s → {value['edited_seconds']:.0f} s  ·  {value['clips']} fragmentos  ·  {value['captions']} subtítulos")
                    notes = " ".join(value["warnings"])
                    self.detail.set((notes + " " if notes else "") + "Revisa los cortes y el texto. Conserva el video original en su ubicación: el proyecto lo referencia.")
                    self.status.set("Listo para revisar o exportar.")
                elif kind == "exported":
                    self.status.set("MP4 guardado: " + value)
                    messagebox.showinfo("Video exportado", "El video está listo:\n" + value)
                elif kind == "model":
                    self.model_button.configure(text="Modelo instalado ✓")
                    self.caption_mode.set("Automáticos")
                    self.status.set("Modelo descargado. Los subtítulos ya pueden generarse sin conexión.")
                elif kind == "cancelled":
                    self.status.set(value)
                elif kind == "error":
                    self.status.set("No se completó el proceso. El original está intacto.")
                    messagebox.showerror("No se pudo completar", value)
                self.set_busy(False)
        except queue.Empty:
            pass
        self.after(150, self.poll)

    def about(self):
        win = tk.Toplevel(self)
        win.title("Acerca de Arroba Editor")
        win.configure(bg=PANEL)
        win.geometry("650x440")
        text = (
            f"Arroba Editor {VERSION} — versión de prueba\n\n"
            "Prepara montajes editables mediante la API de Concat.\n"
            "1. Selecciona una grabación terminada y las acciones.\n"
            "2. Pulsa Preparar edición automática.\n"
            "3. Revisa en Concat o exporta directamente. Si el proyecto está\n"
            "abierto en Concat, guarda y ciérralo antes de exportar aquí.\n\n"
            "Los silencios se detectan por volumen: música y ruido pueden\n"
            "impedir los cortes. El modelo Tiny es rápido, pero requiere revisar\n"
            "los subtítulos. En esta versión se usa una sola pista de audio.\n\n"
            "Software bajo AGPL-3.0-or-later. Concat es un proyecto independiente\n"
            "de Jareer Abdullah y sus colaboradores. Se conserva sin modificar.\n"
            "Código de esta versión: archivo SOURCE.zip junto al ejecutable.\n"
            "Soporte comercial y servicios son compatibles con esta licencia."
        )
        self.label(win, text, 11, TEXT, justify="left", padx=20, pady=20).pack(anchor="w")
        def source():
            folder = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
            archive = folder / "SOURCE.zip"
            os.startfile(str(archive if archive.exists() else folder))
        self.button(win, "Abrir código fuente", source, register=False).pack(anchor="w", padx=20)

    def on_close(self):
        if self.busy:
            messagebox.showinfo("Proceso en curso", "Pulsa Cancelar y espera a que termine antes de cerrar la aplicación.")
            return
        self.save_config()
        self.destroy()


if __name__ == "__main__":
    # --self-test is used on the packaged binary, without opening a GUI.
    if "--self-test" in sys.argv:
        import imageio_ffmpeg
        import faster_whisper
        result = {"version": VERSION, "ffmpeg": imageio_ffmpeg.get_ffmpeg_exe(), "concat": str(find_concat()),
                  "model": str(model_path()), "whisper": faster_whisper.__version__}
        target = Path(sys.argv[sys.argv.index("--self-test") + 1])
        target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    else:
        App().mainloop()
