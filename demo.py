"""Developer commands: check the source, run locally, or fetch a pinned release."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from scripts.release_tools.files import read_json, validate_snapshot_id

ROOT = Path(__file__).resolve().parent
APP_FILES = ("app.R", "renv.lock", "release.json", "restore.R", "bootstrap.R")
LOCAL_RELEASE_POINTER = ROOT / ".work/latest-local.txt"


def main():
    arguments = parse_arguments()
    os.chdir(ROOT)
    os.environ.setdefault("RENV_PATHS_ROOT", str(ROOT / ".work/renv-state"))
    if arguments.command == "check":
        check_local_source()
    elif arguments.command == "run":
        run_local_builder()
    else:
        fetch_published_app(arguments.snapshot, arguments.channel, arguments.out)


def check_local_source():
    run_command("Rscript", "--vanilla", "scripts/restore-dependencies.R")
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    snapshot = "local-" + str(time.time_ns())
    output = ROOT / "dist" / snapshot
    run_command(
        sys.executable,
        "scripts/release.py",
        "build",
        "--out",
        str(output),
        "--snapshot",
        snapshot,
        "--source-sha",
        source_sha,
    )
    run_command(sys.executable, "scripts/release.py", "verify", str(output))
    LOCAL_RELEASE_POINTER.write_text(str(output))
    print("Checks passed. Run: python3 demo.py run")


def run_local_builder():
    if not LOCAL_RELEASE_POINTER.exists():
        raise ValueError("First run: python3 demo.py check")
    app = Path(LOCAL_RELEASE_POINTER.read_text().strip()) / "app"
    environment = {
        **os.environ,
        "R_LIBS_USER": str(ROOT / ".work/dependencies"),
        "R_LIBS_SITE": "",
    }
    print("Local development app. Publish through CI before sharing an exported app.")
    run_command(
        "Rscript",
        "--vanilla",
        "-e",
        "shiny::runApp('.', host='127.0.0.1', port=3838, launch.browser=FALSE)",
        cwd=app,
        env=environment,
    )


def fetch_published_app(snapshot, channel, output):
    base_url = read_json(ROOT / "config.json")["depository_url"]
    selected_snapshot = resolve_snapshot(base_url, snapshot, channel)
    snapshot_url = f"{base_url}/snapshots/{selected_snapshot}"
    manifest = download_json(snapshot_url + "/release.json")
    validate_download_identity(manifest, selected_snapshot, snapshot_url)
    destination = Path(output).resolve()
    download_app_atomically(snapshot_url, manifest, destination)
    print(f"Downloaded and verified snapshot {selected_snapshot} to {destination}")
    print("From that directory, run Rscript restore.R")
    print("Then run: Rscript -e 'shiny::runApp()'")


def resolve_snapshot(base_url, snapshot, channel):
    # Resolve a moving channel once. All subsequent reads use the immutable ID.
    if snapshot is None:
        pointer = download_json(f"{base_url}/channels/{channel}.json")
        snapshot = pointer["snapshot"]
    return validate_snapshot_id(snapshot)


def validate_download_identity(manifest, snapshot, snapshot_url):
    if manifest["snapshot"] != snapshot or manifest["repository_url"] != snapshot_url:
        raise ValueError("Release identity disagrees with selected snapshot")


def download_app_atomically(snapshot_url, manifest, destination):
    if destination.exists():
        raise ValueError("Destination exists; choose a new --out directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        staging = Path(temporary) / "app"
        staging.mkdir()
        for name in APP_FILES:
            relative_path = "app/" + name
            content = download_bytes(snapshot_url + "/" + relative_path)
            if hashlib.sha256(content).hexdigest() != manifest["files"][relative_path]:
                raise ValueError("Checksum mismatch: " + name)
            (staging / name).write_bytes(content)
        staging.rename(destination)


def download_json(url):
    return json.loads(download_bytes(url))


def download_bytes(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def run_command(*arguments, **options):
    subprocess.run(list(arguments), check=True, **options)


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "run", "fetch"])
    parser.add_argument("--snapshot", help="Immutable snapshot ID to fetch")
    parser.add_argument(
        "--channel",
        choices=["dev", "prod"],
        default="dev",
        help="Select once, then pin that snapshot",
    )
    parser.add_argument(
        "--out", default="downloaded-app", help="New destination directory for fetch"
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
