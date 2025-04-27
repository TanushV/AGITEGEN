"""Sync agitegen.__version__ with latest git tag ('vX.Y.Z')."""

from pathlib import Path
import re, subprocess, sys

tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], text=True).strip()
if not tag.startswith("v"):
    sys.exit("❌  Latest tag must start with 'v'")
ver = tag.lstrip("v")

init = Path("agitegen/__init__.py")
init.write_text(re.sub(r'__version__ = ".*"', f'__version__ = "{ver}"', init.read_text()))
print("Version bumped to", ver)
