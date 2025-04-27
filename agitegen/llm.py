"""OpenRouter chat + Aider orchestration."""

from __future__ import annotations
import json, os, time
from pathlib import Path
import httpx, subprocess, shutil, tempfile
from rich.console import Console
from .embed import embed_backend
from .unmet import unmet_requirements
from .utils import run_cmd

console = Console()

PLANNING_MODEL = "google/gemini-2.5-pro-preview-03-25"
DEBUG_MODEL    = "openai/o3"
ORIGIN         = "https://openrouter.ai/api/v1/chat/completions"

def _chat(model: str, msgs: list[dict[str,str]]):
    r = httpx.post(
        ORIGIN,
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": msgs},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def collect_requirements() -> list[str]:
    msgs = [
        {"role":"system","content":"Ask clarifying questions. User will type DONE when finished."},
        {"role":"assistant","content":"Describe your app in one sentence."},
    ]
    while True:
        user = input("🙋 ").strip()
        msgs.append({"role":"user","content":user})
        if user.lower()=="done": break
        reply = _chat(PLANNING_MODEL,msgs)
        print(reply); msgs.append({"role":"assistant","content":reply})
    spec = _chat(PLANNING_MODEL,msgs+[{"role":"assistant","content":"Now output YAML list under key `requirements` where each item is {symbol:<short>, desc:<text>}."}])
    console.print(spec)
    return json.loads(json.dumps(spec))  # rely on YAML subset of JSON

def _run_local_tests(root: Path) -> tuple[bool, str]:
    """Run the local lint + test suite. Returns (success, combined_log)."""
    commands = [
        ["npm", "run", "lint"],
        ["npm", "test"],
        ["flutter", "test"],
        ["flutter", "test", "integration_test"],
    ]
    logs: list[str] = []
    all_ok = True
    for cmd in commands:
        if not shutil.which(cmd[0]):
            # Skip commands that are not available in the local tool-chain
            continue
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        logs.append(proc.stdout + "\n" + proc.stderr)
        if proc.returncode != 0:
            all_ok = False
    return all_ok, "\n".join(logs)

def run_aider_until_green(root: Path, backend: str):
    """Iterate with Aider until there are no unmet symbols **and** the local test suite passes.

    At most 5 passes – first with the planning model, subsequent with the debug model.
    """
    passes = 0
    while passes < 5:
        unmet = unmet_requirements(root)
        tests_ok, test_log = _run_local_tests(root)
        # If everything is green, we're done
        if not unmet and tests_ok:
            console.print("[green]✅ Local tests passed and no unmet symbols – build is green!")
            return

        # Build the message for Aider summarising unmet requirements and failing tests
        msg_dict: dict[str, object] = {}
        if unmet:
            msg_dict["unmet"] = unmet
        if not tests_ok:
            # Save failing log to a temp file for easier reference and include a summary snippet
            tmp_log_file = tempfile.NamedTemporaryFile(delete=False, suffix="_aider_fail.log", mode="w", encoding="utf-8")
            tmp_log_file.write(test_log)
            tmp_log_file.close()
            # only send the tail 100 lines to avoid context bloat
            tail = "\n".join(test_log.splitlines()[-100:])
            msg_dict["failing_tests_tail"] = tail
        # Add backend docs snippet (max 3 chunks) if applicable
        docs = _get_backend_docs(root, backend) if backend != "none" else []
        if docs:
            msg_dict["docs"] = docs[:3]

        model = DEBUG_MODEL if passes else PLANNING_MODEL
        run_cmd([
            "aider", "--continue", "--map-tokens", "25000", "--max-chat-history", "20000",
            "--model", model,
            "--message", json.dumps(msg_dict), ".",
        ])
        passes += 1

    # If we exit the loop still failing, abort with non-zero exit code
    console.print("[red]❌  Maximum Aider passes reached but issues remain. Aborting.")
    raise SystemExit(1)

def _get_backend_docs(root: Path, backend:str):
    store = root/"embeddings"
    if not store.exists(): return []
    client = chromadb.PersistentClient(str(store))
    col    = client.get_collection("docs")
    return col.peek()["documents"]
