"""Guards: abort if OpenRouter credits <10 % or GH Actions minutes <100."""

from __future__ import annotations
import json, os, sys, httpx, subprocess
from rich.console import Console

console = Console()

def ensure_openrouter_quota(threshold=0.10):
    key = os.getenv("OPENROUTER_API_KEY")
    if not key: return
    url = "https://openrouter.ai/api/v1/usage"
    data = httpx.get(url, headers={"Authorization": f"Bearer {key}"}).json()
    avail = data["available"]; limit = data["limit"]
    if limit and avail / limit < threshold:
        console.print(f"[red]OpenRouter credits low ({avail}/{limit}) → aborting.")
        sys.exit(1)

def ensure_github_minutes(threshold=100):
    try:
        out = subprocess.check_output(["gh","api","/user/settings/billing/actions"], text=True)
        used = json.loads(out)["included_minutes_used"]
        remain = 2000-used
        if remain < threshold:
            console.print(f"[red]GitHub Actions minutes low ({remain}) → aborting.")
            sys.exit(1)
    except Exception as e:
        console.log(f"[yellow]Skipping GH minute check: {e}")
