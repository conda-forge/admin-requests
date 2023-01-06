import os
import subprocess
import sys
import time
from pathlib import Path

import requests


def raise_json_for_status(request):
    try:
        request.raise_for_status()
    except Exception as exc:
        exc.args = exc.args + (request.json(), )
        raise exc.with_traceback(exc.__traceback__)


def archive_repo(owner, repo, archive=True, check_only=False):
    headers = {
        "X-GitHub-Api-Version": "2022-11-28",
        "Accept": "application/vnd.github+json",
        "User-Agent": "conda-forge/admin-requests",
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    }

    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
    )
    raise_json_for_status(r)

    target_status = f"{'' if archive else 'un'}archived"
    data = r.json()
    if data["archived"] == archive:
        raise RuntimeError(f"{owner}/{repo} is already {target_status}!")
    elif check_only:
        return

    r = requests.patch(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        json={"archived": archive}
    )
    raise_json_for_status(r)


def feedstocks(directory="archive", check_only=False):
    for path in Path(directory).glob("*.txt"):
        if path.name == "example.txt":
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    yield line
        if not check_only:
            subprocess.check_call(f"git rm {file_name}", shell=True)
            subprocess.check_call(
                (
                    "git commit -m "
                    f"'Remove {file_name} after {directory[:-1]}ing repos'"
                ),
                shell=True
            )
            subprocess.check_call("git show", shell=True)



def main(owner="conda-forge", check_only=False):
    exceptions = []
    for task in "archive", "unarchive":
        seen = set()
        for feedstock in feedstocks(task, check_only=check_only):
            verb = "Archiving" if task == "archive" else "Unarchiving"
            print(f"{verb} {owner}/{feedstock}-feedstock...", end=" ")
            if feedstock in seen:
                print("[SKIP]")
                continue
            seen.add(feedstock.lower())
            try:
                archive_repo(owner, f"{feedstock}-feedstock", archive=task == "archive", check_only=check_only)
            except Exception as exc:
                exceptions.append((feedstock, exc))
                print("[!!]")
            else:
                print("[OK]")
            time.sleep(0.5)
    if exceptions:
        raise Exception(*exceptions)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python archive_feedstock.py [check | archive]")
    check_only = sys.argv[1] == "check"
    main(owner="conda-forge", check_only=check_only)
