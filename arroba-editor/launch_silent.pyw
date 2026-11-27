# SPDX-License-Identifier: AGPL-3.0-or-later
"""Launch the native development build without allocating a Windows console."""
import os
from pathlib import Path
import subprocess
import ctypes
import shutil
import uuid
import sys
import json

try:
    root = Path(__file__).resolve().parent.parent
    ffmpeg = next((root / 'ffmpeg-dev').glob('*/bin'))
    env = os.environ.copy()
    env['PATH'] = str(ffmpeg) + os.pathsep + r'C:\Program Files\Concat' + os.pathsep + env.get('PATH', '')
    source = root / 'src/target/quick/concat.exe'
    try:
        state = json.loads((root / 'arroba-editor/build-state.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        state = {}
    previous = list((root / 'arroba-editor/runtime').glob('*/ArrobaEditor.exe'))
    if state.get('state') == 'running' and previous:
        executable = max(previous, key=lambda p: p.stat().st_mtime_ns)
    else:
        stat = source.stat()
        runtime = root / 'arroba-editor/runtime' / f'{stat.st_mtime_ns}-{stat.st_size}'
        runtime.mkdir(parents=True, exist_ok=True)
        executable = runtime / 'ArrobaEditor.exe'
        if not executable.exists():
            temporary = runtime / (uuid.uuid4().hex + '.tmp')
            shutil.copy2(source, temporary)
            temporary.replace(executable)
    subprocess.Popen([str(executable), *sys.argv[1:]], cwd=str(root), env=env,
                     creationflags=subprocess.CREATE_NO_WINDOW,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except Exception:
    ctypes.windll.user32.MessageBoxW(None, 'No se pudo abrir Arroba Editor. Revisa la instalación.', 'Arroba Editor', 16)
