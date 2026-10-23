from pathlib import Path
import re
import json

root=Path(__file__).resolve().parents[1]
count=0
for path in sorted((root/'.agents/skills').glob('*/SKILL.md')):
    text=path.read_text(encoding='utf8')
    assert text.startswith('---\n'),f'Frontmatter missing: {path}'
    header,body=text[4:].split('\n---\n',1)
    values=dict(line.split(': ',1) for line in header.splitlines())
    assert values['name']==path.parent.name and re.fullmatch('[a-z0-9-]{1,64}',values['name'])
    assert json.loads(values['description']) and len(body)>100
    assert path.read_bytes()==(root/'.claude/skills'/path.parent.name/'SKILL.md').read_bytes()
    count+=1
assert count==29
print(f'{count} canonical skills and {count} Claude copies validated; no divergent SKILL.md.')
