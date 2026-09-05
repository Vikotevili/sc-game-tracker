from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .config import ROOT, git_branch, git_remote


def find_git() -> str | None:
    found = shutil.which("git")
    if found:
        return found
    candidates = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        str(Path.home() / r"AppData\Local\Programs\Git\cmd\git.exe"),
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def _run(git: str, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    return subprocess.run(
        [git, *args],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
        env=env,
    )


def ensure_repo(git: str) -> None:
    if not (ROOT / ".git").exists():
        _run(git, ["init", "-b", git_branch()])


def has_remote(git: str) -> bool:
    result = _run(git, ["remote"], check=False)
    remotes = result.stdout.split()
    return git_remote() in remotes


def identity_args(git: str) -> list[str]:
    name = _run(git, ["config", "user.name"], check=False).stdout.strip()
    email = _run(git, ["config", "user.email"], check=False).stdout.strip()
    extra: list[str] = []
    if not name:
        extra.extend(["-c", "user.name=sc-game-tracker"])
    if not email:
        extra.extend(["-c", "user.email=sc-game-tracker@local"])
    return extra


def commit_and_push(paths: list[Path], message: str, do_push: bool) -> dict[str, str]:
    git = find_git()
    if not git:
        return {"status": "skipped", "reason": "git_not_installed"}

    ensure_repo(git)
    for path in paths:
        rel = path.resolve().relative_to(ROOT)
        _run(git, ["add", "--", str(rel).replace("\\", "/")], check=False)

    staged = _run(git, ["diff", "--cached", "--name-only"], check=False)
    if not staged.stdout.strip():
        return {"status": "unchanged", "reason": "no_changes"}

    extra = identity_args(git)
    commit = _run(git, extra + ["commit", "-m", message], check=False)
    if commit.returncode != 0:
        return {
            "status": "error",
            "reason": "commit_failed",
            "detail": (commit.stderr or commit.stdout).strip(),
        }

    if not do_push:
        return {"status": "committed", "reason": "push_disabled"}
    if not has_remote(git):
        return {"status": "committed", "reason": "no_remote"}

    push = _run(git, ["push", "-u", git_remote(), git_branch()], check=False)
    if push.returncode != 0:
        return {
            "status": "committed",
            "reason": "push_failed",
            "detail": (push.stderr or push.stdout).strip(),
        }
    return {"status": "pushed", "reason": "ok"}
