import os
import requests
import subprocess


def raise_json_for_status(request):
    try:
        request.raise_for_status()
    except Exception as exc:
        exc.args = exc.args + (request.json(), )
        raise exc.with_traceback(exc.__traceback__)


def process_repo(repo, task):
    owner = "conda-forge"
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

    if task == "archive":
        target_status = "archived"
    else:
        target_status = "unarchived"

    data = r.json()
    if task == "archive" and data["archived"]:
        print("feedstock %s is already %s" % (repo, target_status), flush=True)
        return

    if task == "unarchive" and not data["archived"]:
        print("feedstock %s is already %s" % (repo, target_status), flush=True)
        return

    r = requests.patch(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        json={"archived": task == "archive"}
    )
    raise_json_for_status(r)

    print("feedstock %s was %s" % (repo, target_status), flush=True)


def run(request):
    feedstocks = request["feedstocks"]
    task = request["action"]

    pkgs_to_do_again = []
    for feedstock in feedstocks:
        try:
            process_repo(f"{feedstock}-feedstock", task)
        except Exception as e:
            print(
                "failed to %s '%s': %s" % (task, feedstock, repr(e)),
                flush=True,
            )
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
            "feedstocks %s could not be found!" % list(set(missing_feedstocks))
        )
