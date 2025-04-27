from __future__ import annotations
import os, subprocess, sys, json
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from .utils import ensure_env, is_mac
from .quota import ensure_openrouter_quota, ensure_github_minutes, measure_session_cost
from .scaffolder import scaffold_project, install_backend_deps
from .llm import collect_requirements, run_aider_until_green
from .unmet import unmet_requirements
from .runner import run_local
from .ios import dispatch_ios_if_needed

console = Console()

ASCII_BOX_ART = r"""[bold blue]
 ░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓████████▓▒░▒▓██████▓▒░░▒▓████████▓▒░▒▓███████▓▒░  
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░     ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓████████▓▒░▒▓█▓▒▒▓███▓▒░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓██████▓▒░░▒▓█▓▒▒▓███▓▒░▒▓██████▓▒░ ░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓████████▓▒░▒▓██████▓▒░░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░
[/bold blue]"""

console.print(ASCII_BOX_ART)

app = typer.Typer(add_completion=False)

@app.command()
def init(
    name: str = typer.Argument(...),
    framework: str = typer.Option("rn","--framework","-f"),
    targets: str = typer.Option("web,android","--targets","-t"),
    backend: str = typer.Option("none","--backend","-b"),
):
    ensure_env("OPENROUTER_API_KEY")
    ensure_openrouter_quota(); ensure_github_minutes()
    proj = Path(name).absolute(); proj.mkdir(exist_ok=True)
    tlst = [t.strip() for t in targets.split(",") if t.strip()]
    scaffold_project(proj, framework, tlst, backend)
    install_backend_deps(proj, backend)
    reqs = collect_requirements()
    (proj/"requirements.md").write_text(json.dumps({"requirements":reqs}, indent=2))
    console.print(Panel("[green]Scaffold complete! Next steps:\n  1. cd into your project: `cd "+name+"`\n  2. Run the build process: `aidergen build`", 
                      title="Initialization Successful", 
                      border_style="dim blue"))

@app.command()
def build():
    root = Path.cwd()
    package = json.loads((root/"requirements.md").read_text())
    backend = "supabase" if (root/"src/supabaseClient.ts").exists() else "firebase" if (root/"src/firebaseClient.ts").exists() else "none"
    with measure_session_cost():
        run_aider_until_green(root, backend)
    dispatch_ios_if_needed(
        subprocess.check_output(["gh","repo","view","--json","nameWithOwner"], text=True).split('"')[-2],
        subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
    )

@app.command()
def run(): run_local()

if __name__ == "__main__":
    app()
