import os
import sys
import glob
import requests
import subprocess
import tempfile
import github

from .utils import write_secrets_to_files

if "GITHUB_TOKEN" in os.environ:
    FEEDSTOCK_TOKENS_REPO = (
        github
        .Github(os.environ["GITHUB_TOKEN"])
        .get_repo("conda-forge/feedstock-tokens")
    )
else:
    FEEDSTOCK_TOKENS_REPO = None


def feedstock_token_exists(feedstock_name):
    r = requests.get(
        "https://api.github.com/repos/conda-forge/"
        "feedstock-tokens/contents/tokens/%s.json" % (feedstock_name),
        headers={"Authorization": "token %s" % os.environ["GITHUB_TOKEN"]},
    )
    if r.status_code != 200:
        return False
    else:
        return True


def delete_feedstock_token(feedstock_name):
    if FEEDSTOCK_TOKENS_REPO is None:
        raise RuntimeError(
            "Cannot delete feedstock token for %s since "
            "we do not have a github token!" % feedstock_name
        )
    token_file = "tokens/%s.json" % feedstock_name
    fn = FEEDSTOCK_TOKENS_REPO.get_contents(token_file)
    FEEDSTOCK_TOKENS_REPO.delete_file(
        token_file,
        "[ci skip] [skip ci] [cf admin skip] ***NO_CI*** removing "
        "token for %s" % feedstock_name,
        fn.sha,
    )


def reset_feedstock_token(name, skips=None):
    from conda_smithy.ci_register import travis_get_repo_info
    skips = skips or []

    if "travis" not in skips:
        # test to make sure travis ci api is working
        # if not skip migration
        repo_info = travis_get_repo_info("conda-forge", name + "-feedstock")
        if not repo_info:
            raise RuntimeError("Travis-CI API token is not working!")

    owner_info = ['--organization', 'conda-forge']
    token_repo = (
        'https://x-access-token:${GITHUB_TOKEN}@github.com/'
        'conda-forge/feedstock-tokens'
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        feedstock_dir = os.path.join(tmpdir, name + "-feedstock")
        os.makedirs(feedstock_dir)

        if feedstock_token_exists(name + "-feedstock"):
            delete_feedstock_token(name + "-feedstock")

        subprocess.check_call(
            ['conda', 'smithy', 'generate-feedstock-token',
             '--feedstock_directory', feedstock_dir] + owner_info)
        subprocess.check_call(
            [
                'conda', 'smithy', 'register-feedstock-token',
                '--without-circle', '--without-drone',
                '--without-github-actions',
            ]
            + [
                f"--without-{s.replace('_', '-')}" for s in skips
                if s not in [
                    "circle",
                    "drone",
                    "github_actions",
                ]
            ]
            + [
                '--feedstock_directory', feedstock_dir,
            ]
            + owner_info
            + ['--token_repo', token_repo]
        )

        subprocess.check_call(
            [
                'conda', 'smithy', 'rotate-binstar-token',
                '--without-appveyor', '--without-azure',
                '--without-circle', '--without-drone',
                '--without-github-actions',
            ]
            + [
                f"--without-{s.replace('_', '-')}" for s in skips
                if s not in [
                    "circle",
                    "drone",
                    "appveyor",
                    "azure",
                    "github_actions",
                ]
            ]
            + [
                '--token_name', 'STAGING_BINSTAR_TOKEN'
            ],
            cwd=feedstock_dir)


def run(request):
    assert "packages" in request
    packages = request["packages"]

    skips = request.get("skip_providers", [])

    pkgs_to_do_again = []

    for pkg in pkgs:
        try:
            reset_feedstock_token(pkg, skips=skips)
        except Exception as e:
            print(
                "failed to reset token for '%s': %s" % (pkg, repr(e)),
                flush=True,
            )
            pkgs_to_do_again.append(pkg)

    if pkgs_to_do_again:
        request = copy.deepcopy(request)
        request["packages"] = pkgs_to_do_again
        return request
    else:
        return None


def check(request):
    assert "feedstocks" in request
    feedstocks = request["feedstocks"]
    missing_feedstocks = []

    for feedstock in feedstocks:
        r = requests.get(
            f"https://github.com/conda-forge/{feedstock}-feedstock"
        )
        if r.status_code != 200:
            missing_feedstocks.append(feedstock)

    if missing_feedstocks:
        raise RuntimeError(
            f"feedstocks {missing_feedstocks} could not be found!"
        )
