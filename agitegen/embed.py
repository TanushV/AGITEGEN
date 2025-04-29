"""Download backend docs & embed only relevant chunks with Chroma."""

from __future__ import annotations
import hashlib, httpx, os, re
from pathlib import Path

_chromadb = None

def _get_chromadb():
    global _chromadb
    if _chromadb is None:
        import importlib
        _chromadb = importlib.import_module("chromadb")
    return _chromadb

DOC_URLS = {
    "supabase": "https://raw.githubusercontent.com/supabase/docs/main/clients/js/README.md",
    "firebase": "https://raw.githubusercontent.com/firebase/docs/main/docs/web/setup.md",
}

def embed_backend(backend: str, keywords: list[str], root: Path):
    text = httpx.get(DOC_URLS[backend]).text
    chunks = re.split(r"\n##+\s", text)     # cheap segmenter
    store_dir = root / "embeddings"
    store_dir.mkdir(exist_ok=True)
    chromadb = _get_chromadb()
    client = chromadb.PersistentClient(str(store_dir))
    col = client.get_or_create_collection("docs")
    for chunk in chunks:
        if any(k.lower() in chunk.lower() for k in keywords):
            h = hashlib.sha1(chunk.encode()).hexdigest()
            if not col.get(ids=[h])["ids"]:
                col.add(ids=[h], documents=[chunk])
