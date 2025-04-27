from __future__ import annotations
from pathlib import Path
from jinja2 import Template
from .utils import run_cmd, console
from .embed import embed_backend

RN_CMD      = ["npx","create-expo-app"]
FLUTTER_CMD = ["flutter","create"]
NEXT_CMD    = ["npx","create-next-app@latest"]

def scaffold_project(root: Path, framework:str, targets:list[str], backend:str):
    if framework=="rn":
        run_cmd(RN_CMD+[root.name], cwd=root.parent)
    elif framework=="flutter-web":
        run_cmd(FLUTTER_CMD+["--platform","web",root.name], cwd=root.parent)
    elif framework=="flutter-desktop":
        run_cmd(FLUTTER_CMD+["--platform","macos,windows,linux",root.name], cwd=root.parent)
    elif framework=="next":
        run_cmd(NEXT_CMD+[root.name,"--eslint"], cwd=root.parent)
    else:
        console.print("[red]Unknown framework"); return
    if backend!="none":
        (root/"src").mkdir(exist_ok=True)
        stub = Template("""// {{b}} stub\export async function fetchUser() {/* TODO-{{b.upper()}} */ return {id:1}}""").render(b=backend)
        (root/"src"/f"{backend}Client.ts").write_text(stub)
        embed_backend(backend, ["auth","user","database"], root)

def install_backend_deps(root: Path, backend:str):
    if backend=="supabase": run_cmd("npm i @supabase/supabase-js", cwd=root)
    if backend=="firebase": run_cmd("npm i firebase", cwd=root)
