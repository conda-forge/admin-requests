"""
This script will process the `grant_access/` and `revoke_access/` requests.

Main logic lives in conda-smithy. This is just a wrapper for admin-requests infra.
"""
import sys


def check():
    "Check requests are valid (resources exist, feedstocks exist)"
    pass


def _process_request_with_conda_smithy():
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
