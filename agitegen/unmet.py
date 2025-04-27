"""YAML-aware requirement checker with ripgrep JSON."""

from __future__ import annotations
import json, subprocess, sys, textwrap, yaml
from pathlib import Path
from .utils import console

def _ensure_rg():
    try:
        ver = subprocess.check_output(["rg","--version"], text=True)
        if "13." in ver or "14." in ver: return "rg"
    except Exception: pass
    rg_bin = Path.home()/".agitegen/rg"
    if not rg_bin.exists():
        rg_bin.parent.mkdir(exist_ok=True)
        url = "https://github.com/BurntSushi/ripgrep/releases/download/13.0.0/ripgrep-13.0.0-x86_64-unknown-linux-musl.tar.gz"
        subprocess.run(f"curl -sL {url}|tar -xz --strip-components 1 -C {rg_bin.parent}", shell=True, check=True)
    return str(rg_bin)

RG = _ensure_rg()

def unmet_requirements(root: Path):
    data = yaml.safe_load((root/"requirements.md").read_text())
    unmet = []
    reqs = data.get("requirements") if isinstance(data, dict) else None
    if not isinstance(reqs, list):
        console.print("[yellow]requirements.md key 'requirements' is not a list – skipping unmet requirements check.")
        return unmet
    for item in reqs:
        if not isinstance(item, dict) or "symbol" not in item:
            continue
        sym = item["symbol"]
        rg  = subprocess.run([RG,"--json","-F",sym,str(root)], capture_output=True, text=True)
        if not rg.stdout.strip():
            unmet.append(sym)
    return unmet
