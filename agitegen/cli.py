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
):
    ensure_env("OPENROUTER_API_KEY")
    ensure_openrouter_quota(); ensure_github_minutes()
    proj = Path(name).absolute(); proj.mkdir(exist_ok=True)

    # --- Interactive Prompts ---

    # Framework Selection
    framework_choices = {"rn": "React Native"} # Add more frameworks here if needed
    console.print("[bold blue]Select a framework:[/bold blue]")
    for key, desc in framework_choices.items():
        console.print(f"  - {key}: {desc}")
    while True:
        framework_input = console.input("Enter framework abbreviation (default: rn): ") or "rn"
        if framework_input in framework_choices:
            framework = framework_input
            break
        else:
            console.print("[red]Invalid framework selection. Please choose from the list.[/red]")

    # Target Selection (Dependent on Framework)
    available_targets = []
    if framework == "rn":
        available_targets = ["web", "android", "ios"]
    # Add target logic for other frameworks here
    # else:
    #     available_targets = ["web"] # Example default

    console.print("[bold blue]Select target platforms (comma-separated):[/bold blue]")
    for target in available_targets:
        console.print(f"  - {target}")

    default_targets_str = ",".join(t for t in ["web", "android"] if t in available_targets)
    while True:
        targets_input = console.input(f"Enter targets (default: {default_targets_str}): ") or default_targets_str
        targets_list = [t.strip().lower() for t in targets_input.split(",") if t.strip()]
        if all(t in available_targets for t in targets_list):
            tlst = targets_list
            break
        else:
            console.print(f"[red]Invalid target(s). Please choose from: {', '.join(available_targets)}[/red]")


    # Backend Selection
    backend_choices = ["none", "supabase", "firebase"]
    console.print("[bold blue]Select a backend provider:[/bold blue]")
    for backend_option in backend_choices:
        console.print(f"  - {backend_option}")
    while True:
        backend_input = console.input("Enter backend (default: none): ") or "none"
        if backend_input in backend_choices:
            backend = backend_input
            break
        else:
            console.print("[red]Invalid backend selection. Please choose from the list.[/red]")

    # --- End Interactive Prompts ---

    scaffold_project(proj, framework, tlst, backend)
    install_backend_deps(proj, backend)
    reqs = collect_requirements()
    (proj/"requirements.md").write_text(json.dumps({"requirements":reqs}, indent=2))
    console.print(Panel("[green]Scaffold complete! Next steps:\n  1. cd into your project: `cd "+name+"`\n  2. Run the build process: `agitegen build`", 
                      title="Initialization Successful", 
                      border_style="dim blue"))

@app.command()
def build():
    root = Path.cwd()
    try:
        json.loads((root/"requirements.md").read_text())
    except Exception:
        # requirements.md may now contain markdown blocks; ignore parse errors.
        pass
    # Detect backend preference – first check env override, else infer from files
    env_backend = os.getenv("AIDERGEN_BACKEND")
    backend = env_backend if env_backend else (
        "supabase" if (root/"src/backend/supabaseAdapter.ts").exists() else
        "firebase" if (root/"src/backend/firebaseAdapter.ts").exists() else
        "none"
    )
    with measure_session_cost():
        run_aider_until_green(root, backend)
    dispatch_ios_if_needed(
        subprocess.check_output(["gh","repo","view","--json","nameWithOwner"], text=True).split('"')[-2],
        subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
    )

@app.command()
def run(): run_local()

@app.command()
def add_backend(
    backend: str = typer.Argument(..., help="Backend to add: supabase|firebase"),
):
    """Installs SDK, generates adapter + docs embedding, and updates requirements.md."""
    root = Path.cwd()
    if backend not in {"supabase", "firebase"}:
        console.print("[red]Invalid backend. Choose 'supabase' or 'firebase'.")
        raise typer.Exit(code=1)

    # Re-use scaffolder logic – generate only backend bits
    console.print(f"[blue]Scaffolding {backend} backend adapters...[/blue]")
    from .scaffolder import scaffold_project, install_backend_deps
    scaffold_project(root, framework="", targets=[], backend=backend)  # no-op for project creation but adds backend
    install_backend_deps(root, backend)

    # Append note to requirements.md for Aider context
    req_file = root / "requirements.md"
    note = f"\n\n<!-- AIDERGEN_BACKEND_NOTE -->\n- Added backend adapter for **{backend}**. Ensure CRUD + auth paths are implemented and tested."
    if req_file.exists():
        content = req_file.read_text()
        if "<!-- AIDERGEN_BACKEND_NOTE -->" not in content:
            req_file.write_text(content + note)
    else:
        req_file.write_text(note.strip())
    console.print(f"[green]{backend.capitalize()} backend successfully integrated. Run `agitegen build` next.")

if __name__ == "__main__":
    app()
