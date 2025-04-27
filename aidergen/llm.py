"""OpenRouter chat + Aider orchestration."""

from __future__ import annotations
import json, os, time
from pathlib import Path
import httpx, subprocess
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

def run_aider_until_green(root: Path, backend: str):
    unmet = unmet_requirements(root)
    passes = 0
    while unmet and passes < 5:
        model = DEBUG_MODEL if passes else PLANNING_MODEL
        docs = _get_backend_docs(root, backend) if backend!="none" else []
        msg = json.dumps({"unmet":unmet, "docs":docs[:3]})
        run_cmd([
            "aider","--continue","--map-tokens","25000","--max-chat-history","20000",
            "--model",model,"--message",msg,"."
        ])
        unmet = unmet_requirements(root)
        passes += 1

def _get_backend_docs(root: Path, backend:str):
    store = root/"embeddings"
    if not store.exists(): return []
    client = chromadb.PersistentClient(str(store))
    col    = client.get_collection("docs")
    return col.peek()["documents"]
