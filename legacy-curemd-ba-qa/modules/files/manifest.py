"""
Files Module — file organization, analysis, and storage management.

Merged from: local_ai_file_organizer v1+v2, files_analysis, storage_guardian.
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List

from core.agents.tools import get_registry, tool

logger = logging.getLogger(__name__)


@tool(name="organize_files", description="Organize files in a directory by type, date, or custom rules", module="files")
def organize_files(directory: str, strategy: str = "type", dry_run: bool = True) -> Dict:
    """
    Organize files in a directory.

    Strategies: type (by extension), date (by modified date), size (by size ranges)
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return {"error": f"Directory not found: {directory}"}

    files = [f for f in dir_path.iterdir() if f.is_file()]
    plan = {"strategy": strategy, "total_files": len(files), "moves": [], "dry_run": dry_run}

    for f in files:
        if strategy == "type":
            ext = f.suffix.lower().lstrip(".") or "other"
            dest = dir_path / ext / f.name
        elif strategy == "date":
            mtime = f.stat().st_mtime
            import time
            date_str = time.strftime("%Y-%m", time.localtime(mtime))
            dest = dir_path / date_str / f.name
        elif strategy == "size":
            size = f.stat().st_size
            if size < 1024 * 1024:
                bucket = "small"
            elif size < 100 * 1024 * 1024:
                bucket = "medium"
            else:
                bucket = "large"
            dest = dir_path / bucket / f.name
        else:
            continue

        plan["moves"].append({"from": str(f), "to": str(dest)})

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            f.rename(dest)

    return plan


@tool(name="analyze_files", description="Analyze files in a directory — types, sizes, duplicates", module="files")
def analyze_files(directory: str, check_duplicates: bool = False) -> Dict:
    """Analyze files in a directory."""
    dir_path = Path(directory)
    if not dir_path.exists():
        return {"error": f"Directory not found: {directory}"}

    stats = {"total_files": 0, "total_size": 0, "by_type": {}, "largest": []}
    hashes = {} if check_duplicates else None

    for f in dir_path.rglob("*"):
        if not f.is_file():
            continue
        size = f.stat().st_size
        ext = f.suffix.lower()
        stats["total_files"] += 1
        stats["total_size"] += size
        stats["by_type"][ext] = stats["by_type"].get(ext, 0) + 1

        if check_duplicates:
            h = hashlib.md5(f.read_bytes()).hexdigest()
            hashes.setdefault(h, []).append(str(f))

    stats["total_size_mb"] = round(stats["total_size"] / (1024 * 1024), 2)
    if check_duplicates and hashes:
        stats["duplicates"] = {
            h: paths for h, paths in hashes.items() if len(paths) > 1
        }
    return stats


@tool(name="guard_storage", description="Check storage usage and alert on thresholds", module="files")
def guard_storage(path: str = "/", threshold_mb: float = 1000) -> Dict:
    """Check storage usage at a given path."""
    target = Path(path)
    if not target.exists():
        return {"error": f"Path not found: {path}"}

    total_size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    total_mb = total_size / (1024 * 1024)

    return {
        "path": path,
        "total_size_mb": round(total_mb, 2),
        "threshold_mb": threshold_mb,
        "over_threshold": total_mb > threshold_mb,
        "status": "WARNING" if total_mb > threshold_mb else "OK",
    }


def register():
    return {
        "name": "files",
        "description": "File organization, analysis, and storage management",
        "version": "2.0.0",
        "tools": ["organize_files", "analyze_files", "guard_storage"],
        "routes": [
            {"method": "POST", "path": "/files/organize", "handler": "organize_files"},
            {"method": "GET", "path": "/files/analyze", "handler": "analyze_files"},
            {"method": "GET", "path": "/files/storage", "handler": "guard_storage"},
        ],
    }
