# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate a reviewable plan; never writes the open project."""
import json
import sys
import threading
import urllib.request
from ai_settings import load
from editor_agent import SYSTEM, tools_for
from engine import ConcatClient, find_concat
from chat_history import read, append_turn, append_event, transcript, history_path, migrate
from agent_context import catalogue, project_summary, describe, effects_context

OPS = {'title_add': 'addTextClip', 'clip_update': 'updateClip',
       'clip_transform': 'setClipTransform', 'keyframe_set': 'setClipKey',
       'effect_layer_add': 'addLayerClip'}
OPS.update({'clip_trim': 'trimClip', 'clips_split': 'splitClips',
            'clips_remove': 'removeClips', 'clip_speed': 'setClipSpeed'})

def plan(data):
    # Older native builds do not send a project path. Their history is scoped
    # to project name + source identities until the path-aware build is used.
    view = data.get('snapshot') or {}
    legacy_identity = json.dumps({'name': view.get('settings', {}).get('name'),
               'media': sorted(m.get('path', '') for m in view.get('project', {}).get('media', []))}, sort_keys=True)
    identity = data.get('projectPath') or legacy_identity
    if identity != legacy_identity:
        migrate(identity, legacy_identity)
    history = read(identity)
    if data.get('action') == 'record':
        history = append_event(identity, data['status'], data['message'])
        return {'commands': [], 'message': data['message'], 'history': history[-100:]}
    if not data.get('instruction', '').strip():
        return {'commands': [], 'message': 'Historial guardado en este equipo.', 'history': history[-100:]}
    settings = load()
    if not settings:
        raise ValueError('Configura primero OpenRouter en Cuenta e IA.')
    contract, effects = catalogue()
    effect_context = effects_context(effects, data['instruction'] + ' ' + ' '.join(m['content'] for m in history[-4:]))
    tools = [t for t in tools_for(contract) if t['function']['name'] in OPS]
    messages = [{'role': 'system', 'content': SYSTEM + '\nLa lectura del proyecto y catálogo ya se adjunta. El historial contiene propuestas, no pruebas de acciones realizadas. El estado actual del proyecto es la autoridad. Propón acciones en UNA respuesta con herramientas. Las acciones NO están aplicadas todavía. Máximo 8. Si falta información pregunta en texto.'},
                *[{'role': m['role'], 'content': m['content']} for m in history[-16:]],
                {'role': 'user', 'content': json.dumps({'instruction': data['instruction'], 'project': project_summary(data['snapshot']), 'effects': effect_context}, ensure_ascii=False)}]
    payload = {'model': settings['model'], 'messages': messages, 'tools': tools,
               'tool_choice': 'auto', 'temperature': 0, 'max_tokens': 4000}
    request = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps(payload).encode(),
              headers={'Authorization': 'Bearer ' + settings['key'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=90) as response:
        result = json.load(response)
    choice = result['choices'][0]
    if choice.get('finish_reason') not in {'stop', 'tool_calls'}:
        raise ValueError('Respuesta incompleta; vuelve a intentarlo.')
    message = choice['message']
    calls = message.get('tool_calls') or []
    if len(calls) > 8:
        raise ValueError('Demasiadas acciones. Pide un cambio más concreto.')
    commands, descriptions = [], []
    for call in calls:
        name = call['function']['name']
        if name not in OPS:
            raise ValueError('Herramienta no autorizada.')
        args = json.loads(call['function']['arguments'])
        if not isinstance(args, dict) or 'path' in args or 'op' in args:
            raise ValueError('Argumentos no autorizados.')
        commands.append({'op': OPS[name], **args})
        descriptions.append(describe(name, args))
    answer = ('Propuesta pendiente de aplicar:\n' + '\n'.join(descriptions)) if calls else (message.get('content') or 'No se propusieron cambios.')
    history = append_turn(identity, data['instruction'], answer)
    return {'commands': commands, 'message': 'Propuesta lista para revisar.' if calls else '', 'history': history[-100:]}

if __name__ == '__main__':
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        print(json.dumps(plan(json.load(sys.stdin)), ensure_ascii=False))
    except Exception:
        print(json.dumps({'commands': [], 'message': 'No se pudo generar el plan. Revisa la conexión, el modelo y que admita herramientas.'}))
        sys.exit(1)
