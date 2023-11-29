import os
import glob
import yaml
import sys

from . import archive_feedstock as archive, mark_broken, token_reset


def get_task_files():
    return list(glob.glob(os.path.join("examples", "*.yml")))


def check():
    filenames = get_task_files()
    
    for filename in filenames:
        with open(filename) as f:
            request = yaml.safe_load(f) 

        assert "action" in request

        action = request["action"]

        if action in ("archive", "unarchive"):
            archive.check(request)
        elif action in ("broken", "not_broken"):
            mark_broken.check(request)
        elif action in ("token_reset"):
            token_reset.check(request)


def run():
    filenames = get_task_files()
    
    for filename in filenames:
        with open(filename) as f:
            request = yaml.safe_load(f) 

        assert "action" in request

        action = request["action"]

        if action in ("archive", "unarchive"):
            try_again = archive.run(request)
        elif action in ("broken", "not_broken"):
            try_again = mark_broken.run(request)

        if try_again:
            with open(filename, "w") as fp:
                yaml.dump(request, try_again)
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

