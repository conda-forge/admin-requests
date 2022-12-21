import os
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
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Accept": "application/vnd.github+json",
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


def feedstocks(directory="archive"):
    for path in Path(directory).glob("*.txt"):
        if path.name == "example.txt":
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    yield line


def main(owner="conda-forge", check_only=False):
    for feedstock in feedstocks("archive"):
        print(f"Archiving {owner}/{feedstock}-feedstock...")
        archive_repo(owner, f"{feedstock}-feedstock", archive=True, check_only=check_only)
        time.sleep(0.5)
    for feedstock in feedstocks("unarchive"):
        print(f"Unarchiving {owner}/{feedstock}-feedstock...")
        archive_repo(owner, f"{feedstock}-feedstock", archive=False, check_only=check_only)
        time.sleep(0.5)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python archive_feedstock.py [check | archive]")
    check_only = sys.argv[1] == "check"
    main(owner="conda-forge", check_only=check_only)
