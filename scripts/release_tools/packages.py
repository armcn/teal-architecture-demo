"""Read package dependencies, reuse immutable archives, and run R checks."""

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

from .files import file_digest, read_json, run_command


def build_package_cohort(
    root, repository, check_directory, library, environment, published_packages
):
    """Build in dependency order so each check sees its internal dependencies."""
    records = []
    for source, fields in packages_in_dependency_order(root):
        archive, record = prepare_package_archive(
            source, fields, repository, environment, published_packages
        )
        install_package(archive, library, environment)
        check_package(
            archive,
            fields["Package"],
            check_directory,
            root / ".work/logs",
            environment,
        )
        records.append(record)
    return records


def packages_in_dependency_order(root):
    packages = discover_packages(root)
    dependencies = {
        name: internal_dependencies(fields, packages.keys())
        for name, (_, fields) in packages.items()
    }
    order = dependency_order(dependencies)
    return [packages[name] for name in order]


def discover_packages(root):
    packages = {}
    for directory in sorted((Path(root) / "packages").iterdir()):
        if not directory.is_dir():
            continue
        fields = parse_description((directory / "DESCRIPTION").read_text())
        name = fields["Package"]
        if name in packages or name != directory.name:
            raise ValueError("Package names must be unique and match directory names")
        packages[name] = (directory, fields)
    return packages


def parse_description(text):
    """Parse the fields and continuation lines used in R DESCRIPTION files."""
    fields = {}
    current_field = None
    for line in text.splitlines():
        if line[:1].isspace() and current_field:
            fields[current_field] += " " + line.strip()
        elif ":" in line:
            current_field, value = line.split(":", 1)
            fields[current_field] = value.strip()
    return fields


def internal_dependencies(fields, package_names):
    dependency_fields = ("Imports", "Depends", "LinkingTo")
    entries = ",".join(fields.get(field, "") for field in dependency_fields)
    names = {re.split(r"\s|\(", entry.strip())[0] for entry in entries.split(",")}
    return names.intersection(package_names)


def dependency_order(dependencies):
    """Pure, deterministic topological sort; reject dependency cycles."""
    ordered = []
    while len(ordered) < len(dependencies):
        ready = sorted(
            name
            for name, required in dependencies.items()
            if name not in ordered and required <= set(ordered)
        )
        if not ready:
            raise ValueError("Internal package dependency cycle")
        ordered.extend(ready)
    return ordered


def package_source_digest(directory):
    fingerprint = hashlib.sha256()
    for path in sorted(Path(directory).rglob("*")):
        if path.is_symlink():
            raise ValueError("Package sources may not contain symlinks")
        if path.is_file():
            fingerprint.update(str(path.relative_to(directory)).encode() + b"\0")
            fingerprint.update(path.read_bytes() + b"\0")
    return fingerprint.hexdigest()


def read_published_packages(site):
    """Index prior name/version identities and verify their retained bytes."""
    packages = {}
    if not site:
        return packages
    manifests = (Path(site) / "snapshots").glob("*/release.json")
    for manifest_path in sorted(manifests):
        for record in read_json(manifest_path)["packages"]:
            identity = (record["name"], record["version"])
            archive = manifest_path.parent / record["file"]
            if file_digest(archive) != record["sha256"]:
                raise ValueError(f"Existing package checksum mismatch: {archive}")
            previous = packages.get(identity)
            if previous and previous[0]["sha256"] != record["sha256"]:
                raise ValueError(f"Conflicting published package identity: {identity}")
            packages[identity] = (record, archive)
    return packages


def prepare_package_archive(source, fields, repository, environment, published):
    name, version = fields["Package"], fields["Version"]
    if not re.fullmatch(r"[0-9]+(?:[.-][0-9]+)+", version):
        raise ValueError(f"Invalid R package version: {version}")
    source_digest = package_source_digest(source)
    archive = repository / f"{name}_{version}.tar.gz"
    previous = published.get((name, version))
    if previous:
        previous_record, previous_archive = previous
        if previous_record["source_sha256"] != source_digest:
            raise ValueError(f"{name} {version} changed: bump its DESCRIPTION Version")
        shutil.copyfile(previous_archive, archive)
    else:
        run_command(
            ["R", "CMD", "build", "--no-build-vignettes", "--no-manual", source],
            cwd=repository,
            env=environment,
        )
    record = {
        "name": name,
        "version": version,
        "source_sha256": source_digest,
        "file": "src/contrib/" + archive.name,
        "sha256": file_digest(archive),
    }
    return archive, record


def install_package(archive, library, environment):
    run_command(
        ["R", "CMD", "INSTALL", "--library=" + str(library), archive],
        env=environment,
    )


def check_package(archive, name, check_directory, log_directory, environment):
    result = subprocess.run(
        ["R", "CMD", "check", "--no-manual", "--no-build-vignettes", str(archive)],
        cwd=check_directory,
        env=environment,
    )
    report_directory = check_directory / f"{name}.Rcheck"
    report = (report_directory / "00check.log").read_text()
    log_directory.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        report_directory,
        log_directory / report_directory.name,
        dirs_exist_ok=True,
    )
    if result.returncode or re.search(r"\b(?:ERROR|WARNING)\b", report):
        raise ValueError(f"R CMD check failed for {name}: {report}")
