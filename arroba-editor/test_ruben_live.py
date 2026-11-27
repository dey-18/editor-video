import json
from pathlib import Path
from ruben_plan import plan
from engine import ConcatClient,find_concat
root=Path('test-output').resolve()
report=json.loads((root/'integration-result.json').read_text(encoding='utf-8'))
project=report['report']['project']
with ConcatClient(find_concat(),[root]) as c:
    c.tool('project_open',path=project)
    snapshot=c.tool('project_get',path=project)
    result=plan({'instruction':'Añade un título que diga Prueba Ruben-bot desde el segundo 0 durante 2 segundos encima del video. No cambies nada más.', 'snapshot':snapshot})
    assert result['commands'],result
    assert all(x['op']=='addTextClip' for x in result['commands']),result
    c.tool('edit_apply',path=project,command={'op':'batch','commands':result['commands']})
    after=c.tool('timeline_read',path=project)
    assert any(x.get('text')=='Prueba Ruben-bot' for x in after['timeline']['clips']),after
    c.tool('edit_undo',path=project)
    c.tool('project_close',path=project,save=False)
    print('OPENROUTER TOOL + TITLE + UNDO: OK')
