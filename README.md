# Teal architecture demo

A small working example of a multi-package R application, a separate CRAN-style Depository, and reproducible releases. All packages and data are examples. No company code is used.

**Start here:** [Developer walkthrough](docs/WALKTHROUGH.md).

## The three actions

1. **Check source** runs automatically for branches and pull requests. It tests the packages together and restores them into a fresh library.
2. **Publish candidate** runs in [the Depository](https://github.com/armcn/teal-depository-demo/actions/workflows/publish.yml). Select a source branch or commit that passed its checks. CI publishes a snapshot and tests installation over HTTPS.
3. **Promote or roll back** selects an already tested snapshot for the simulated production environment. It never rebuilds packages.

The [Depository homepage](https://armcn.github.io/teal-depository-demo/) shows current dev and production selections. They are simulations of deployment selection, **not live Posit Connect applications**. You can run the real Shiny example locally.

## Where things live

| Location | Contents | Edited by |
|---|---|---|
| This repository | R package source, external dependency lock, tests, build scripts | Developers through branches and pull requests |
| CI temporary workspace | Tarballs and app files being prepared and tested | CI |
| Depository `main` | Publishing tools and workflows | Maintainers through pull requests |
| Depository `published` branch | Immutable snapshots, test evidence, environment pointers | Publishing workflow |
| GitHub Pages | HTTPS copy of the Depository's generated `site/` directory | Pages workflow |

The Depository has one permanent generated-output branch. There is **no matching Depository branch for each feature branch**.

## Run locally

Install the R version in `config.json` (currently 4.6.1), Python 3.9 or newer, and Git. A compiler toolchain may be needed for external R packages on your platform.

```sh
git clone https://github.com/armcn/teal-architecture-demo.git
cd teal-architecture-demo
python3 demo.py check
python3 demo.py run
```

Open `http://127.0.0.1:3838`. The first command restores pinned dependencies, builds and checks all four internal packages, then performs a clean installation test. The second starts the example builder. Local builds can contain uncommitted edits and are for development only; publish a candidate before distributing exported apps.

To run the published dev candidate instead:

```sh
python3 demo.py fetch --channel dev
cd downloaded-app
Rscript restore.R
Rscript -e 'shiny::runApp()'
```

`fetch` resolves the channel once, downloads the saved app files, and verifies their checksums. The resulting app remains pinned to that snapshot even when dev changes. Use `--snapshot <id>` to fetch an older snapshot, or `--out <new-directory>` to retain several side by side.

## Package responsibilities

```text
tb.checks ─────┐
              ├─ tb.modules ─ tb.builder
tb.reporter ───┘
```

`tb.checks` contains pure data checks. `tb.reporter` creates a simple report. `tb.modules` supplies a reusable Shiny module and standalone app. `tb.builder` embeds that module and exports app code with its release lockfile.

The source `renv.lock` pins external dependencies. CI adds exact internal package records and an immutable snapshot URL to a generated app lockfile. The source lock is never overwritten by a release build. Dependency upgrades are explicit changes reviewed in Git.

Source CI reads the Depository's published package identities. A missing package version bump therefore fails the pull request check, and unchanged packages are tested using their already published archive bytes.

## Reliability guarantees

- All internal packages are ordered from their `DESCRIPTION` dependencies; dependency cycles fail.
- R and third-party action revisions are pinned. Application dependencies are version-locked.
- Every package receives `R CMD check`; errors and warnings fail the build.
- A cache-disabled restore into an empty library verifies package origins, versions, the module, builder, and exported app.
- Published snapshots contain a full source commit, package source fingerprints, and SHA-256 checksums for every file.
- Reusing a package version with different source fails. Unchanged published packages reuse their original archive bytes.
- Snapshot writes are append-only. Identical publication is retryable; different bytes cannot replace an existing snapshot.
- Publication and promotion share a concurrency group, and Git pushes must fast-forward.
- Package code executes only in jobs with read-only permissions. The write job validates and copies data without running package code.
- Production requires recorded staging evidence, release versions, a source commit reachable from `main`, and the expected current production selection.
- Snapshots are retained independently of short-lived Actions artifacts and feature branch deletion.

Read [architecture and tradeoffs](docs/ARCHITECTURE.md) for the limits and the mapping to company infrastructure.

## Validation commands

```sh
python3 -m unittest discover -s tests -v
python3 demo.py check
```

The separate Depository has additional tests for corruption, immutability, version collisions, path traversal, staging requirements, and stale promotions.
