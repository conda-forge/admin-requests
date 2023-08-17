"""
This script will process the `grant_access/` and `revoke_access/` requests.

Main logic lives in conda-smithy. This is just a wrapper for admin-requests infra.
"""
import sys
from pathlib import Path


def _get_access_control_files(path):
    access_path = Path(path)
    all_files = list(access_path.glob("*"))
    return (
        [f for f in all_files if f.parts[-1] != "example.txt"]
    )


def get_filename_feedstock_mapping(path):
    access_files = _get_access_control_files(path)
    file_name_feedstock_mapping = {}
    for file_path in access_files:
        with open(file_path, "r") as f:
            feedstocks = f.readlines()
            feedstocks = [feedstock.strip() for feedstock in feedstocks]
            file_name = file_path.parts[-1]
            file_name_feedstock_mapping[file_name] = feedstocks
    return file_name_feedstock_mapping


def check():
    "Check requests are valid (resources exist, feedstocks exist)"
    pass


def _update_access_control_yml():
    pass


def _remove_input_files():
    pass



def main():
    "Process requests"
    check()  # doesn't hurt
    _process_request_with_conda_smithy()
    _update_access_control_yml()
    _remove_input_files()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and "check" in sys.argv:
        sys.exit(check())
    sys.exit(main())
