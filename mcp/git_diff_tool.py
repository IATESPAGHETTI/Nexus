"""Bounded, allowlisted access to the NEXUS repo's own git history.

Evidence source for get_git_diff: not the simulated production HTTP API (production/
doesn't track deployments as real commits), but the NEXUS repo's real git history for
the paths that actually make up what gets "deployed" (production/, backend/, mcp/).
This is genuine `git` execution, not a filesystem walk or arbitrary shell access:

- only `git log -p` / `git diff` / `git status`, never arbitrary commands
- only against this repo (`-C REPO_ROOT`), never another path
- only for an explicit allowlist of top-level paths (config.GIT_DIFF_ALLOWED_PATHS)
- fixed timeout, output size cap
"""

from __future__ import annotations

import os
import subprocess

from config import (
    GIT_DIFF_ALLOWED_PATHS,
    GIT_DIFF_MAX_COMMITS,
    GIT_DIFF_MAX_OUTPUT_CHARS,
    GIT_TIMEOUT_SECONDS,
    REPO_ROOT,
)


class InvalidGitDiffPathError(Exception):
    pass


class GitDiffDisabledError(Exception):
    pass


DISABLED_MESSAGE = (
    "get_git_diff is disabled: this repository's own history contains the simulator's fault-injection "
    "code and docs, so reading it would tell the agent the answer (blind-evaluation contamination). "
    "Set NEXUS_ENABLE_GIT_DIFF=1 to enable it deliberately. Use get_recent_deployments for change history."
)


def _validate_paths(paths: list[str]) -> list[str]:
    if not paths:
        return list(GIT_DIFF_ALLOWED_PATHS)
    for path in paths:
        if path not in GIT_DIFF_ALLOWED_PATHS:
            raise InvalidGitDiffPathError(
                f"{path!r} is not in the allowed path list {GIT_DIFF_ALLOWED_PATHS}"
            )
    return paths


def _run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",  # git emits UTF-8; the Windows default (cp1252) crashed on non-ASCII history
        errors="replace",
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )
    return result.stdout


def get_diff(paths: list[str] | None = None, max_commits: int = GIT_DIFF_MAX_COMMITS) -> dict:
    if os.environ.get("NEXUS_ENABLE_GIT_DIFF") != "1":
        raise GitDiffDisabledError(DISABLED_MESSAGE)
    scoped_paths = _validate_paths(paths or [])
    max_commits = max(1, min(max_commits, GIT_DIFF_MAX_COMMITS))

    commit_count_raw = _run_git(["rev-list", "--count", "HEAD", "--", *scoped_paths])
    has_commits = commit_count_raw.strip().isdigit() and int(commit_count_raw.strip()) > 0

    history = ""
    if has_commits:
        history = _run_git(
            ["log", "-p", f"-n{max_commits}", "--", *scoped_paths]
        )

    uncommitted_stat = _run_git(["diff", "--stat", "--", *scoped_paths])
    staged_stat = _run_git(["diff", "--cached", "--stat", "--", *scoped_paths])

    truncated = len(history) > GIT_DIFF_MAX_OUTPUT_CHARS
    if truncated:
        history = history[:GIT_DIFF_MAX_OUTPUT_CHARS]

    return {
        "paths": scoped_paths,
        "commit_history_available": has_commits,
        "commit_log_diff": history,
        "commit_log_truncated": truncated,
        "uncommitted_changes_stat": uncommitted_stat.strip(),
        "staged_changes_stat": staged_stat.strip(),
    }
