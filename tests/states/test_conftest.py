import pathlib

from libvcs.conftest import CreateRepoCallbackFixtureProtocol


def test_create_git_remote_repo(
    create_git_remote_repo: CreateRepoCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
):
    git_remote_1 = create_git_remote_repo()
    git_remote_2 = create_git_remote_repo()

    assert git_remote_1 != git_remote_2


def test_create_svn_remote_repo(
    create_svn_remote_repo: CreateRepoCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
):
    svn_remote_1 = create_svn_remote_repo()
    svn_remote_2 = create_svn_remote_repo()

    assert svn_remote_1 != svn_remote_2