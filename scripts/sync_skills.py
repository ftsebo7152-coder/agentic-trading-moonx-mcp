"""Generate Claude copies from the canonical Codex skill tree, without symlinks."""
from pathlib import Path
import shutil

root=Path(__file__).resolve().parents[1]
for source in sorted((root/'.agents/skills').iterdir()):
    if not source.is_dir():continue
    dest=root/'.claude/skills'/source.name
    shutil.copytree(source,dest,dirs_exist_ok=True)
print('Skill trees synchronized.')
