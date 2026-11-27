# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cache stable engine metadata and keep private filesystem paths out of prompts."""
import json
import os
from pathlib import Path
import time
import re
import unicodedata
from engine import ConcatClient, find_concat

def catalogue():
    exe = find_concat()
    version = [str(exe), exe.stat().st_size, exe.stat().st_mtime_ns]
    target = Path(os.environ['LOCALAPPDATA']) / 'ArrobaEditor/cache/agent-catalogue.json'
    try:
        stored = json.loads(target.read_text(encoding='utf-8'))
        if stored['version'] == version and 0 <= time.time() - stored['at'] < 86400:
            return stored['tools'], stored['effects']
    except (OSError, ValueError, KeyError, TypeError):
        pass
    with ConcatClient(exe, []) as client:
        tools = client.ask('tools/list', {})['tools']
        effects = client.tool('effects_list')
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps({'version': version, 'at': time.time(), 'tools': tools, 'effects': effects}), encoding='utf-8')
        temporary.replace(target)
    except OSError:
        pass  # Metadata caching must not prevent editing.
    return tools, effects

def project_summary(view):
    project = view.get('project') or {}
    timelines = project.get('timelines') or []
    active = next((t for t in timelines if t.get('id') == project.get('activeTimelineId')), timelines[0] if timelines else {})
    media_keys = {'id', 'name', 'duration', 'kind', 'width', 'height', 'hasAudio'}
    return {'settings': view.get('settings', {}), 'timeline': active,
            'media': [{k: v for k, v in m.items() if k in media_keys} for m in project.get('media', [])]}

def describe(name, args):
    clip = args.get('clipId', 'seleccionado')
    if name == 'clip_trim':
        edge = 'inicio' if args.get('edge') == 'start' else 'final'
        return f"Ajustar el {edge} de {clip} en {args.get('delta', 0)} s; cerrar huecos: {'sí' if args.get('ripple') else 'no'}."
    if name == 'clips_split':
        return f"Dividir {', '.join(args.get('clipIds', []))} en el segundo {args.get('time', 0)}."
    if name == 'clips_remove':
        return f"Quitar del montaje: {', '.join(args.get('clipIds', []))}. Cerrar huecos: {'sí' if args.get('ripple') else 'no'}."
    if name == 'clip_speed':
        return f"Cambiar la velocidad de {clip} a {args.get('speed', 1)}×."
    if name == 'title_add':
        return f"Añadir el título «{args.get('style', {}).get('content', '')}» en {args.get('start', 0)} s, durante {args.get('duration', 4)} s."
    if name == 'clip_transform':
        labels = {'scale': 'Escala', 'offsetX': 'Posición horizontal', 'offsetY': 'Posición vertical', 'rotation': 'Rotación', 'stretchX': 'Ancho', 'stretchY': 'Alto'}
        fields = ', '.join(f'{label}: {args[key]}' for key, label in labels.items() if key in args)
        return f'Ajustar {clip}: {fields}.'
    if name == 'clip_update':
        patch = args.get('patch', {})
        labels = {'volume': 'volumen', 'opacity': 'opacidad', 'fadeIn': 'entrada', 'fadeOut': 'salida', 'muted': 'silencio', 'text': 'texto', 'videoEffects': 'efectos', 'filters': 'filtros'}
        parts = []
        for key, value in patch.items():
            if key == 'volume' and isinstance(value, (int, float)):
                parts.append(f'volumen a {value * 100:g} %')
            elif key == 'text' and isinstance(value, dict):
                parts.append('texto: «' + str(value.get('content', '(solo estilo)')) + '»')
            elif isinstance(value, (str, int, float, bool)):
                parts.append(f'{labels.get(key, key)}: {value}')
            else:
                parts.append(labels.get(key, key))
        fields = ', '.join(parts)
        return f'Cambiar {fields} del clip {clip}.'
    if name == 'keyframe_set':
        return f"Animar {args.get('property')} de {clip}: valor {args.get('value')} en {round(args.get('at', 0) * 100)} % del clip."
    return f"Añadir efecto {args.get('effectId', '')} en {args.get('start', 0)} s durante {args.get('duration', 5)} s."

def effects_context(effects, text):
    """Keep the ID/name index complete, but send detailed knobs only for matches."""
    if not isinstance(effects, list):
        return effects
    def normalized(value):
        return ''.join(c for c in unicodedata.normalize('NFKD', str(value).lower()) if not unicodedata.combining(c))
    words = {w for w in re.findall(r'[a-z0-9]+', normalized(text)) if len(w) > 3}
    aliases = {'desenfoque': 'blur', 'temblor': 'shake', 'cinematografico': 'cinematic',
               'brillo': 'brightness', 'contraste': 'contrast', 'saturacion': 'saturation',
               'fundido': 'fade', 'ruido': 'noise', 'vintage': 'retro'}
    words |= {alias for word, alias in aliases.items() if word in words}
    ranked = []
    for index, effect in enumerate(effects):
        haystack = normalized(' '.join(str(effect.get(k, '')) for k in ('id', 'name', 'category')))
        score = sum(word in haystack for word in words)
        if score:
            ranked.append((-score, index, effect))
    return {'index': [{k: e[k] for k in ('id', 'name', 'kind') if k in e} for e in effects],
            'details': [e for _, _, e in sorted(ranked, key=lambda r: (r[0], r[1]))[:12]]}
