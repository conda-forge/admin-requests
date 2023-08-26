"""
This script will process the `grant_access/` and `revoke_access/` requests.

Main logic lives in conda-smithy. This is just a wrapper for admin-requests infra.
"""
import os
import subprocess
import sys
from pathlib import Path


GH_ORG = os.environ.get("GH_ORG", "conda-forge")

CIRUN_FILENAME_RESOURCE_MAPPING = {
    "cirun-gpu-runner": {
        "resource": "cirun-gpu-runner",
    },
    "cirun-gpu-runner-pr": {
        "resource": "cirun-gpu-runner",
        "policy_args": ["pull_request"]
    }
}


def _get_access_control_files(path):
    access_path = Path(path)
    all_files = list(access_path.glob("*"))
    return (
        [f for f in all_files if f.parts[-1] != "example.txt"]
    )


def _get_filename_feedstock_mapping(path):
    access_files = _get_access_control_files(path)
    file_name_feedstock_mapping = {}
    for file_path in access_files:
        with open(file_path, "r") as f:
            feedstocks = f.readlines()
            feedstocks = [feedstock.strip() for feedstock in feedstocks]
            file_name = file_path.parts[-1].strip(".txt")
            file_name_feedstock_mapping[file_name] = feedstocks
    return file_name_feedstock_mapping


def _process_access_control_requests(path, remove=True):
    print(f"Processing access control requests for {path}")
    grant_access_request = _get_filename_feedstock_mapping(path)
    for filename, feedstocks in grant_access_request.items():
        if filename in CIRUN_FILENAME_RESOURCE_MAPPING:
            resource_mapping = CIRUN_FILENAME_RESOURCE_MAPPING.get(filename)
            resource = resource_mapping.get("resource")
            policy_args = resource_mapping.get("policy_args")
            for feedstock in feedstocks:
                print(f"Processing feedstock for access control: {feedstock}")
                _process_request_for_feedstock(
                    feedstock, resource, remove=remove, policy_args=policy_args
                )


def process_access_control_requests():
    """Process access control requests"""
    print("Processing access control request")
    _process_access_control_requests("grant_access", remove=False)
    _process_access_control_requests("revoke_access")


def _process_request_for_feedstock(feedstock, resource, remove, policy_args):
    feedstock_clone_path = f"/tmp/{feedstock}"
    path = Path(feedstock_clone_path)
    if not path.exists():
         subprocess.run(
            f"git clone --depth 1 https://github.com/{GH_ORG}/{feedstock} {feedstock_clone_path}",
            shell=True,
        )


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
    subprocess.check_call(register_ci_cmd_str,
        shell=True,
    )


def check():
    """Check requests are valid (resources exist, feedstocks exist)"""
    pass


def _commit_after_files_removal(push=True):
    subprocess.check_call(
        "git add .",
        shell=True,
    )

    subprocess.check_call(
            "git commit --allow-empty -am 'Remove access control files'",
            shell=True,
        )
    if push:
        subprocess.check_call(
            "git push",
            shell=True,
        )


def _remove_input_files(dir, file_to_keep):
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


def main():
    """Process requests"""
    check()  # doesn't hurt
    process_access_control_requests()
    _remove_input_files("grant_access/", file_to_keep="grant_access/example.txt")
    _remove_input_files("revoke_access/", file_to_keep="revoke_access/example.txt")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and "check" in sys.argv:
        sys.exit(check())
    sys.exit(main())
