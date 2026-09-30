# How to read the automation

Start with the workflow, then its command-line script, then the operation it calls.
Each level describes one kind of work. The scripts use ordinary functions and the
Python standard library; there is no task framework to learn.

## Reading order

| File | Question it answers |
|---|---|
| `.github/workflows/ci.yml` | Which checks run, and in what order? |
| `demo.py` | What happens when a developer checks, runs, or fetches an app? |
| `scripts/release.py` | Which release operation did the command request? |
| `scripts/release_tools/build.py` | How is a complete snapshot assembled? |
| `scripts/release_tools/packages.py` | How are package order, reuse, and R checks handled? |
| `scripts/release_tools/restore.py` | How do we test the actual downloaded app? |
| `scripts/release_tools/files.py` | Where do file reads, writes, and subprocesses happen? |

In each operation module, read its first function for the overall sequence.
Helpers below it explain the details. Names describe an action and its subject,
such as `build_package_cohort`, `validate_build_runtime`, and
`verify_fresh_r_session`.

## Data transformation versus actions

`dependency_order`, `release_lockfile`, and `lock_with_repository_url` return new
results without changing their inputs. Tests cover this separation. File copying,
network access, R execution, and directory creation are explicit operations.

`build_snapshot` prepares a temporary directory, checks all packages, saves the
app and metadata, then renames the completed directory into place. Its output
format is the contract with the separate Depository. Internal Python functions
are implementation details; the command-line arguments and snapshot schema are
the stable interface between repositories.

`verify_restore` copies the delivered app into a fresh project, runs its actual
`restore.R`, and starts a separate R process. The R smoke test checks activation
before checking dependencies and app behavior. Do not substitute a convenient
restore helper for the delivered script.

## R scripts

- `bootstrap.R`: obtain the pinned renv version.
- `restore-dependencies.R`: prepare the package-check library.
- `restore-app.R`: prepare and activate a downloaded app's project library.
- `repository-index.R`: create standard CRAN repository indexes.
- `smoke.R`: check the restored library, module, Builder, and exported app.

These scripts define the main operation first, helpers below it, and invoke the
operation at the end. `bootstrap.R` only defines functions because other scripts
source it.

## Keep changes readable

Use a small number of named functions with one purpose each. Keep workflow YAML
focused on orchestration and permissions. Put transformations and business rules
in Python or R files, where they can be read and tested normally. Prefer clear
loops and intermediate names over compressed expressions or clever abstractions.

CI enforces Ruff formatting, import order, basic lint checks, and an 88-character
Python line limit. R scripts use short lines and explicit blocks. To run the
Python style checks locally on macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m ruff format --check .
.venv/bin/python -m ruff check .
python3 -m unittest discover -s tests -v
```

Use `ruff format .` to apply formatting. Ruff is a pinned development dependency;
app users and release commands do not need it.
