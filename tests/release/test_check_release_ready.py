"""Release gates must not let workspace overrides mask wheel requirements."""

import subprocess
import sys
from pathlib import Path

import check_release_ready as guard
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMMAND = "python3 scripts/release/check_release_ready.py"


def test_current_migration_blocks_release(capsys):
    assert guard.main(["--repo-root", str(ROOT)]) == 1
    message = capsys.readouterr().err
    assert "Release blocked:" in message
    assert "HUGR" in message
    assert "Selene compiler" in message
    assert "distributable dependency ranges" in message


def test_guard_cli_blocks_before_publication(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.guppylang.release]\nblocked-reason = "Unreleased dependency"\n'
    )
    result = subprocess.run(  # noqa: S603 - interpreter and repository script are fixed
        [
            sys.executable,
            str(ROOT / "scripts/release/check_release_ready.py"),
            "--repo-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Unreleased dependency" in result.stderr


def test_repository_without_blocker_can_release(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "example"\n')
    assert guard.main(["--repo-root", str(tmp_path)]) == 0


@pytest.mark.parametrize("reason", ['""', '"   "', "false", "42"])
def test_malformed_blocker_fails_closed(tmp_path, reason, capsys):
    (tmp_path / "pyproject.toml").write_text(
        f"[tool.guppylang.release]\nblocked-reason = {reason}\n"
    )
    assert guard.main(["--repo-root", str(tmp_path)]) == 1
    assert "Cannot verify release readiness" in capsys.readouterr().err


def test_missing_repository_fails_closed(tmp_path):
    assert guard.main(["--repo-root", str(tmp_path)]) == 1


def workflow(name):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def guard_index(steps):
    return next(i for i, step in enumerate(steps) if step.get("run") == COMMAND)


@pytest.mark.parametrize(
    ("job", "publication"),
    [("tag-release-line", "git tag"), ("create-release", "gh release create")],
)
def test_tag_and_release_mutations_are_guarded(job, publication):
    steps = workflow("release-publish.yml")["jobs"][job]["steps"]
    gate = guard_index(steps)
    assert any(
        step.get("uses", "").startswith("actions/checkout@") for step in steps[:gate]
    )
    assert gate < next(
        i for i, step in enumerate(steps) if publication in step.get("run", "")
    )


def test_pypi_publication_checks_tagged_source():
    job = workflow("python-wheels.yml")["jobs"]["publish"]
    assert job["permissions"]["contents"] == "read"
    steps = job["steps"]
    gate = guard_index(steps)
    publish = next(
        i
        for i, step in enumerate(steps)
        if step.get("uses", "").startswith("pypa/gh-action-pypi-publish@")
    )
    assert gate < publish
    checkouts = [
        step
        for step in steps[:gate]
        if step.get("uses", "").startswith("actions/checkout@")
    ]
    assert len(checkouts) == 1
    # Checkout's default ref is the workflow's tag; do not replace it with main.
    assert "ref" not in checkouts[0].get("with", {})
    assert steps[gate]["if"] == steps[publish]["if"] == checkouts[0]["if"]


def test_release_compatibility_uses_registry_and_native_build_tools():
    steps = workflow("release-checks.yml")["jobs"]["check-release-guppylang"]["steps"]
    sync = next(i for i, step in enumerate(steps) if "uv sync" in step.get("run", ""))
    assert guard_index(steps) < sync
    assert "uv lock --no-sources" in steps[sync]["run"]
    assert "uv sync --no-sources" in steps[sync]["run"]
    assert any(
        step.get("uses", "").startswith("dtolnay/rust-toolchain@")
        for step in steps[:sync]
    )
    assert any(
        step.get("uses", "").startswith(
            "quantinuum/hugrverse-env/install-hugrenv-action@"
        )
        and step["with"]["packages"] == "llvm"
        for step in steps[:sync]
    )


def test_draft_source_checks_remain_enabled():
    jobs = workflow("pull-request.yaml")["jobs"]
    for name in ["check", "test-coverage"]:
        steps = jobs[name]["steps"]
        assert all(step.get("run") != COMMAND for step in steps)
        sync = next(
            i
            for i, step in enumerate(steps)
            if "uv sync --frozen" in step.get("run", "")
        )
        assert any(
            step.get("uses", "").startswith(
                "quantinuum/hugrverse-env/install-hugrenv-action@"
            )
            for step in steps[:sync]
        )
