from __future__ import annotations
import os, platform, shutil, subprocess, sys
from pathlib import Path
from typing import Sequence
from rich.console import Console

console = Console()

def run_cmd(cmd: Sequence[str] | str, cwd: Path | None = None, check: bool=True):
    console.log(f"[grey]$ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str))
        if check and r.returncode != 0:
            console.print(f"[red]Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
            raise SystemExit(r.returncode)
    except FileNotFoundError as e:
        console.print(f"[yellow]Skipping command – binary not found: {e}")

def ensure_env(var: str):
    if not os.getenv(var):
        console.print(f"[red]❌  {var} environment variable not set")
        raise SystemExit(1)

def is_mac() -> bool:
    return platform.system() == "Darwin"
