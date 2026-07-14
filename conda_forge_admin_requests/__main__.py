import glob
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import yaml

from conda_forge_admin_requests import get_actions, register_actions


def _get_task_files():
    return list(glob.glob(os.path.join("requests", "*.yml"))) + list(
        glob.glob(os.path.join("requests", "*.yaml"))
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

    if any(
        not fname.startswith("examples/example-") for fname in glob.glob("examples/*")
    ):
        assert False, (
            "Found non-example files in the `examples` directory. Please "
            "make sure you put your requests in the `requests` directory."
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

    failing_filenames_to_raise = []
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
            if subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0:
                # Only commit if there are changes
                subprocess.check_call(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"Keeping {filename} after failed {action}",
                    ]
                )
            else:
                # How old is this failing file? Raise issue after 6h
                added_at = subprocess.check_output(
                    [
                        "git",
                        "log",
                        "--diff-filter=A",
                        "-1",
                        "--format=%aI",
                        "--",
                        filename,
                    ],
                    text=True,
                ).strip()
                if added_at:
                    added_at_dt = datetime.fromisoformat(added_at)
                    if datetime.now(tz=timezone.utc) - added_at_dt > timedelta(hours=6):
                        failing_filenames_to_raise.append(filename)
                else:
                    print(
                        "::error::No timestamp information for",
                        filename,
                        file=sys.stderr,
                    )
        else:
            subprocess.check_call(["git", "rm", filename])
            subprocess.check_call(
                ["git", "commit", "-m", f"Remove {filename} after {action}"]
            )
    if failing_filenames_to_raise:
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(
                f"FAILING_FILENAMES_TO_RAISE={' '.join(failing_filenames_to_raise)}\n"
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
