# SPDX-License-Identifier: AGPL-3.0-or-later
"""Headless adapter used by the native editor, no second application window."""
import json
from pathlib import Path
import sys
import threading
from engine import Options, find_concat, model_path, prepare

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
    try:
        import os
        import time
        from ai_settings import load
        event_mode = '--events' in sys.argv
        options = json.load(sys.stdin) if event_mode else {}
        if event_mode and options.get('captions', True) and not (model_path() / 'model.bin').is_file():
            raise ValueError('El modelo local de subtítulos no está instalado. Desactiva los subtítulos o instala el modelo antes de continuar.')
        cancel = threading.Event()
        def progress(message):
            if event_mode:
                print(json.dumps({'progress': message}, ensure_ascii=False), flush=True)
            else:
                print(message, file=sys.stderr, flush=True)
        if event_mode:
            sys.stdout.reconfigure(encoding='utf-8')
            def watch_cancel():
                import ctypes
                kernel = ctypes.windll.kernel32
                kernel.OpenProcess.restype = ctypes.c_void_p
                kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
                kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                parent = kernel.OpenProcess(0x100000, False, os.getppid())
                flag = Path(options['cancelFile'])
                try:
                    while not cancel.wait(.2):
                        if flag.exists() or (parent and kernel.WaitForSingleObject(parent, 0) == 0):
                            cancel.set()
                finally:
                    if parent:
                        kernel.CloseHandle(parent)
            threading.Thread(target=watch_cancel, daemon=True).start()
        settings = load()
        if settings:
            os.environ['OPENROUTER_API_KEY'] = settings['key']
            os.environ['ARROBA_OPENROUTER_MODEL'] = settings['model']
            os.environ['ARROBA_AI_CAPTIONS'] = '1'
        report = prepare(Options(source=sys.argv[1], output=sys.argv[2], concat=str(find_concat()),
                                 silence=options.get('silence', True), preset=options.get('preset', 'Normal'),
                                 audio_track=options.get('audioTrack', 1), language=options.get('language', 'es'),
                                 captions=('Automáticos' if options.get('captions', True) and (model_path() / 'model.bin').is_file() else 'Ninguno')),
                         progress, cancel)
        summary = f"{report['original_seconds']:.1f} s → {report['edited_seconds']:.1f} s · {report['removed_seconds']:.1f} s eliminados · {report['clips']} fragmentos · {report['captions']} subtítulos"
        print(json.dumps({'project': report['project'], 'summary': summary, 'warnings': report['warnings']}, ensure_ascii=False), flush=True)
    except Exception as error:
        if '--events' in sys.argv:
            print(json.dumps({'error': str(error)}, ensure_ascii=False), flush=True)
        else:
            print(str(error), file=sys.stderr)
        sys.exit(1)
