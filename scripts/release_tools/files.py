"""Small file and process operations shared by release preparation and testing."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_snapshot_id(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", value):
        raise ValueError(
            "Snapshot ID must contain only lowercase letters, numbers and hyphens"
        )
    return value


def run_command(arguments, **options):
    command = [str(argument) for argument in arguments]
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, check=True, **options)


def isolated_r_environment(library):
    """Return a new environment; never modify the caller's process environment."""
    return {
        **os.environ,
        "R_LIBS_USER": str(library),
        "R_LIBS_SITE": "",
        "RENV_CONFIG_AUTOLOADER_ENABLED": "FALSE",
        "RENV_CONFIG_CACHE_ENABLED": "FALSE",
        "RENV_CONFIG_PAK_ENABLED": "FALSE",
        "RENV_CONFIG_REPOS_OVERRIDE": "",
        "R_ENVIRON_USER": "",
        "R_PROFILE_USER": "",
        "_R_CHECK_FORCE_SUGGESTS_": "false",
        "NOT_CRAN": "true",
    }
