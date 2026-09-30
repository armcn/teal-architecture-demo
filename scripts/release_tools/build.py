"""Prepare a complete release in temporary storage, then publish it locally."""

import copy
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .files import (
    file_digest,
    isolated_r_environment,
    read_json,
    run_command,
    validate_snapshot_id,
    write_json,
)
from .packages import build_package_cohort, read_published_packages

ROOT = Path(__file__).resolve().parents[2]


def build_snapshot(output, snapshot, base_url, source_sha, existing_site=None):
    """Validate inputs, check packages, save the app, and commit the directory."""
    output = Path(output).resolve()
    validate_build_request(output, snapshot, base_url, source_sha)
    config = read_json(ROOT / "config.json")
    external_lock = read_json(ROOT / "renv.lock")
    library = ROOT / ".work/dependencies"
    environment = isolated_r_environment(library)
    validate_build_runtime(config, external_lock, library, environment)
    published = read_published_packages(existing_site)
    repository_url = base_url.rstrip("/") + "/snapshots/" + snapshot

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-", dir=output.parent) as work:
        staging, repository, checks = create_build_directories(Path(work))
        packages = build_package_cohort(
            ROOT, repository, checks, library, environment, published
        )
        write_repository_index(repository, environment)
        metadata = release_metadata(
            config, snapshot, source_sha, repository_url, packages
        )
        app_lock = release_lockfile(external_lock, packages, repository_url)
        save_release_app(staging, app_lock, metadata)
        write_snapshot_manifest(staging, metadata)
        staging.rename(output)
    print(f"Created {output}")


def validate_build_request(output, snapshot, base_url, source_sha):
    validate_snapshot_id(snapshot)
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("A full source commit SHA is required")
    if not base_url.startswith("https://"):
        raise ValueError("Published repository URL must use HTTPS")
    if output.exists():
        raise ValueError("Output already exists; snapshots are never overwritten")


def validate_build_runtime(config, lock, library, environment):
    required_r = config["r_version"]
    if lock["R"]["Version"] != required_r:
        raise ValueError("R version disagrees between config and dependency lock")
    if not library.is_dir():
        raise ValueError("Run Rscript scripts/restore-dependencies.R first")
    installed_r = subprocess.check_output(
        ["Rscript", "--vanilla", "-e", "cat(as.character(getRversion()))"],
        env=environment,
        text=True,
    ).strip()
    if installed_r != required_r:
        raise ValueError(f"Use R {required_r}; this process uses R {installed_r}")


def create_build_directories(work):
    staging = work / "snapshot"
    repository = staging / "src/contrib"
    checks = work / "check"
    repository.mkdir(parents=True)
    checks.mkdir()
    return staging, repository, checks


def write_repository_index(repository, environment):
    run_command(
        ["Rscript", "--vanilla", ROOT / "scripts/repository-index.R", repository],
        env=environment,
    )


def release_metadata(config, snapshot, source_sha, repository_url, packages):
    return {
        "schema": 1,
        "snapshot": snapshot,
        "source_commit": source_sha,
        "source_repository": config["source_repository"],
        "r_version": config["r_version"],
        "repository_url": repository_url,
        "packages": packages,
    }


def release_lockfile(external_lock, packages, repository_url):
    """Return a release lock without changing the source dependency lock."""
    lock = copy.deepcopy(external_lock)
    for package in packages:
        name = package["name"]
        lock["Packages"][name] = {
            "Package": name,
            "Version": package["version"],
            "Source": "Repository",
            "Repository": "TBDEMO",
        }
    external_repositories = [
        repository
        for repository in lock["R"]["Repositories"]
        if repository["Name"] != "TBDEMO"
    ]
    lock["R"]["Repositories"] = [
        *external_repositories,
        {"Name": "TBDEMO", "URL": repository_url},
    ]
    return lock


def save_release_app(staging, lock, metadata):
    app = staging / "app"
    app.mkdir()
    source_files = {
        "app/app.R": "app.R",
        "scripts/bootstrap.R": "bootstrap.R",
        "scripts/restore-app.R": "restore.R",
    }
    for source, destination in source_files.items():
        shutil.copyfile(ROOT / source, app / destination)
    write_json(app / "renv.lock", lock)
    write_json(app / "release.json", metadata)
    shutil.copyfile(ROOT / "scripts/smoke.R", staging / "smoke.R")


def write_snapshot_manifest(staging, metadata):
    files = {
        str(path.relative_to(staging)): file_digest(path)
        for path in sorted(staging.rglob("*"))
        if path.is_file()
    }
    write_json(staging / "release.json", {**metadata, "files": files})
