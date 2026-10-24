"""Synchronize only agentic-trading-master into the user's installed skill tree."""
from datetime import datetime,timezone
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import tempfile
import os


def update(destination=None):
    root=Path(__file__).resolve().parents[1]
    source=(root/'.agents/skills/agentic-trading-master').resolve(strict=True)
    target=Path(destination or Path.home()/'.agents/skills/agentic-trading-master').expanduser().resolve()
    if target.name!='agentic-trading-master' or target==source:
        raise ValueError('Expected a distinct installed agentic-trading-master directory')
    if source in target.parents or target in source.parents:
        raise ValueError('Source and installation must not contain each other')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    copied=[];backups=[]
    for item in sorted(source.rglob('*')):
        if not item.is_file():continue
        if item.is_symlink():raise ValueError('Symlinked skill source is not supported')
        relative=item.relative_to(source);dest=target/relative
        if not dest.resolve().is_relative_to(target):raise ValueError('Destination escapes skill directory')
        raw=item.read_bytes();dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists() and dest.read_bytes()==raw:continue
        if dest.exists():
            backup=dest.with_name(dest.name+'.backup-'+stamp);shutil.copy2(dest,backup);backups.append(str(backup))
        fd,name=tempfile.mkstemp(prefix=dest.name+'.',suffix='.tmp',dir=dest.parent)
        try:
            with os.fdopen(fd,'wb') as handle:handle.write(raw)
            os.replace(name,dest)
        finally:
            if os.path.exists(name):os.unlink(name)
        if hashlib.sha256(dest.read_bytes()).digest()!=hashlib.sha256(raw).digest():raise OSError('Skill copy verification failed')
        copied.append(str(relative))
    return {'target':str(target),'updated_files':copied,'backups':backups,'tasks_started':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination');args=parser.parse_args()
    print(json.dumps(update(args.destination),ensure_ascii=False))
