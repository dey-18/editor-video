# SPDX-License-Identifier: AGPL-3.0-or-later
"""Visible development build status; never fabricates a percentage."""
from pathlib import Path
import json
import time
from datetime import datetime
import ctypes
import sys
import tkinter as tk
from tkinter import ttk

root = Path(__file__).resolve().parent
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateMutexW.restype = ctypes.c_void_p
kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
monitor_mutex = kernel.CreateMutexW(None, False, 'Local\\ArrobaEditorBuildMonitor')
if monitor_mutex and ctypes.get_last_error() == 183:
    sys.exit(0)
window = tk.Tk()
window.title('Arroba Editor · Estado de compilación')
window.geometry('850x500')
window.configure(bg='#101827')
status = tk.StringVar()
detail = tk.StringVar()
tk.Label(window, textvariable=status, bg='#101827', fg='#8be0b2', font=('Segoe UI', 20, 'bold')).pack(anchor='w', padx=24, pady=(20, 8))
tk.Label(window, textvariable=detail, bg='#101827', fg='#dce5f2', font=('Segoe UI', 11)).pack(anchor='w', padx=24)
bar = ttk.Progressbar(window, mode='indeterminate')
bar.pack(fill='x', padx=24, pady=16)
log = tk.Text(window, bg='#182234', fg='#e1e8f4', font=('Consolas', 10), wrap='word', relief='flat')
log.pack(fill='both', expand=True, padx=24, pady=(0, 16))
tk.Label(window, text='Esta ventana observa la compilación. Cerrarla no detiene el proceso.', bg='#101827', fg='#a7b7cc').pack(pady=(0, 12))
active_before = False

def alive(pid):
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000, False, int(pid))
    if not handle:
        return False
    try:
        return kernel.WaitForSingleObject(handle, 0) == 258
    finally:
        kernel.CloseHandle(handle)

def update():
    global active_before
    try:
        text = (root / 'integrated-build.log').read_text(encoding='utf-8', errors='replace')
    except OSError:
        text = ''
    try:
        build = json.loads((root / 'build-state.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        build = {}
    active = build.get('state') == 'running' and alive(build.get('pid', 0))
    if active:
        elapsed = max(0, time.time() - datetime.fromisoformat(build['started']).timestamp())
        status.set('Compilando Arroba Editor…')
        detail.set(f'Transcurrido: {int(elapsed // 60)} min {int(elapsed % 60)} s · No hay un porcentaje fiable disponible.')
    elif build.get('state') == 'done' or (not build and 'Finished `quick`' in text):
        status.set('Compilación terminada correctamente ✓')
        detail.set('La nueva versión está lista. Reinicia Arroba Editor para cargarla.')
    elif build.get('state') == 'failed' or 'error: could not compile' in text or 'error: failed' in text:
        status.set('La compilación falló')
        detail.set('El registro inferior contiene el error. La aplicación anterior no se actualizó.')
    elif build.get('state') == 'running':
        status.set('Compilación interrumpida o sin seguimiento')
        detail.set('No se detecta el proceso registrado. Revisa el final del registro.')
    else:
        status.set('Sin compilación activa registrada')
        detail.set('Aquí aparecerá el estado cuando se inicie la siguiente compilación.')
    if active != active_before:
        bar.start(12) if active else bar.stop()
        active_before = active
    log.configure(state='normal')
    log.delete('1.0', 'end')
    log.insert('end', '\n'.join(text.splitlines()[-60:]) or 'Todavía no hay registro.')
    log.see('end')
    log.configure(state='disabled')
    window.after(1000, update)

update()
window.mainloop()
