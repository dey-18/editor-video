# SPDX-License-Identifier: AGPL-3.0-or-later
"""Local chat storage. No credentials, project snapshots or video content."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps

def history_path(identity):
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()
    return Path(os.environ['LOCALAPPDATA']) / 'ArrobaEditor/chats' / (digest + '.json')

def locked_write(function):
    @wraps(function)
    def wrapped(identity, *args, **kwargs):
        target = history_path(identity).with_suffix('.lock')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('a+b') as lock:
            lock.seek(0, 2)
            if lock.tell() == 0:
                lock.write(b'0'); lock.flush()
            lock.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                return function(identity, *args, **kwargs)
            finally:
                lock.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return wrapped

def read(identity):
    target = history_path(identity)
    if not target.exists():
        return []
    data = json.loads(target.read_text(encoding='utf-8'))
    if not isinstance(data, list) or any(not isinstance(m, dict) or m.get('role') not in {'user', 'assistant'} or not isinstance(m.get('content'), str) for m in data):
        raise ValueError('Historial inválido. No se sobrescribió el archivo.')
    return data

@locked_write
def append_turn(identity, user, assistant):
    messages = read(identity)
    now = datetime.now(timezone.utc).isoformat()
    messages.extend([{'role': 'user', 'content': user, 'at': now},
                     {'role': 'assistant', 'content': assistant, 'at': now}])
    target = history_path(identity)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(target)
    return messages

def transcript(messages):
    return '\n\n'.join(('Tú' if m['role'] == 'user' else 'Ruben-bot') + '\n' + m['content'] for m in messages)

@locked_write
def append_event(identity, status, message):
    if status not in {'applied', 'rejected', 'stale', 'undo', 'redo', 'unchanged'}:
        raise ValueError('Estado de acción inválido.')
    messages = read(identity)
    messages.append({'role': 'assistant', 'content': 'Estado del editor: ' + message,
                     'status': status, 'at': datetime.now(timezone.utc).isoformat()})
    target = history_path(identity)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(target)
    return messages

@locked_write
def migrate(identity, legacy_identity):
    target = history_path(identity)
    if target.exists() or not history_path(legacy_identity).exists():
        return
    messages = read(legacy_identity)
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(target)
