"""Which source the running process was built from.

AGPL-3.0 section 13 obliges the deployment to offer every remote user the
Corresponding Source of the version they are using. "The repository" is not
enough once the fork moves on, so the Source code link is pinned to a commit.

Resolution order:

1. ``settings.SOURCE_COMMIT``, which the Docker build bakes in from a build
   argument. This is the only source used in production images (they contain
   no ``.git`` directory; see ``.dockerignore``).
2. The working copy's ``.git`` directory, read directly (no ``git`` binary),
   so a development server links to the commit it is running.

Anything else resolves to "unknown", which the source page states plainly and
the deploy check ``about.E002`` refuses.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _normalise_sha(value: str) -> str:
    value = (value or "").strip().lower()
    return value if _SHA_RE.match(value) else ""


def _resolve_git_dir(dot_git: Path) -> Path | None:
    """The real git directory behind ``.git``, which may be a ``gitdir:`` file (worktrees, submodules)."""
    if dot_git.is_dir():
        return dot_git
    if dot_git.is_file():
        content = dot_git.read_text(encoding="utf-8", errors="replace").strip()
        if content.startswith("gitdir:"):
            target = Path(content.split(":", 1)[1].strip())
            if not target.is_absolute():
                target = (dot_git.parent / target).resolve()
            return target if target.is_dir() else None
    return None


def _read_ref(git_dir: Path, ref: str) -> str:
    """Look ``ref`` up as a loose ref, then in ``packed-refs``, in this dir and its common dir."""
    search = [git_dir]
    commondir = git_dir / "commondir"
    if commondir.is_file():
        common = Path(commondir.read_text(encoding="utf-8").strip())
        search.append(common if common.is_absolute() else (git_dir / common).resolve())
    for directory in search:
        loose = directory / ref
        if loose.is_file():
            return _normalise_sha(loose.read_text(encoding="utf-8"))
        packed = directory / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref:
                    return _normalise_sha(parts[0])
    return ""


def commit_from_git_dir(dot_git: Path) -> str:
    """The commit ``HEAD`` points at in the repository whose ``.git`` is ``dot_git``, or ""."""
    try:
        git_dir = _resolve_git_dir(dot_git)
        if git_dir is None:
            return ""
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref:"):
            return _read_ref(git_dir, head.split(":", 1)[1].strip())
        return _normalise_sha(head)
    except OSError:
        return ""


@functools.cache
def running_commit() -> str:
    """The full commit SHA of the running code, or "" when it cannot be established."""
    configured = _normalise_sha(getattr(settings, "SOURCE_COMMIT", ""))
    if configured:
        return configured
    return commit_from_git_dir(Path(settings.BASE_DIR) / ".git")


@dataclass(frozen=True)
class SourceInfo:
    """Everything a template needs to point a user at the running source."""

    repository_url: str
    commit: str
    upstream_name: str
    upstream_url: str
    license_name: str

    @property
    def short_commit(self) -> str:
        return self.commit[:7]

    @property
    def is_pinned(self) -> bool:
        """True when the link leads to the exact running version, not just the repository."""
        return bool(self.repository_url and self.commit)

    @property
    def browse_url(self) -> str:
        """The source tree at the running commit (GitHub URL layout)."""
        if self.is_pinned:
            return f"{self.repository_url}/tree/{self.commit}"
        return self.repository_url

    @property
    def archive_url(self) -> str:
        """A zip of the source at the running commit (GitHub URL layout), or ""."""
        if self.is_pinned:
            return f"{self.repository_url}/archive/{self.commit}.zip"
        return ""

    @property
    def license_url(self) -> str:
        """The LICENSE file as shipped in the running version (GitHub URL layout), or ""."""
        if self.is_pinned:
            return f"{self.repository_url}/blob/{self.commit}/LICENSE"
        if self.repository_url:
            return f"{self.repository_url}/blob/HEAD/LICENSE"
        return ""

    @property
    def clone_url(self) -> str:
        return f"{self.repository_url}.git" if self.repository_url else ""

    @property
    def clone_dir(self) -> str:
        """The directory ``git clone`` creates for this repository."""
        return self.repository_url.rsplit("/", 1)[-1] if self.repository_url else ""


def source_info() -> SourceInfo:
    return SourceInfo(
        repository_url=getattr(settings, "SOURCE_CODE_URL", "").rstrip("/"),
        commit=running_commit(),
        upstream_name=getattr(settings, "UPSTREAM_PROJECT_NAME", "BrightBean Studio"),
        upstream_url=getattr(settings, "UPSTREAM_SOURCE_URL", ""),
        license_name=getattr(settings, "SOFTWARE_LICENSE", "AGPL-3.0"),
    )
