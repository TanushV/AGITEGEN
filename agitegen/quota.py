"""Guards: abort if OpenRouter credits <10 % or GH Actions minutes <100."""

from __future__ import annotations
import json, os, sys, httpx, subprocess
from rich.console import Console
from contextlib import contextmanager

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

def _get_openrouter_usage():
    key = os.getenv("OPENROUTER_API_KEY");
    if not key: return 0, 0
    data = httpx.get("https://openrouter.ai/api/v1/usage", headers={"Authorization": f"Bearer {key}"}).json()
    return data["available"], data["limit"]

class _SessionCost:
    def __enter__(self):
        self.start_avail, self.start_limit = _get_openrouter_usage(); return self
    def __exit__(self,*a):
        end_avail, _ = _get_openrouter_usage()
        spent = self.start_avail - end_avail
        if spent:
            console.print(f"[cyan]💸 OpenRouter tokens spent this build: {spent}")

# helper to wrap build cost reporting
@contextmanager
def measure_session_cost():
    token_ctx = _SessionCost()
    token_ctx.__enter__()
    try:
        yield
    finally:
        token_ctx.__exit__(None,None,None)
