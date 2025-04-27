import subprocess, sys
from rich.prompt import Prompt

def dispatch_ios_if_needed(repo: str, ref: str):
    pat = Prompt.ask("Paste PAT for iOS workflow (blank to skip)")
    if not pat: return
    subprocess.run([
        "gh","api",f"/repos/{repo}/actions/workflows/ios.yml/dispatches",
        "-f","ref=main","-F",f"inputs[ref]={ref}",
        "-H",f"Authorization: token {pat}"
    ], check=True)
