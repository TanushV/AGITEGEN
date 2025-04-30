"""OpenRouter chat + Aider orchestration."""

from __future__ import annotations
import json, os, time
import yaml
from pathlib import Path
import httpx, subprocess, shutil, tempfile
from rich.console import Console
from .embed import embed_backend
from .unmet import unmet_requirements
from .tester import run_local_tests
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

def collect_requirements() -> list[dict]:
    msgs = [
        {"role": "system", "content": "Ask clarifying questions. User will type DONE when finished."},
        {"role": "assistant", "content": "Describe your app in one sentence."},
        {
            "role": "assistant",
            "content": (
                "Which backend do you plan to use first?\n"
                "If you might switch or add others later, list them all.\n"
                "For each one, describe the data tables / collections you foresee."),
        },
    ]
    while True:
        user = input("🙋 ").strip()
        msgs.append({"role":"user","content":user})
        if user.lower()=="done": break
        reply = _chat(PLANNING_MODEL,msgs)
        print(reply); msgs.append({"role":"assistant","content":reply})
    spec = _chat(PLANNING_MODEL,msgs+[{"role":"assistant","content":"Now output YAML list under key `requirements` where each item is {symbol:<short>, desc:<text>}."}])
    console.print(spec)
    # Parse the YAML-formatted specs into Python and return the list
    parsed = yaml.safe_load(spec)
    if isinstance(parsed, dict):
        reqs = parsed.get("requirements", [])
        if isinstance(reqs, list):
            return reqs
    # Fallback: no valid requirements list detected
    console.print("[yellow]No valid YAML requirements list produced; continuing without explicit requirements.")
    return []

def run_aider_until_green(root: Path, backend: str):
    """Iterate with Aider until there are no unmet symbols **and** the local test suite passes.

    At most 5 passes – first with the planning model, subsequent with the debug model.
    """
    passes = 0
    while passes < 5:
        unmet = unmet_requirements(root)
        # Determine framework based on existing files (simplified logic, might need refinement)
        framework = "flutter" if (root / "pubspec.yaml").exists() else "rn"
        tests_ok, test_log = run_local_tests(root, framework, backend)
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
    try:
        import chromadb  # local import to avoid mandatory dependency if embeddings not used
    except ImportError:
        return []
    store = root / "embeddings"
    if not store.exists():
        return []
    try:
        client = chromadb.PersistentClient(str(store))
        col = client.get_collection("docs")
        return col.peek()["documents"]
    except Exception:
        return []
