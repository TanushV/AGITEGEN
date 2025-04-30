"""Runs the appropriate local test suite based on project framework."""

from __future__ import annotations
import subprocess
import shutil
import time
import os
import signal
from pathlib import Path
from rich.console import Console
from .utils import run_cmd # Now potentially useful for starting/stopping services
import json

console = Console()

# Helper function to check if Docker is running
def _is_docker_running() -> bool:
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, check=True, timeout=5)
        return "Docker Root Dir:" in result.stdout
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        console.print(f"[yellow]Docker check failed: {e}[/yellow]")
        return False

# Helper function to check if Firebase CLI is installed
def _is_firebase_cli_installed() -> bool:
    return shutil.which("firebase") is not None

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

def run_local_tests(root: Path, framework: str, backend: str) -> tuple[bool, str]:
    """
    Runs the local test suite (lint, unit, integration), including backend integration tests if configured.
    Returns (overall_success, combined_log)
    """
    console.print("[blue]Running local test suite...[/blue]")
    overall_success = True
    combined_log = ""
    
    supabase_container_name = "agitegen-local-supabase"
    firebase_emulator_process = None
    backend_service_started = False

    tests_to_run = []
    integration_tests_to_run = []

    if framework == "rn":
        # React Native / Expo tests (assuming npm)
        tests_to_run = [
            ["npm", "run", "lint"],
            ["npm", "test"],
            # We separate integration tests as they might depend on backend services
        ]
        # Check if package.json has a test:int script for backend tests
        pkg_json_path = root / "package.json"
        if pkg_json_path.exists():
            try:
                with open(pkg_json_path, "r") as f:
                    pkg_data = json.load(f)
                    if "test:int" in pkg_data.get("scripts", {}):
                        integration_tests_to_run.append(["npm", "run", "test:int"])
            except Exception as e:
                console.print(f"[yellow]Could not read package.json scripts: {e}[/yellow]")
    elif framework == "flutter":
        tests_to_run = [
            ["flutter", "analyze"], # Flutter's linting/analysis
            ["flutter", "test"], # Unit tests
        ]
        integration_tests_to_run = [
            ["flutter", "test", "integration_test"]
        ]
    else:
        console.print(f"[yellow]Warning: Unknown framework '{framework}', cannot run local tests.[/yellow]")
        return True, "Unknown framework" # Assume success if no tests to run

    try:
        # Start backend services if needed
        if backend == "supabase" and integration_tests_to_run:
            if _is_docker_running():
                console.print("[blue]Starting Supabase local service via Docker...")
                # Ensure any previous container is stopped and removed
                subprocess.run(["docker", "stop", supabase_container_name], capture_output=True, text=True)
                subprocess.run(["docker", "rm", supabase_container_name], capture_output=True, text=True)
                # Start new container (consider making ports configurable if needed)
                run_cmd([
                    "docker", "run", "-d", "--name", supabase_container_name,
                    "-p", "54321:54321", "-p", "54322:54322",
                    "-e", "SUPABASE_DB_PASSWORD=postgres", # Use a fixed default password for local dev
                    "-e", "SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0", # Default anon key
                    "-e", "SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU", # Default service role key
                    "supabase/supabase-edge:latest"
                ], check=True)
                console.print("[blue]Waiting for Supabase to start...")
                time.sleep(15) # Give Supabase time to initialize
                backend_service_started = True
            else:
                console.print("[yellow]Docker daemon not running. Skipping Supabase integration tests.")
                integration_tests_to_run = [] # Clear integration tests if service can't start
        elif backend == "firebase" and integration_tests_to_run:
            if _is_firebase_cli_installed():
                console.print("[blue]Starting Firebase emulators...")
                # Start emulators in the background
                # Consider using --import/--export flags if state persistence is needed locally
                cmd = ["firebase", "emulators:start", "--project", "demo", "--only", "auth,firestore"]
                # Use Popen for background process
                firebase_emulator_process = subprocess.Popen(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                console.print("[blue]Waiting for Firebase emulators to start...")
                time.sleep(10) # Give emulators time to initialize
                backend_service_started = True
            else:
                console.print("[yellow]Firebase CLI ('firebase') not found. Skipping Firebase integration tests.")
                integration_tests_to_run = [] # Clear integration tests if service can't start

        # Combine standard and integration tests
        all_tests = tests_to_run + integration_tests_to_run

        for cmd in all_tests:
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
                # Decide whether to stop on first failure or run all tests
                # console.print("[red]Stopping tests due to failure.")
                # break 

    finally:
        # Stop backend services if they were started
        if backend == "supabase" and backend_service_started:
            console.print("[blue]Stopping Supabase local service...")
            subprocess.run(["docker", "stop", supabase_container_name], capture_output=True, text=True)
            subprocess.run(["docker", "rm", supabase_container_name], capture_output=True, text=True)
        elif backend == "firebase" and firebase_emulator_process:
            console.print("[blue]Stopping Firebase emulators...")
            # Send SIGTERM to the process group to ensure child processes are killed
            try:
                os.killpg(os.getpgid(firebase_emulator_process.pid), signal.SIGTERM)
                firebase_emulator_process.wait(timeout=10) # Wait for graceful shutdown
            except ProcessLookupError:
                pass # Process already terminated
            except subprocess.TimeoutExpired:
                console.print("[yellow]Firebase emulator process did not terminate gracefully, killing.")
                os.killpg(os.getpgid(firebase_emulator_process.pid), signal.SIGKILL)
            except Exception as e:
                console.print(f"[yellow]Error stopping Firebase emulators: {e}")

    if overall_success:
        console.print("[green]All local tests passed.[/green]")
    else:
        console.print("[red]Some local tests failed.[/red]")
        
    return overall_success, combined_log.strip() 