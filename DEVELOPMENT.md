# Welcome to the Guppy development guide <!-- omit in toc -->

This guide is intended to help you get started with developing guppylang.

If you find any errors or omissions in this document, please [open an issue](https://github.com/quantinuum/guppylang/issues/new)!

## #️⃣ Setting up the development environment

You can setup the development environment in two ways:

### The Nix way

The easiest way to setup the development environment is to use the provided
[`devenv.nix`](devenv.nix) file. This will setup a development shell with all the
required dependencies.

To use this, you will need to install [devenv](https://devenv.sh/getting-started/).
Once you have it running, open a shell with:

```bash
devenv shell
```

All the required dependencies should be available. You can automate loading the
shell by setting up [direnv](https://devenv.sh/automatic-shell-activation/).

### Manual setup

To setup the environment manually you will need:

- Just: [just.systems](https://just.systems/)
- uv `>=0.6`: [docs.astral.sh](https://docs.astral.sh/uv/getting-started/installation/)
  - If you have an older manually installed `uv` version you can upgrade it with `uv self update`,
    or by following the instructions in your package manager.
- bencher_cli: [bencer.dev](https://bencher.dev/docs/tutorial/quick-start/?adapter=json)

Once you have these installed, you can install the required python dependencies and setup pre-commit hooks with:

```bash
just setup
```

## 🏃 Running the tests

To compile and test the code, run:

```bash
just test
# or, to try a specific test
just test -k test_name
```

If you need to export the integration test cases, use:

```bash
just export-integration-tests
```

Run `just` to see all available commands.

## 🐰 Running the benchmarks

To run the benchmarks using `pytest-benchmark`:

```bash
just bench
# or, to specify a directory and name for the report to be saved locally
just bench_save <dir> <name>
```

If you save the results, then you can compare them following
[this approach](https://pytest-benchmark.readthedocs.io/en/latest/comparing.html).
However, this would only let you compare the `latency` or running time,
but not the other custom metrics like `hugr_bytes` and `hugr_nodes`.

You can also upload benchmark results to the
[guppylang-benchmarks](https://bencher.dev/console/projects/guppylang-benchmarks)
bencher project with:

```bash
just bench_upload
```

And if you want to compare your local changes against the base benchmarks (main),
including `latency`, `hugr_bytes` and `hugr_nodes` you can use:

```bash
just bench_compare
```

## 💅 Coding Style

The python code in this repository is formatted using `ruff`. Most IDEs will
provide automatic formatting on save, but you can also run the formatter manually:

```bash
just format
```

We also use various linters to catch common mistakes and enforce best practices. To run these, use:

```bash
just check
```

To quickly fix common issues, run:

```bash
just fix
```

## 📈 Code Coverage

We run coverage checks on the CI. Once you submit a PR, you can review the
line-by-line coverage report on
[codecov](https://app.codecov.io/gh/quantinuum/guppylang/commits?branch=All%20branches).

To generate the coverage info locally, simply run:

```bash
just coverage
```

and open it with your favourite coverage viewer. In VSCode, you can use
[`coverage-gutters`](https://marketplace.visualstudio.com/items?itemName=ryanluker.vscode-coverage-gutters).

## 🌐 Contributing to Guppy

We welcome contributions to Guppy! Please open [an issue](https://github.com/quantinuum/guppylang/issues/new) or [pull request](https://github.com/quantinuum/guppylang/compare) if you have any questions or suggestions.

PRs should be made against the `main` branch, and should pass all CI checks before being merged. This includes using the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) format for the PR title.

The general format of a contribution title should be:

```text
<type>(<scope>)!: <description>
```

Where the scope is optional, and the `!` is only included if this is a semver breaking change that requires a major version bump.

We accept the following contribution types:

- feat: New features.
- fix: Bug fixes.
- docs: Improvements to the documentation.
- style: Formatting, missing semi colons, etc; no code change.
- refactor: Refactoring code without changing behaviour.
- perf: Code refactoring focused on improving performance.
- test: Adding missing tests, refactoring tests; no production code change.
- ci: CI related changes. These changes are not published in the changelog.
- chore: Updating build tasks, package manager configs, etc. These changes are not published in the changelog.
- revert: Reverting previous commits.

## :shipit: Releasing new versions

We use automation to bump the version number and generate changelog entries
based on the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) labels. Release PRs are created automatically
for each package when new changes are merged into the `main` branch. Once the PR is
approved by someone in the [release team](.github/CODEOWNERS) and is merged, the new package
is published on PyPI.

The changelog can be manually edited before merging the release PR. Note however
that modifying the diff before other changes are merged will cause the
automation to close the release PR and create a new one to avoid conflicts.

Releases are managed by `release-please`. This tool always bumps the
minor version (or the pre-release version if the previous version was a
pre-release).

To override the version getting released, you must merge a PR to `main` containing
`Release-As: 0.1.0` in the description.
Python pre-release versions should be formatted as `0.1.0a1` (or `b1`, `rc1`).

Before merging a release PR, make sure to update the uv lock file by running `uv
lock` and pushing to the release branch.
When releasing `guppylang-internals`, also update the dependency version in `guppylang/pyproject.toml`.

### Patch releases

Sometimes we need to release a patch version to fix a critical bug, but we don't want
to include all the changes that have been merged into the main branch. In this case,
you can create a new branch from the latest release tag and cherry-pick the commits
you want to include in the patch release.

You will need to modify the version and changelog manually in this case. Check
the existing release PRs for examples on how to do this. Once the branch is
ready, create a draft PR so that the release team can review it.

The wheel building process and publication to PyPI is handled by the CI. Just
create a [github release](https://github.com/quantinuum/guppylang/releases/new) from
the **unmerged** branch, and the CI will take care of the rest. The release tag
should follow the format used in the previous releases, e.g. `v0.1.1`.

After the release is published, make sure to merge the changes to the CHANGELOG
and versions back into the `main` branch. This may be done by cherry-picking the
PR used to create the release.
