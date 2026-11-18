"""Resolving the running commit, and the URLs built from it."""

import pytest
from django.test import override_settings

from apps.about.version import SourceInfo, commit_from_git_dir, running_commit, source_info

SHA = "14b92fc0123456789abcdef0123456789abcdef0"
OTHER_SHA = "a2cef5b0123456789abcdef0123456789abcdef0"


@pytest.fixture(autouse=True)
def _clear_commit_cache():
    running_commit.cache_clear()
    yield
    running_commit.cache_clear()


def _make_repo(tmp_path, head, refs=None, packed=None):
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text(head + "\n")
    for ref, sha in (refs or {}).items():
        path = git / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sha + "\n")
    if packed:
        (git / "packed-refs").write_text(
            "# pack-refs with: peeled fully-peeled sorted\n" + "".join(f"{sha} {ref}\n" for ref, sha in packed.items())
        )
    return git


class TestCommitFromGitDir:
    def test_loose_branch_ref(self, tmp_path):
        git = _make_repo(tmp_path, "ref: refs/heads/main", refs={"refs/heads/main": SHA})
        assert commit_from_git_dir(git) == SHA

    def test_packed_ref(self, tmp_path):
        git = _make_repo(tmp_path, "ref: refs/heads/main", packed={"refs/heads/main": SHA})
        assert commit_from_git_dir(git) == SHA

    def test_loose_ref_wins_over_packed(self, tmp_path):
        git = _make_repo(
            tmp_path,
            "ref: refs/heads/main",
            refs={"refs/heads/main": SHA},
            packed={"refs/heads/main": OTHER_SHA},
        )
        assert commit_from_git_dir(git) == SHA

    def test_detached_head(self, tmp_path):
        git = _make_repo(tmp_path, SHA)
        assert commit_from_git_dir(git) == SHA

    def test_gitdir_file_as_used_by_worktrees(self, tmp_path):
        real = _make_repo(tmp_path, "ref: refs/heads/main", refs={"refs/heads/main": SHA})
        checkout = tmp_path / "checkout"
        checkout.mkdir()
        (checkout / ".git").write_text(f"gitdir: {real}\n")
        assert commit_from_git_dir(checkout / ".git") == SHA

    def test_missing_repository_is_unknown(self, tmp_path):
        assert commit_from_git_dir(tmp_path / ".git") == ""

    def test_unborn_branch_is_unknown(self, tmp_path):
        git = _make_repo(tmp_path, "ref: refs/heads/main")
        assert commit_from_git_dir(git) == ""

    def test_garbage_head_is_unknown(self, tmp_path):
        git = _make_repo(tmp_path, "not a sha")
        assert commit_from_git_dir(git) == ""


class TestRunningCommit:
    def test_build_setting_wins_over_working_copy(self, tmp_path):
        _make_repo(tmp_path, OTHER_SHA)
        with override_settings(SOURCE_COMMIT=SHA.upper(), BASE_DIR=tmp_path):
            assert running_commit() == SHA

    def test_falls_back_to_working_copy(self, tmp_path):
        _make_repo(tmp_path, SHA)
        with override_settings(SOURCE_COMMIT="", BASE_DIR=tmp_path):
            assert running_commit() == SHA

    def test_invalid_build_setting_is_ignored(self, tmp_path):
        with override_settings(SOURCE_COMMIT="latest", BASE_DIR=tmp_path):
            assert running_commit() == ""


class TestSourceInfo:
    def _info(self, repository_url="https://github.com/studio/brown-creative-studio", commit=SHA):
        return SourceInfo(
            repository_url=repository_url,
            commit=commit,
            upstream_name="BrightBean Studio",
            upstream_url="https://github.com/brightbeanxyz/brightbean-studio",
            license_name="AGPL-3.0",
        )

    def test_pinned_links_lead_to_the_running_commit(self):
        info = self._info()
        assert info.is_pinned
        assert info.short_commit == SHA[:7]
        assert info.browse_url == f"https://github.com/studio/brown-creative-studio/tree/{SHA}"
        assert info.archive_url == f"https://github.com/studio/brown-creative-studio/archive/{SHA}.zip"
        assert info.license_url == f"https://github.com/studio/brown-creative-studio/blob/{SHA}/LICENSE"
        assert info.clone_url == "https://github.com/studio/brown-creative-studio.git"
        assert info.clone_dir == "brown-creative-studio"

    def test_unknown_commit_falls_back_to_the_repository(self):
        info = self._info(commit="")
        assert not info.is_pinned
        assert info.browse_url == "https://github.com/studio/brown-creative-studio"
        assert info.archive_url == ""

    def test_no_repository(self):
        info = self._info(repository_url="")
        assert not info.is_pinned
        assert info.browse_url == ""
        assert info.clone_url == ""

    def test_source_info_reads_settings(self, tmp_path):
        with override_settings(
            SOURCE_CODE_URL="https://github.com/studio/brown-creative-studio/",
            SOURCE_COMMIT=SHA,
            BASE_DIR=tmp_path,
        ):
            info = source_info()
        assert info.repository_url == "https://github.com/studio/brown-creative-studio"
        assert info.commit == SHA
        assert info.upstream_name == "BrightBean Studio"
        assert info.license_name == "AGPL-3.0"
