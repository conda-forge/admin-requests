"""
This script will process the `grant_access/` and `revoke_access/` requests.

Main logic lives in conda-smithy. This is just a wrapper for admin-requests infra.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests
from ruamel.yaml import YAML
from typing import List, Dict, Tuple, Optional, Union, Any


from pydantic import BaseModel, Field, RootModel


GH_ORG = os.environ.get("GH_ORG", "conda-forge")

# This is a mapping for the filename in {grant,revoke}_access/<name>.txt
# to the cirun resource configuration
# The schema for resource configuration is:
# {
#    "resource": "<cirun-resource-name>"
#    "policy_args": "List[<policy-args>]"
# }
# policy_args can only contain "pull_request at the moment"
CIRUN_FILENAME_RESOURCE_MAPPING = {
    "cirun-gpu-runner": {
        "resource": "cirun-gpu-runner",
    },
    "cirun-gpu-runner-pr": {
        "resource": "cirun-gpu-runner",
        "policy_args": ["pull_request"],
    },
}

ACCESS_YAML_FILENAME = ".access_control.yml"


class AccessControlItem(BaseModel):
    feedstock: str


class AccessControl(RootModel):
    root: Dict[str, Union[List[AccessControlItem], None]]


class AccessControlConfig(BaseModel):
    version: int
    access_control: AccessControl


def _get_input_access_control_files(path: str) -> List[Path]:
    """
    Get a list of input access control files from a specified directory.

    Parameters:
    path (str): The path to the directory containing the access control files.

    Returns:
    List[Path]: A list of paths to the access control files in the specified directory.
    """
    access_path = Path(path)
    all_files = list(access_path.glob("*"))
    return [f for f in all_files if f.parts[-1] != "example.txt"]


def _get_filename_feedstock_mapping(path: str) -> Dict[str, List[str]]:
    """
    Get a mapping from filename to a list of feedstocks in that file from
    the input access control files.

    Parameters:
    path (str): The path to the directory containing the access control files.

    Returns:
    Dict[str, List[str]]: A dictionary mapping from filename to a list of feedstocks.
    """
    access_files = _get_input_access_control_files(path)
    file_name_feedstock_mapping = {}
    for file_path in access_files:
        file_name, feedstocks = parse_an_input_file(file_path)
        file_name_feedstock_mapping[file_name] = feedstocks
    return file_name_feedstock_mapping


def parse_an_input_file(file_path: Path) -> Tuple[str, List[str]]:
    """
    Parse an input access control file and get the filename and the list of feedstocks.

    Parameters:
    file_path (Path): The path to the input access control file.

    Returns:
    Tuple[str, List[str]]: A tuple containing the filename and the list of feedstocks.
    """
    with open(file_path, "r") as f:
        feedstocks = f.readlines()
        feedstocks = [feedstock.strip() for feedstock in feedstocks]
        file_name = file_path.parts[-1].strip(".txt")
        return file_name, feedstocks


def _process_access_control_requests(path: str, remove: bool = False) -> None:
    """
    Process the access control requests by processing each feedstock found in
    the access control files.

    Parameters:
    path (str): The path to the directory containing the access control files.
    remove (bool, optional): Whether to remove (revoke) access to resource.
    Defaults to False.
    """
    print(f"Processing access control requests for {path}")
    grant_access_request = _get_filename_feedstock_mapping(path)
    for filename, feedstocks in grant_access_request.items():
        if filename in CIRUN_FILENAME_RESOURCE_MAPPING:
            resource_mapping = CIRUN_FILENAME_RESOURCE_MAPPING.get(filename)
            resource = resource_mapping["resource"]
            policy_args = resource_mapping.get("policy_args")
            for feedstock in feedstocks:
                feedstock_repo = f"{feedstock}-feedstock"
                print(f"Processing feedstock for access control: {feedstock_repo}")
                _process_request_for_feedstock(
                    feedstock_repo, resource, remove=remove, policy_args=policy_args
                )
                action = "remove" if remove else "add"
                update_access_yaml(resource, feedstock_repo, action=action)


def process_access_control_requests() -> None:
    """Process access control requests from both 'grant_access' and
    'revoke_access' directories.
    """
    print("Processing access control request")
    _process_access_control_requests("grant_access", remove=False)
    _process_access_control_requests("revoke_access", remove=True)


def _process_request_for_feedstock(
    feedstock: str, resource: str, remove: bool, policy_args: Optional[List[str]] = None
) -> None:
    """
    Process the access control request for a single feedstock.

    Parameters:
    feedstock (str): The name of the feedstock.
    resource (str): The name of the resource for access control.
    remove (bool): Whether to remove the access control.
    policy_args (List[str]): A list of policy arguments.
    """
    with tempfile.TemporaryDirectory() as feedstock_clone_path:
        assert GH_ORG
        clone_cmd = f"git clone --depth 1 https://github.com/{GH_ORG}/{feedstock}.git {feedstock_clone_path}"
        print(f"Cloning: {clone_cmd}")
        subprocess.run(clone_cmd, shell=True)

        register_ci_cmd = [
            "conda-smithy register-ci",
            f"--organization {GH_ORG}",
            "--without-azure",
            "--without-travis",
            "--without-circle",
            "--without-appveyor",
            "--without-drone",
            "--without-webservice",
            "--without-anaconda-token",
            f"--feedstock_directory {feedstock_clone_path}",
            f"--cirun-resources {resource}",
        ]

        if policy_args:
            policy_args_param = [f"--cirun-policy-args {arg}" for arg in policy_args]
            register_ci_cmd.extend(policy_args_param)
        if remove:
            register_ci_cmd.append("--remove")

        register_ci_cmd_str = " ".join(register_ci_cmd)
        print(f"RegisterCI command: {register_ci_cmd_str}")
        subprocess.check_call(register_ci_cmd_str, shell=True)


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


def _check_for_path(path: str) -> None:
    """
    Check if the path contains valid access control requests by checking the filename and feedstock existence.

    Parameters:
    path (str): The path to the directory containing the access control files.
    """
    mapping = _get_filename_feedstock_mapping(path)
    for filename, feedstocks in mapping.items():
        print(f"Checking if {filename} is in {CIRUN_FILENAME_RESOURCE_MAPPING.keys()}")
        assert filename in CIRUN_FILENAME_RESOURCE_MAPPING
        for feedstock in feedstocks:
            check_if_repo_exists(feedstock)
    if not mapping:
        print(f"Nothing to check for: {path}")


def check() -> None:
    """Check if the access control requests in both 'grant_access' and 'revoke_access' directories are valid."""
    print("Checking access control request")
    _check_for_path("grant_access")
    _check_for_path("revoke_access")


def _commit_after_files_removal(push: bool = True) -> None:
    """
    Commit the changes to the repository after removing files.

    Parameters:
    push (bool, optional): Whether to push the changes to the repository. Defaults to True.
    """
    print("Committing the changes")
    subprocess.run(["git", "add", "grant_access", "revoke_access"], check=True)
    subprocess.run(
        ["git", "commit", "-m", "Processed access control requests"], check=True
    )
    if push:
        subprocess.run(["git", "push"], check=True)


def _remove_input_files(dir: str, file_to_keep: str) -> None:
    """
    Remove input files from a directory, excluding a specific file.

    Parameters:
    dir (str): The directory from which to remove the files.
    file_to_keep (str): The filename of the file to keep in the directory.

    Raises:
    ValueError: If the specified path is not a directory.
    """
    print("Removing input files")
    directory = Path(dir)
    files_to_keep = [Path(file_to_keep)]
    if not directory.is_dir():
        raise ValueError("The specified path is not a directory.")

    for file in directory.iterdir():
        if file.is_file() and file not in files_to_keep:
            print(f"Removing input file: {file}")
            file.unlink()
    _commit_after_files_removal(push=False)


def update_access_yaml(
    resource: str,
    feedstock_name: str,
    action: str,
    filename: str = ACCESS_YAML_FILENAME,
) -> None:
    """
    Manage feedstock in .access_control.yml.

    Parameters:
    - resource: the access control resource (e.g., "travis", "cirun-gpu-small").
    - feedstock_name: the name of the feedstock.
    - action: either "add" or "remove".
    - filename: the name of the YAML file.
    """
    print(f"Updating {filename}")
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)  # Indent settings for 2-space mapping

    with open(filename, "r") as f:
        content = yaml.load(f)

    # If resource doesn't exist, create it
    if resource not in content["access_control"]:
        content["access_control"][resource] = []

    if action == "add":
        # Check if feedstock already exists
        if any(
            entry["feedstock"] == feedstock_name
            for entry in content["access_control"][resource]
        ):
            print(
                f"Feedstock {feedstock_name} already exists under {resource}. Skipping addition."
            )
            return

        entry = {"feedstock": feedstock_name}
        content["access_control"][resource].append(entry)

    elif action == "remove":
        if not content["access_control"][resource]:
            raise ValueError(f"No feedstock found under resource {resource}.")
        content["access_control"][resource] = [
            entry
            for entry in content["access_control"][resource]
            if entry["feedstock"] != feedstock_name
        ]

    else:
        raise ValueError(f"Invalid action {action}. Choose 'add' or 'remove'.")

    # Validate access control config
    AccessControlConfig.model_validate(content)
    with open(filename, "w") as f:
        yaml.dump(content, f)


def main() -> None:
    """
    The main function to process the access control requests. It performs the following steps:
    1. Check if the requests are valid.
    2. Process the access control requests.
    3. Remove the processed files from the 'grant_access' and 'revoke_access' directories.
    4. Commit the changes to the repository.
    """
    check()
    process_access_control_requests()
    _remove_input_files("grant_access/", file_to_keep="grant_access/example.txt")
    _remove_input_files("revoke_access/", file_to_keep="revoke_access/example.txt")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and "check" in sys.argv:
        sys.exit(check())
    sys.exit(main())
