# Architecture and transfer to company infrastructure

## Source, package distribution, and installed libraries

The monorepo contains source. R CMD build creates source tarballs in a temporary CI directory. The Depository retains these archives under `site/snapshots/<id>/src/contrib/`. Connect or renv installs the archives into an R library. These are three different things.

Each snapshot also retains `app/` (entry point, exact lockfile, restoration scripts, release identity), a smoke test, and `release.json` with the file inventory and checksums. The complete snapshot is a reviewable release artifact.

The Depository's default branch contains trusted publication code. Its permanent `published` branch contains generated files. This allows normal review requirements on workflow code without making the automated publication job bypass those requirements. It is a storage implementation choice, not a branch paired with application feature work.

## Why a pull publisher

The public demo's publishing workflow lives in the Depository. A maintainer supplies a source ref. The workflow resolves the ref once, requires passing source CI, and checks out that exact commit. This avoids a personal access token spanning both repositories. For private company repositories, use an installation token from a narrowly scoped GitHub App (or your CI platform's equivalent).

Source code executes in read-only build and verification jobs. A separate privileged job receives only a candidate artifact, validates filenames and SHA-256 checksums, and copies files into generated storage. It does not source R or Python code from the candidate.

GitHub Actions artifacts are temporary transport, with a seven-day retention window. The durable copies live in the Depository's generated branch and Pages site. Deleting a source branch has no effect on them.

## Promotion and failure recovery

Publish complete snapshots before updating environment selections. Git commits provide an atomic repository update; Pages publishes the complete retained site. HTTPS verification checks every published file and a fresh renv restore before recording dev evidence.

The restore check runs the actual saved `app/restore.R`, then starts a separate R process using the generated `.Rprofile`. It checks that this process selected the app's project library before testing package versions and application behavior. This prevents a helper test from passing while the files developers download install into a different library.

All writer workflows share a concurrency group. Git push refuses non-fast-forward changes. Production updates also use a compare-and-set check against an expected current snapshot. Together these prevent silent lost updates. GitHub can replace an older pending run with a newer pending run; the action can be started again. No in-progress publication is cancelled by the workflow configuration.

A Pages failure can leave Git ahead of the served website. **Republish retained site** validates and republishes the retained data without a package rebuild. Rerun failed jobs afterward. Consumers use immutable URLs, so moving a channel pointer does not alter an already pinned app.

Every promotion has durable staging evidence and history. Checksums detect corruption and inconsistent publication; they are not independent signatures against an administrator who can rewrite both files and metadata.

## Package version policy

A package name/version is associated with one archive. Each internal package has a source fingerprint. If the source is unchanged, a new candidate reuses its published archive. If the source changed without a version bump, publication fails. This avoids timestamp differences between repeated R builds creating competing archive bytes for an unchanged package.

Development versions may have a fourth numeric component. Production accepts at most three components. This is an explicit convention for this demo; adapt it to company policy. Package versions remain independent: changing the reporter does not require bumping every package.

## Runtime prerequisites

Use the exact R version in `renv.lock` and a C/C++ build toolchain when installing source packages. Bootstrap selects the libuv source bundled with the pinned `fs` package (`USE_BUNDLED_LIBUV=1`), so Linux restores do not depend on an undeclared system libuv installation. For the real company packages, document and provision every additional system library in the runner and Connect images.

## What is deliberately simulated

- Dev and production are persisted selections plus real installation and application smoke tests. There is no Connect server in this example.
- The nested Shiny module and downloadable generated app are real, but intentionally small. The packages do not implement real Teal functionality.
- Exported apps carry the full release lockfile. A smaller runtime dependency closure could be added after the release process is proven.
- Third-party package versions are pinned and retrieved from public CRAN. Long-term operation still depends on their availability. The company can replace this with its approved retained package mirror or snapshot service.
- R is pinned, but `ubuntu-24.04` runner images receive updates. Full OS reproducibility would require a separately maintained container image pinned by digest and compatible Connect execution settings.
- All snapshots are retained for this small example. There is no automatic deletion; durable exports make naive branch-based cleanup unsafe. A company retention policy should distinguish temporary candidates and supported releases.
- Repository owners can bypass or modify repository settings. Organization roles, protected branches, narrow publisher identities, and audit controls should enforce read-only distribution for ordinary consumers.

## Mapping to the company environment

| Example | Company equivalent |
|---|---|
| Four mock packages | Existing Builder, adapters, checks, modules and Reporter packages |
| GitHub Pages | Existing HTTPS CRAN-like Depository hosting |
| Published snapshot ID | Immutable release/candidate directory; dates can remain friendly release labels |
| Generated app lockfile | Dependency input to rsconnect manifest generation |
| Dev/prod selection | Deploy the corresponding saved app bundle to the chosen Connect application |
| Clean restore smoke test | Same test plus genuine Teal module, reporting, data-compatibility and deployment checks |
| Per-project renv library | Existing dated shared library, separated by compatible R version and platform |

Connect integration must be tested against the company's actual rsconnect/Connect versions, repository overrides, authentication, operating system libraries and R installations. Before final promotion, generate and inspect its deployment manifest from the saved app lockfile. Keep credentials in the CI secret store and environment-specific configuration outside the package archives.

## Primary references

- [renv package sources](https://rstudio.github.io/renv/articles/package-sources.html)
- [Posit Connect reproducible R deployment](https://docs.posit.co/connect/how-to/use-renv-for-reproducible-r-deployments/)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
