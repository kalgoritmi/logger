from pathlib import Path
from typing import List

def get_existing_backups(file_path: Path, sort: bool = False) -> List[Path]:
    """Find all backup files for the given log file."""
    globbing_pattern = file_path.with_suffix(f".*{file_path.suffix}")
    existing_backups = [
        backup for backup in file_path.parent.glob(globbing_pattern.name)
        if backup.stem.split('.')[-1].isdigit()
    ]
    return existing_backups if not sort else sorted(
        existing_backups,
        key=lambda p: int(p.stem.split('.')[-1])
    )


def get_last_rollover_seq(file_path: Path) -> int:
    """Get the sequence number of the last rollover backup file."""
    existing_backups = get_existing_backups(file_path, sort=True)
    if not existing_backups:
        return -1
    return  int(existing_backups[-1].stem.split('.')[-1])
