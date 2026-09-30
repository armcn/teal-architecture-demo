"""Test the actual downloaded app in a fresh project and a fresh R process."""

import contextlib
import copy
import http.server
import shutil
import tempfile
import threading
from pathlib import Path

from .files import isolated_r_environment, read_json, run_command, write_json

ROOT = Path(__file__).resolve().parents[2]


def verify_restore(snapshot_path, online=False):
    """Restore delivered files, then verify activation in a separate R process."""
    snapshot_path = Path(snapshot_path).resolve()
    with tempfile.TemporaryDirectory(prefix="restore-") as temporary:
        project = Path(temporary)
        shutil.copytree(snapshot_path / "app", project, dirs_exist_ok=True)
        environment = prepare_test_environment(project)
        with serve_snapshot(snapshot_path) as local_url:
            if not online:
                point_lock_at_local_repository(project, local_url)
            restore_delivered_app(project, environment)
            verify_fresh_r_session(project, environment)
    print("PASS: cold restore and app smoke tests")


def prepare_test_environment(project):
    library = project / "empty-user-library"
    library.mkdir()
    return {
        **isolated_r_environment(library),
        "RENV_PATHS_ROOT": str(project / "renv-state"),
    }


def point_lock_at_local_repository(project, repository_url):
    # Before publication, only the transport URL changes. All versions stay fixed.
    lockfile = project / "renv.lock"
    lock = lock_with_repository_url(read_json(lockfile), repository_url)
    write_json(lockfile, lock)


def lock_with_repository_url(original_lock, repository_url):
    lock = copy.deepcopy(original_lock)
    for repository in lock["R"]["Repositories"]:
        if repository["Name"] == "TBDEMO":
            repository["URL"] = repository_url
    return lock


def restore_delivered_app(project, environment):
    # A different helper script could pass while the delivered restore.R fails.
    run_command(["Rscript", "--vanilla", "restore.R"], cwd=project, env=environment)


def verify_fresh_r_session(project, environment):
    library = find_restored_library(project)
    startup_environment = {
        **environment,
        "RENV_CONFIG_AUTOLOADER_ENABLED": "TRUE",
        "R_PROFILE_USER": str(project / ".Rprofile"),
    }
    run_command(
        ["Rscript", ROOT / "scripts/smoke.R", library, project, "active"],
        cwd=project,
        env=startup_environment,
    )


def find_restored_library(project):
    descriptions = (project / "renv/library").rglob("tb.builder/DESCRIPTION")
    libraries = [path.parent.parent for path in descriptions]
    if len(libraries) != 1:
        raise ValueError("restore.R did not install the app into its project library")
    return libraries[0]


@contextlib.contextmanager
def serve_snapshot(directory):
    """Serve one candidate on localhost; close the server even after a failure."""

    class SnapshotHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SnapshotHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
