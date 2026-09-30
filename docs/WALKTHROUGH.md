# Try a complete release

## 1. Make and check a change

Create a feature branch in this repository. For a visible example, change the report text in `packages/tb.reporter/R/report.R`, update its test, and increment `Version` in that package's `DESCRIPTION`.

Use a development version such as `0.1.1.9001` while experimenting. Every changed version that you publish must have a new version number. You do not need to publish every local edit.

Push the branch and open a pull request. Wait for **Check source / Packages and clean restore**. Its job log names each package and test. Local equivalent: `python3 demo.py check`.

## 2. Publish a feature candidate (optional)

Open [Publish candidate](https://github.com/armcn/teal-depository-demo/actions/workflows/publish.yml) in the Depository. Choose **Run workflow**, leave the workflow branch as `main`, and put your feature branch name in `source_ref`.

CI resolves that name to a full commit, verifies that source CI passed, builds the internal packages, tests a clean install, publishes the snapshot, and repeats the restore over public HTTPS. The successful run summary gives a snapshot ID such as `run-12345-1-abcdef123456`.

The snapshot ID identifies saved files, not a branch. Later commits on the feature branch cannot change those files.

## 3. Make a release candidate

Set the intended release package versions (for example `0.1.1`, without a fourth development component). Merge the pull request. Wait for source CI on `main` to pass, then run **Publish candidate** with `source_ref=main`.

The [Depository homepage](https://armcn.github.io/teal-depository-demo/) shows the verified candidate as **dev**. These final release package bytes are what will be promoted. Do not rename or rebuild them after testing.

## 4. Select production

Open [Promote or roll back](https://github.com/armcn/teal-depository-demo/actions/workflows/promote.yml).

- `snapshot`: the candidate's exact ID.
- `expected_current`: the production ID shown on the homepage, or `none` before the first release.

The workflow verifies the retained snapshot again, checks its staging evidence and source provenance, then changes `channels/prod.json`. It leaves every package and app file unchanged. A production environment exists so company maintainers can add reviewer requirements later.

In this example, changing the production pointer simulates choosing the release for Connect. It does not deploy to a Connect server.

## 5. Roll back

Run **Promote or roll back** again, selecting an older, previously tested release. Enter the current production ID in `expected_current`. This restores the earlier selection without rebuilding packages. The `history/` directory records both transitions.

## 6. Prove that old apps keep working

An app exported by a published Builder candidate carries `renv.lock`, `release.json`, and restoration scripts. Restore and run that export after selecting a newer production snapshot. It should still use the original package versions, because its lockfile names an immutable snapshot rather than `prod` or `latest`.

The automated smoke test checks that exported app code executes and that its lockfile is byte-identical to the Builder release lockfile. The demo uses the complete release package cohort for exports; reducing it to a smaller dependency closure is a later optimization.

## Common failures

| Message or situation | Meaning | What to do |
|---|---|---|
| No successful Check source run | The selected commit hasn't passed CI | Wait for CI or fix the failure, then publish again |
| Package changed: bump Version | Published name/version already identifies different code | Increment that package's `DESCRIPTION` version |
| Production changed | Someone promoted another snapshot after you looked | Inspect current production, then deliberately retry with that ID |
| Development package versions cannot be promoted | Candidate still uses development versions | Set release versions on a branch, merge, and publish a new candidate |
| Source is not an ancestor of main | Feature work has not been merged | Merge and publish the merged code |
| Pages deployment fails after a Git commit | Snapshot is retained but HTTPS publication failed | Run **Republish retained site**, then rerun failed jobs in the original publication workflow |
| Restore fails | A required package or runtime is unavailable | Read the named package and URL in logs; fix infrastructure or create a new candidate |
| CI cancelled a pending publication | GitHub concurrency retains a running and a pending request | Run the desired action again once the active publication finishes |

Do not edit package archives or lockfiles in the Depository to fix failures. Make a source/configuration change and publish a new candidate.
