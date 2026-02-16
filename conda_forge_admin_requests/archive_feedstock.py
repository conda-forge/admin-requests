import subprocess

import requests

from .utils import get_gh_headers, raise_json_for_status


def process_repo(repo, task):
    owner = "conda-forge"
    headers = get_gh_headers()

    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
    )
    raise_json_for_status(r)

    if task == "archive":
        target_status = "archived"
    else:
        target_status = "unarchived"

    data = r.json()
    if task == "archive" and data["archived"]:
        print(f"feedstock {repo} is already {target_status}", flush=True)
        return

    if task == "unarchive" and not data["archived"]:
        print(f"feedstock {repo} is already {target_status}", flush=True)
        return

    r = requests.patch(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        json={"archived": task == "archive"},
    )
    raise_json_for_status(r)

    print(f"feedstock {repo} was {target_status}", flush=True)


def run(request):
    feedstocks = request["feedstocks"]
    task = request["action"]

    pkgs_to_do_again = []
    for feedstock in feedstocks:
        try:
            process_repo(f"{feedstock}-feedstock", task)
        except Exception as e:
            print(f"failed to {task} '{feedstock}': {e!r}", flush=True)
            pkgs_to_do_again.append(feedstock)

    if pkgs_to_do_again:
        request["feedstocks"] = pkgs_to_do_again

    subprocess.check_call(["git", "show"])


def check(request):
    assert "feedstocks" in request

    missing_feedstocks = []

    for feedstock in request["feedstocks"]:
        r = requests.get(f"https://github.com/conda-forge/{feedstock}-feedstock")
        if r.status_code != 200:
            missing_feedstocks.append(feedstock)

    if missing_feedstocks:
        raise RuntimeError(
            f"{list(set(missing_feedstocks))} feedstocks could not be found!"
        )
