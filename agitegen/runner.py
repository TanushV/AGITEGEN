import subprocess, platform, shutil, os

def _spawn(cmd): subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def run_local():
    if shutil.which("npm"): _spawn(["npm","run","dev"])
    if shutil.which("expo"): _spawn(["npx","expo","run:android"])
    if platform.system()=="Darwin" and shutil.which("expo"):
        _spawn(["npx","expo","run:ios"])
    if shutil.which("flutter"):
        _spawn(["flutter","run","-d","chrome"])
    if platform.system()=="Darwin" and shutil.which("flutter"):
        _spawn(["flutter","run","-d","ios"])
