import os
import glob
import yaml
import sys
import subprocess

from . import archive_feedstock as archive, mark_broken, token_reset, access_control, core


def get_task_files():
    return list(glob.glob(os.path.join("requests", "*.yml")))


def check():
    filenames = get_task_files()

    for filename in filenames:
        with open(filename) as f:
            request = yaml.safe_load(f)

        assert "action" in request, f"Invalid request: {request}"

        action = request["action"]

        if action in ("archive", "unarchive"):
            archive.check(request)
        elif action in ("broken", "not_broken"):
            mark_broken.check(request)
        elif action == "token_reset":
            token_reset.check(request)
        elif action == "core":
            core.check(request)
        elif action in ("travis", "cirun"):
            access_control.check(request)
        else:
            assert False, f"Unknown action: {action}"


def run():
    filenames = get_task_files()

    for filename in filenames:
        with open(filename) as f:
            request = yaml.safe_load(f)

        assert "action" in request, f"Invalid request: {request}"

        action = request["action"]

        if action in ("archive", "unarchive"):
            try_again = archive.run(request)
        elif action in ("broken", "not_broken"):
            try_again = mark_broken.run(request)
        elif action == "token_reset":
            try_again = token_reset.run(request)
        elif action == "core":
            try_again = core.run(request)
        elif action in ("travis", "cirun"):
            try_again = access_control.run(request)
        else:
            assert False, f"Unknown action: {action}"

        if try_again:
            with open(filename, "w") as fp:
                yaml.dump(try_again, fp)
            subprocess.check_call(f"git add {filename}", shell=True)
            subprocess.check_call(
                f"git commit --allow-empty -m 'Keeping {filename} "
                f"after failed {action}'",
                shell=True,
            )
        else:
            subprocess.check_call(f"git rm {filename}", shell=True)
            subprocess.check_call(
                f"git commit -m 'Remove {filename} after {action}'",
                shell=True,
            )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m conda_forge_admin_requests [check | run]")
    check_only = sys.argv[1] == "check"

    if check_only:
        check()
    else:
        run()

