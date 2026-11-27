# SPDX-License-Identifier: AGPL-3.0-or-later
"""Windows DPAPI storage and OpenRouter connection test. JSON on stdin."""
import ctypes
from ctypes import wintypes
import base64
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

def public_status():
    if not path().is_file():
        return {'model': '', 'status': 'OpenRouter: sin configurar'}
    stored = json.loads(path().read_text(encoding='utf-8'))
    load()  # Verify that Windows can decrypt it without exposing the key.
    checked = stored.get('verified_at')
    label = 'Configurado · pendiente de prueba'
    if checked:
        local = datetime.fromisoformat(checked).astimezone().strftime('%d/%m/%Y %H:%M')
        label = 'Conexión verificada el ' + local + ' · no es un estado en tiempo real'
    return {'model': stored['model'], 'status': 'OpenRouter: ' + label + '\nClave guardada y protegida en Windows.'}

def remember_verified(key, model):
    saved = load()
    if not saved or (key and key != saved['key']) or model.strip() != saved['model']:
        return
    stored = json.loads(path().read_text(encoding='utf-8'))
    stored['verified_at'] = datetime.now(timezone.utc).isoformat()
    temporary = path().with_suffix('.tmp')
    temporary.write_text(json.dumps(stored), encoding='utf-8')
    temporary.replace(path())

class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_byte))]

def protect(value, decrypt=False):
    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    target = Blob()
    function = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise RuntimeError('No se pudo acceder al almacén protegido de Windows.')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.windll.kernel32.LocalFree(target.data)

def path():
    return Path(os.environ['LOCALAPPDATA']) / 'ArrobaEditor/openrouter.json'

def load():
    if not path().is_file():
        return {}
    data = json.loads(path().read_text(encoding='utf-8'))
    return {'key': protect(base64.b64decode(data['secret']), True).decode(), 'model': data['model']}

def save(key, model):
    if not key:
        key = load().get('key', '')
    if not key or not model.strip():
        raise ValueError('Escribe una clave y el identificador del modelo.')
    path().parent.mkdir(parents=True, exist_ok=True)
    data = {'secret': base64.b64encode(protect(key.encode())).decode(), 'model': model.strip()}
    temporary = path().with_suffix('.tmp')
    temporary.write_text(json.dumps(data), encoding='utf-8')
    temporary.replace(path())

def test(key, model):
    key = key or load().get('key', '')
    if not key or not model.strip():
        raise ValueError('Falta la clave o el modelo.')
    payload = {'model': model.strip(), 'messages': [{'role': 'user', 'content': 'Responde OK.'}], 'max_tokens': 16}
    request = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps(payload).encode(),
                headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        if not result.get('choices'):
            raise ValueError()
    except urllib.error.HTTPError as error:
        messages = {401: 'La API key no es válida o fue revocada.',
                    402: 'OpenRouter requiere saldo para esta solicitud.',
                    404: 'El identificador del modelo no está disponible.',
                    429: 'Se alcanzó el límite de solicitudes. Espera y vuelve a probar.',
                    400: 'El modelo rechazó la solicitud. Revisa su identificador y compatibilidad.'}
        raise RuntimeError(messages.get(error.code, f'OpenRouter respondió con error {error.code}.')) from None
    except Exception:
        raise RuntimeError('Conexión fallida. Revisa clave, modelo, saldo y conexión.') from None

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
    try:
        data = json.load(sys.stdin)
        if data['action'] == 'test':
            test(data['key'], data['model'])
            remember_verified(data['key'], data['model'])
            print(json.dumps({'model': data['model'], 'status': 'Conexión correcta.\n' + public_status()['status']}, ensure_ascii=False))
        elif data['action'] == 'status':
            print(json.dumps(public_status(), ensure_ascii=False))
        else:
            save(data['key'], data['model'])
            print(json.dumps(public_status(), ensure_ascii=False))
    except Exception as error:
        print(str(error))
        sys.exit(1)
