"""Friendly local entry point: python3 demo.py check | run | fetch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import re
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
os.environ.setdefault("RENV_PATHS_ROOT", str(ROOT / ".work/renv-state"))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=["check", "run", "fetch"])
parser.add_argument("--snapshot", help="Immutable snapshot ID to fetch")
parser.add_argument("--channel", choices=["dev", "prod"], default="dev", help="Select once, then pin that snapshot")
parser.add_argument("--out", default="downloaded-app", help="New destination directory for fetch")
args = parser.parse_args()
pointer = ROOT / ".work/latest-local.txt"
if args.command == "check":
    subprocess.run(["Rscript", "--vanilla", "scripts/restore-dependencies.R"], check=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    snapshot = "local-" + str(time.time_ns())
    output = ROOT / "dist" / snapshot
    subprocess.run([sys.executable, "scripts/release.py", "build", "--out", str(output), "--snapshot", snapshot, "--source-sha", sha], check=True)
    subprocess.run([sys.executable, "scripts/release.py", "verify", str(output)], check=True)
    pointer.write_text(str(output))
    print("Checks passed. Run: python3 demo.py run")
elif args.command == "run":
    if not pointer.exists():
        parser.error("First run: python3 demo.py check")
    release = Path(pointer.read_text().strip()) / "app"
    env = os.environ.copy()
    env["R_LIBS_USER"] = str(ROOT / ".work/dependencies")
    env["R_LIBS_SITE"] = ""
    # This local working build is not distributed. Publish a candidate before sharing exports.
    print("Local development app. Publish through CI before sharing an exported app.")
    subprocess.run(["Rscript", "--vanilla", "-e", "shiny::runApp('.', host='127.0.0.1', port=3838, launch.browser=FALSE)"], cwd=release, env=env, check=True)
else:
    base = json.loads((ROOT / "config.json").read_text())["depository_url"]
    def download(url):
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read()
    snapshot = args.snapshot or json.loads(download(base + "/channels/" + args.channel + ".json"))["snapshot"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", snapshot):
        parser.error("Invalid snapshot identifier")
    url = base + "/snapshots/" + snapshot
    manifest = json.loads(download(url + "/release.json"))
    if manifest["snapshot"] != snapshot or manifest["repository_url"] != url:
        parser.error("Release identity disagrees with selected snapshot")
    destination = Path(args.out).resolve()
    if destination.exists():
        parser.error("Destination exists; choose a new --out directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        staging = Path(tmp) / "app"
        staging.mkdir()
        for name in ("app.R", "renv.lock", "release.json", "restore.R", "bootstrap.R"):
            key = "app/" + name
            content = download(url + "/" + key)
            if hashlib.sha256(content).hexdigest() != manifest["files"][key]:
                raise ValueError("Checksum mismatch: " + name)
            (staging / name).write_bytes(content)
        staging.rename(destination)
    print(f"Downloaded and verified snapshot {snapshot} to {destination}")
    print("From that directory, run Rscript restore.R, then Rscript -e 'shiny::runApp()'")
