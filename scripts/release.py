"""Build and validate immutable R release directories. Python standard library only."""
import argparse
import contextlib
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    print("+", " ".join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_id(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", value):
        raise ValueError("Snapshot ID must contain only lowercase letters, numbers and hyphens")
    return value


def source_hash(directory):
    result = hashlib.sha256()
    for file in sorted(Path(directory).rglob("*")):
        if file.is_symlink():
            raise ValueError("Package sources may not contain symlinks")
        if file.is_file():
            result.update(str(file.relative_to(directory)).encode() + b"\0")
            result.update(file.read_bytes() + b"\0")
    return result.hexdigest()


def description(path):
    fields = {}
    key = None
    for line in Path(path).read_text().splitlines():
        if line[:1].isspace() and key:
            fields[key] += " " + line.strip()
        elif ":" in line:
            key, value = line.split(":", 1)
            fields[key] = value.strip()
    return fields


def package_order(root):
    packages = {}
    for path in sorted((Path(root) / "packages").iterdir()):
        if path.is_dir():
            fields = description(path / "DESCRIPTION")
            name = fields["Package"]
            if name in packages or name != path.name:
                raise ValueError("Package names must be unique and match directory names")
            packages[name] = (path, fields)
    dependencies = {}
    for name, (_, fields) in packages.items():
        deps = ",".join(fields.get(key, "") for key in ("Imports", "Depends", "LinkingTo"))
        dependencies[name] = {re.split(r"\s|\(", d.strip())[0] for d in deps.split(",")} & packages.keys()
    ordered = []
    while len(ordered) < len(packages):
        ready = sorted(n for n in packages if n not in ordered and dependencies[n] <= set(ordered))
        if not ready:
            raise ValueError("Internal package dependency cycle")
        ordered.extend(ready)
    return [packages[name] for name in ordered]


def prior_packages(site):
    result = {}
    if not site:
        return result
    for manifest_path in sorted((Path(site) / "snapshots").glob("*/release.json")):
        manifest = read_json(manifest_path)
        for package in manifest["packages"]:
            key = (package["name"], package["version"])
            path = manifest_path.parent / package["file"]
            if sha256(path) != package["sha256"]:
                raise ValueError(f"Existing package checksum mismatch: {path}")
            if key in result and result[key][0]["sha256"] != package["sha256"]:
                raise ValueError(f"Conflicting published package identity: {key}")
            result[key] = (package, path)
    return result


def isolated_env(library):
    env = os.environ.copy()
    env.update(R_LIBS_USER=str(library), R_LIBS_SITE="", RENV_CONFIG_AUTOLOADER_ENABLED="FALSE",
               RENV_CONFIG_CACHE_ENABLED="FALSE", RENV_CONFIG_PAK_ENABLED="FALSE",
               RENV_CONFIG_REPOS_OVERRIDE="", R_ENVIRON_USER="", R_PROFILE_USER="",
               _R_CHECK_FORCE_SUGGESTS_="false", NOT_CRAN="true")
    return env


def build(output, snapshot, base_url, source_sha, existing_site=None):
    validate_id(snapshot)
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("A full source commit SHA is required")
    if not base_url.startswith("https://"):
        raise ValueError("Published repository URL must use HTTPS")
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Output already exists; snapshots are never overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    config = read_json(ROOT / "config.json")
    lock = read_json(ROOT / "renv.lock")
    if lock["R"]["Version"] != config["r_version"]:
        raise ValueError("R version disagrees between config and dependency lock")
    dependencies = ROOT / ".work" / "dependencies"
    if not dependencies.is_dir():
        raise ValueError("Run Rscript scripts/restore-dependencies.R first")
    env = isolated_env(dependencies)
    actual_r = subprocess.check_output(["Rscript", "--vanilla", "-e", "cat(as.character(getRversion()))"],
                                       env=env, text=True).strip()
    if actual_r != config["r_version"]:
        raise ValueError(f"Use R {config['r_version']}; this process uses R {actual_r}")
    existing = prior_packages(existing_site)
    repository_url = base_url.rstrip("/") + "/snapshots/" + snapshot
    with tempfile.TemporaryDirectory(prefix="release-", dir=output.parent) as temporary:
        staging = Path(temporary) / "snapshot"
        contrib = staging / "src" / "contrib"
        contrib.mkdir(parents=True)
        work = Path(temporary) / "check"
        work.mkdir()
        packages = []
        for package, fields in package_order(ROOT):
            name, version = fields["Package"], fields["Version"]
            if not re.fullmatch(r"[0-9]+(?:[.-][0-9]+)+", version):
                raise ValueError(f"Invalid R package version: {version}")
            fingerprint = source_hash(package)
            filename = f"{name}_{version}.tar.gz"
            previous = existing.get((name, version))
            if previous:
                if previous[0]["source_sha256"] != fingerprint:
                    raise ValueError(f"{name} {version} changed: bump its DESCRIPTION Version")
                shutil.copyfile(previous[1], contrib / filename)
            else:
                run(["R", "CMD", "build", "--no-build-vignettes", "--no-manual", package], cwd=contrib, env=env)
            run(["R", "CMD", "INSTALL", "--library=" + str(dependencies), contrib / filename], env=env)
            check = subprocess.run(["R", "CMD", "check", "--no-manual", "--no-build-vignettes", str(contrib / filename)], cwd=work, env=env)
            check_log = (work / f"{name}.Rcheck" / "00check.log").read_text()
            logs = ROOT / ".work" / "logs"
            logs.mkdir(parents=True, exist_ok=True)
            shutil.copytree(work / f"{name}.Rcheck", logs / f"{name}.Rcheck", dirs_exist_ok=True)
            if check.returncode or re.search(r"\b(?:ERROR|WARNING)\b", check_log):
                raise ValueError(f"R CMD check failed for {name}: {check_log}")
            packages.append(dict(name=name, version=version, source_sha256=fingerprint,
                                 file="src/contrib/" + filename, sha256=sha256(contrib / filename)))
            lock["Packages"][name] = dict(Package=name, Version=version, Source="Repository", Repository="TBDEMO")
        run(["Rscript", "--vanilla", ROOT / "scripts/repository-index.R", contrib], env=env)
        app = staging / "app"
        app.mkdir()
        shutil.copyfile(ROOT / "app/app.R", app / "app.R")
        shutil.copyfile(ROOT / "scripts/bootstrap.R", app / "bootstrap.R")
        shutil.copyfile(ROOT / "scripts/restore-app.R", app / "restore.R")
        lock["R"]["Repositories"] = [r for r in lock["R"]["Repositories"] if r["Name"] != "TBDEMO"]
        lock["R"]["Repositories"].append(dict(Name="TBDEMO", URL=repository_url))
        write_json(app / "renv.lock", lock)
        metadata = dict(schema=1, snapshot=snapshot, source_commit=source_sha,
                        source_repository=config["source_repository"], r_version=config["r_version"],
                        repository_url=repository_url, packages=packages)
        write_json(app / "release.json", metadata)
        shutil.copyfile(ROOT / "scripts/smoke.R", staging / "smoke.R")
        metadata["files"] = {str(p.relative_to(staging)): sha256(p)
                             for p in sorted(staging.rglob("*")) if p.is_file()}
        write_json(staging / "release.json", metadata)
        staging.rename(output)
    print(f"Created {output}")


@contextlib.contextmanager
def serve(directory):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


def verify_restore(snapshot_path, online=False):
    snapshot_path = Path(snapshot_path).resolve()
    with tempfile.TemporaryDirectory(prefix="restore-") as temporary:
        project = Path(temporary)
        # Exercise the exact files developers download, including restore.R and
        # a new R process loading the generated .Rprofile. A separate helper
        # restore can accidentally hide bugs in the delivered restoration path.
        shutil.copytree(snapshot_path / "app", project, dirs_exist_ok=True)
        empty_user_library = project / "empty-user-library"
        empty_user_library.mkdir()
        lock = read_json(project / "renv.lock")
        with serve(snapshot_path) as local_url:
            if not online:
                # Only the transport URL changes for an unpublished candidate.
                for repo in lock["R"]["Repositories"]:
                    if repo["Name"] == "TBDEMO":
                        repo["URL"] = local_url
            write_json(project / "renv.lock", lock)
            env = isolated_env(empty_user_library)
            env["RENV_PATHS_ROOT"] = str(project / "renv-state")
            run(["Rscript", "--vanilla", "restore.R"], cwd=project, env=env)
            libraries = [p.parent.parent for p in (project / "renv/library").rglob("tb.builder/DESCRIPTION")]
            if len(libraries) != 1:
                raise ValueError("restore.R did not install the app into its project library")
            env["RENV_CONFIG_AUTOLOADER_ENABLED"] = "TRUE"
            env["R_PROFILE_USER"] = str(project / ".Rprofile")
            run(["Rscript", ROOT / "scripts/smoke.R", libraries[0], project, "active"],
                cwd=project, env=env)
    print("PASS: cold restore and app smoke tests")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    builder = commands.add_parser("build")
    builder.add_argument("--out", required=True)
    builder.add_argument("--snapshot", required=True)
    builder.add_argument("--base-url", default=read_json(ROOT / "config.json")["depository_url"])
    builder.add_argument("--source-sha", required=True)
    builder.add_argument("--existing-site")
    restore = commands.add_parser("verify")
    restore.add_argument("snapshot")
    restore.add_argument("--online", action="store_true")
    args = parser.parse_args()
    if args.command == "build":
        build(args.out, args.snapshot, args.base_url, args.source_sha, args.existing_site)
    else:
        verify_restore(args.snapshot, args.online)


if __name__ == "__main__":
    main()
