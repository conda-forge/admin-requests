"""
This script will process the `travis` and `cirun` requests.

Main logic lives in conda-smithy. This is just a wrapper for admin-requests infra.
"""
import os
import subprocess
import tempfile
import time
from typing import Dict, List, Any
import textwrap
import copy
from unittest import mock

import requests

from .utils import write_secrets_to_files

from conda_smithy.utils import update_conda_forge_config
from conda_smithy.github import Github, gh_token


GH_ORG = os.environ.get("GH_ORG", "conda-forge")

DEFAULT_CIRUN_OPENSTACK_VALUES = {
    "cirun_roles": ["admin", "maintain", "write"],
    "cirun_users_from_json": ["https://raw.githubusercontent.com/Quansight/open-gpu-server/main/access/conda-forge-users.json"]
}


def send_pr_cirun(
    feedstock: str,
    feedstock_dir: str,
    resources: List[str],
    pull_request: bool,
) -> None:
    """
    Send PR to feedstock to enable Github Actions with Cirun

    Parameters:
    feedstock (str): The name of the feedstock.
    feedstock_dir (str): Path to a git checkout of the feedstock.
    resources (List[str]): The names of the resources for access control.
    pull_request (bool): Whether to allow Pull Requests.
    """

    with update_conda_forge_config(
            os.path.join(
                feedstock_dir,
                "recipe",
                "conda_build_config.yaml")) as cbc, \
            update_conda_forge_config(
                os.path.join(feedstock_dir, "conda-forge.yml")) as cfg:
        if any(label.startwith("cirun-") for label in cbc.get(
                "github_actions_labels", [])):
            return
        cfg["github_actions"] = {"self_hosted": True}
        if pull_request:
            cfg["github_actions"]["triggers"] = ["push", "pull_request"]
        if "provider" not in cfg:
            cfg["provider"] = {}
        cfg["provider"]["linux_64"] = "github_actions"
        cbc["github_actions_labels"] = resources

    gh = Github(os.environ['GITHUB_TOKEN'])
    user = gh.get_user()

    repo = gh.get_repo(f"{GH_ORG}/{feedstock}")
    repo.create_fork()

    base_branch = f"cirun-{int(time.time())}"

    resource_str = ", ".join(resources)

    git_cmds = [
        "git add recipe/conda_build_config.yaml conda-forge.yml",
        f"git remote add {user.login} https://x-access-token:${{GITHUB_TOKEN}}@github.com/"
        f"{user.login}/{feedstock}.git",
        f"git commit -m 'Enable {resource_str} using Cirun' --author '{user.name} <{user.email}>'",
        "conda-smithy rerender -c auto --no-check-uptodate",
        f"git push {user.login} HEAD:{base_branch}",
    ]
    for git_cmd in git_cmds:
        print("Running:", git_cmd, " in ", feedstock_dir)
        subprocess.check_call(git_cmd, shell=True, cwd=feedstock_dir)

    print("Creating PR:")
    repo.create_pull(
        base="main",
        head=f"{user.login}:{base_branch}",
        title=f"Update feedstock to use {resource_str} with Cirun",
        body=textwrap.dedent("""
        Note that only builds triggered by maintainers of the feedstock (and core)
        who have accepted the terms of service and privacy policy will run
        on Github actions via Cirun.
        - [ ] Maintainers have accepted the terms of service and privacy policy
          at https://github.com/Quansight/open-gpu-server

        Also, note that rerendering with Github actions as CI provider must be done
        locally in the future for this feedstock.
        """),
    )


def _process_request_for_feedstock(
    feedstock: str,
    action: str,
    resources: List[str] = None,
    revoke: bool = False,
    pull_request: bool = False,
    send_pr: bool = True,
) -> None:
    """
    Process the access control request for a single feedstock.

    Parameters:
    feedstock (str): The name of the feedstock.
    resources (List[str]): The names of the resources for access control.
    revoke (bool): Whether to remove the access control.
    pull_request (bool): Whether to allow PRs for resource.
    """

    # We need a token with admin permissions for Cirun
    with tempfile.TemporaryDirectory() as tmp_dir, \
            mock.patch.dict('os.environ', {'GITHUB_TOKEN': os.environ['GITHUB_ADMIN_TOKEN']}):
        feedstock_dir = os.path.join(tmp_dir, feedstock)
        assert GH_ORG
        clone_cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            f"https://github.com/{GH_ORG}/{feedstock}.git",
            feedstock_dir,
        ]
        print("Cloning:", *clone_cmd)
        subprocess.check_call(clone_cmd)

        owner_info = ["--organization", GH_ORG]
        token_repo = (
            'https://x-access-token:${GITHUB_TOKEN}@github.com/'
            f'{GH_ORG}/feedstock-tokens'
        )

        register_ci_cmd = [
            "conda-smithy",
            "register-ci",
            "--feedstock_dir",
            feedstock_dir,
            "--without-all",
            "--without-anaconda-token",
            *owner_info,
        ]
        if action == "travis":
            register_ci_cmd.append("--with-travis")

        elif action == "cirun":
            register_ci_cmd.append("--with-cirun")

            for resource in resources:
                register_ci_cmd.extend(["--cirun-resources", resource])
                assert resource.startswith("cirun-openstack"), f"Unknown resource {resource}"

            if all(resource.startswith("cirun-openstack") for resource in resources):
                for key, value in DEFAULT_CIRUN_OPENSTACK_VALUES.items():
                    for arg in value:
                        register_ci_cmd.extend((f"--{key.replace('_', '-')}", arg))
            else:
                assert False, f"Unknown resources {resources}"

            if pull_request:
                register_ci_cmd.extend(("--cirun-policy-args", "pull_request"))

            if revoke:
                register_ci_cmd.append("--remove")

        print("Register-CI command:", *register_ci_cmd)
        subprocess.check_call(register_ci_cmd)

        if not revoke:
            if action == "travis":
                with_cmd = "--with-travis"
            elif action == "cirun":
                with_cmd = "--with-github-actions"

            print("Generating a new feedstock token")
            subprocess.check_call(
                [
                    'conda', 'smithy', 'generate-feedstock-token',
                    '--unique-token-per-provider',
                    '--feedstock_directory', feedstock_dir,
                    *owner_info,
                ]
            )

            print("Register new feedstock token with provider and feedstock-tokens repo.")
            subprocess.check_call(
                [
                    'conda', 'smithy', 'register-feedstock-token',
                    '--unique-token-per-provider',
                    '--feedstock_directory', feedstock_dir,
                    '--without-all', with_cmd,
                    *owner_info,
                    '--token_repo', token_repo,
                ]
            )

            if action == "travis":
                print("Add STAGING_BINSTAR_TOKEN to travis")
                subprocess.check_call(
                    [
                        'conda', 'smithy', 'rotate-binstar-token',
                        '--feedstock_directory', feedstock_dir,
                        '--without-all', with_cmd,
                        *owner_info,
                        '--token_name', 'STAGING_BINSTAR_TOKEN',
                    ]
                )

            if action == "cirun" and send_pr:
                print("Sending PR to feedstock")
                send_pr_cirun(feedstock, feedstock_dir, resources, pull_request)


def check_if_repo_exists(feedstock_name: str) -> None:
    """
    Check if a repository exists on GitHub.

    Parameters:
    feedstock_name (str): The name of the feedstock to check.

    Raises:
    ValueError: If the repository does not exist on GitHub.
    """
    repo = f"{feedstock_name}-feedstock"
    owner_repo = f"{GH_ORG}/{repo}"
    print(f"Checking if {owner_repo} exists")
    response = requests.get(f"https://api.github.com/repos/{owner_repo}")
    if response.status_code != 200:
        raise ValueError(f"Repository: {owner_repo} not found!")


def check(request: Dict[str, Any]) -> None:
    """Check if the access control requests in both 'grant_access'
    and 'revoke_access' directories are valid."""
    print("Checking access control request")
    assert "feedstocks" in request
    feedstocks = request["feedstocks"]
    for feedstock in feedstocks:
        check_if_repo_exists(feedstock)

    action = request["action"]
    assert action in ("travis", "cirun"), f"Unknown action {action}"

    if action == "cirun":
        assert "resources" in request, "No resources field in request"
        resources = request["resources"]
        assert resources, "Empty resources"
        for resource in resources:
            assert resource.startswith("cirun-openstack")

    if action == "travis":
        assert not request.get("revoke", False)


def run(request: Dict[str, Any]) -> None:
    """
    The main function to process the access control requests. It performs the following steps:
    1. Check if the requests are valid.
    2. Process the access control requests.
    """
    check(request)
    write_secrets_to_files()

    feedstocks = request["feedstocks"]
    for feedstock in feedstocks:
        request_copy = copy.deepcopy(request)
        del request_copy["feedstocks"]
        _process_request_for_feedstock(f"{feedstock}-feedstock", **request_copy)
