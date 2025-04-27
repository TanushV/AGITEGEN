"""Runs the appropriate local test suite based on project framework."""

from __future__ import annotations
import subprocess
from pathlib import Path
from rich.console import Console
# from .utils import run_cmd # Not used here

console = Console()

def _run_test_command(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    """Runs a single test command, capturing output and success status."""
    console.print(f"Running: `{' '.join(cmd)}`...")
    try:
        # Use subprocess.run to capture output easily
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False, # Don't throw exception on failure
            timeout=300 # 5 minute timeout per command
        )
        log = f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        if result.returncode == 0:
            console.print(f"[green]Success:[/green] `{' '.join(cmd)}`")
            return True, log
        else:
            console.print(f"[red]Failed:[/red] `{' '.join(cmd)}` (exit code {result.returncode})")
            return False, log
    except subprocess.TimeoutExpired:
        console.print(f"[red]Timeout:[/red] `{' '.join(cmd)}`")
        return False, "Command timed out after 5 minutes."
    except Exception as e:
        console.print(f"[red]Error running `{' '.join(cmd)}`:[/red] {e}")
        return False, f"Error executing command: {e}"

def run_local_tests(root: Path, framework: str) -> tuple[bool, str]:
    """
    Runs the local test suite (lint, unit, integration).
    Returns (overall_success, combined_log)
    """
    console.print("[blue]Running local test suite...[/blue]")
    overall_success = True
    combined_log = ""
    
    tests_to_run = []
    if framework == "rn":
        # React Native / Expo tests (assuming npm)
        tests_to_run = [
            ["npm", "run", "lint"],
            ["npm", "test"],
            # Integration tests (Detox) might require specific setup/emulators,
            # making them hard to run reliably *locally* within this script.
            # Skipping Detox for now in local loop. Add back if feasible/desired.
            # ["npx", "detox", "test", "-c", "android.emu.release", "--headless"] 
        ]
    elif framework == "flutter":
        tests_to_run = [
            ["flutter", "analyze"], # Flutter's linting/analysis
            ["flutter", "test"], # Unit tests
            ["flutter", "test", "integration_test"]
        ]
    else:
        console.print(f"[yellow]Warning: Unknown framework '{framework}', cannot run local tests.[/yellow]")
        return True, "Unknown framework" # Assume success if no tests to run

    for cmd in tests_to_run:
        # Check if command likely exists (basic check)
        if cmd[0] == "npm" and not (root / "package.json").exists():
             console.print(f"[yellow]Skipping `{' '.join(cmd)}`: package.json not found.[/yellow]")
             continue
        if cmd[0] == "flutter" and not (root / "pubspec.yaml").exists():
             console.print(f"[yellow]Skipping `{' '.join(cmd)}`: pubspec.yaml not found.[/yellow]")
             continue
            
        success, log = _run_test_command(cmd, root)
        combined_log += f"\n\n=== Log for: `{' '.join(cmd)}` ===\n{log}"
        if not success:
            overall_success = False
            # Maybe stop after first failure? Or run all? Running all provides more info.
            # console.print("[red]Stopping tests due to failure.[/red]")
            # break 

    if overall_success:
        console.print("[green]All local tests passed.[/green]")
    else:
        console.print("[red]Some local tests failed.[/red]")
        
    return overall_success, combined_log.strip() 