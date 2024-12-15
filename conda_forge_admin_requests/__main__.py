import os
import glob
import yaml
import sys
import subprocess
from conda_forge_admin_requests import get_actions, register_actions

def _get_task_files():
    return (
        list(glob.glob(os.path.join("requests", "*.yml")))
        + list(glob.glob(os.path.join("requests", "*.yaml")))
    )


def check():
    # error if people put thinks in old places
    old_files = glob.glob("broken/*")
    if old_files:
        assert False, (
            f"Found old files ({old_files}) in wrong location. "
            "Please put YAML-formatted requests in the `requests` directory."
        )

    if not all(
        fname.endswith(".yaml") or fname.endswith(".yml")
        for fname in glob.glob("requests/*")
    ):
        assert False, (
            "Found non-YAML files in the `requests` directory. Please "
            "use only YAML-formatted requests with filename extensions "
            "`.yml` or `.yaml`."
        )

    filenames = _get_task_files()

    for filename in filenames:
        with open(filename) as f:
            request = yaml.safe_load(f)

        assert "action" in request, f"Invalid request: {request}"

        action = request["action"]
        actions = get_actions()

        if action not in actions:
            assert False, f"Unknown action: {action}"

        getattr(actions[action], "check")(request)


def run():
    filenames = _get_task_files()

    for filename in filenames:
        with open(filename) as f:
            request = yaml.safe_load(f)

        assert "action" in request, f"Invalid request: {request}"

        action = request["action"]
        actions = get_actions()

        if action not in actions:
            assert False, f"Unknown action: {action}"

        try_again = getattr(actions[action], "run")(request)

        if try_again:
            with open(filename, "w") as fp:
                yaml.dump(try_again, fp)
            subprocess.check_call(["git", "add", filename])
            subprocess.check_call(
                [
                    "git",
                    "commit",
                    "--allow-empty",
                    "-m",
                    f"Keeping {filename} after failed {action}",
                ]
            )
        else:
            subprocess.check_call(["git", "rm", filename])
            subprocess.check_call(
                ["git", "commit", "-m", f"Remove {filename} after {action}"]
            )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m conda_forge_admin_requests [check | run]")

    register_actions()
    check_only = sys.argv[1] == "check"

    if check_only:
        check()
    else:
        run()

