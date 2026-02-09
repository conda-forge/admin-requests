import copy

import requests

from .utils import get_gh_headers, raise_json_for_status


def check(request):
    assert "feedstocks" in request
    assert "action" in request
    feedstocks = request["feedstocks"]
    task = request["action"]

    if not isinstance(feedstocks, dict):
        raise ValueError(
            "'feedstocks' must be a mapping from feedstock names to lists of branches"
        )
    if task not in ("archive_branch", "unarchive_branch"):
        raise ValueError(f"Illegal value for action: {task}")

    print(f"received map from feedstocks to branches-to-be-archived: {feedstocks!r}")
    owner = "conda-forge"
    headers = get_gh_headers()

    for feedstock, branches in feedstocks.items():
        repo = f"{feedstock}-feedstock"
        api_base_url = f"https://api.github.com/repos/{owner}/{repo}"

        r = requests.get(api_base_url, headers=headers)
        if r.status_code != 200:
            raise ValueError(f"Cannot find {owner}/{repo}!")

        if not isinstance(branches, list):
            raise ValueError(
                f"branches for '{feedstock}' must be a list, got {branches!r}"
            )

        for branch in branches:
            if branch == "main":
                raise ValueError(
                    f"{feedstock}: Task '{task}' is not allwed for 'main' branch"
                )

            if task == "archive_branch":
                # branch must exist
                r = requests.get(f"{api_base_url}/branches/{branch}", headers=headers)
                if r.status_code != 200:
                    raise ValueError(f"{feedstock}: branch '{branch}' not found")

                # tag must NOT exist
                r = requests.get(
                    f"{api_base_url}/git/ref/tags/{branch}", headers=headers
                )
                if r.status_code == 200:
                    raise ValueError(f"{feedstock}: tag '{branch}' already exists")

            elif task == "unarchive_branch":
                # tag must exist
                r = requests.get(
                    f"{api_base_url}/git/ref/tags/{branch}", headers=headers
                )
                if r.status_code != 200:
                    raise ValueError(f"{feedstock}: tag '{branch}' not found")

                # branch must NOT exist
                r = requests.get(f"{api_base_url}/branches/{branch}", headers=headers)
                if r.status_code == 200:
                    raise ValueError(f"{feedstock}: branch '{branch}' already exists")


def _archive_branch(owner, repo, branch, headers):
    api_base_url = f"https://api.github.com/repos/{owner}/{repo}"

    # get SHA of last commit on branch
    r = requests.get(f"{api_base_url}/branches/{branch}", headers=headers)
    raise_json_for_status(r)
    sha = r.json()["commit"]["sha"]

    # create tag
    r = requests.post(
        f"{api_base_url}/git/refs",
        headers=headers,
        json={"ref": f"refs/tags/{branch}", "sha": sha},
    )
    raise_json_for_status(r)

    # delete branch
    r = requests.delete(f"{api_base_url}/git/refs/heads/{branch}", headers=headers)
    raise_json_for_status(r)

    print(f"{repo}: archived branch '{branch}' as tag '{branch}'", flush=True)


def _unarchive_branch(owner, repo, branch, headers):
    api_base_url = f"https://api.github.com/repos/{owner}/{repo}"

    # get SHA of tag
    r = requests.get(f"{api_base_url}/git/ref/tags/{branch}", headers=headers)
    raise_json_for_status(r)
    sha = r.json()["object"]["sha"]

    # create branch
    r = requests.post(
        f"{api_base_url}/git/refs",
        headers=headers,
        json={"ref": f"refs/heads/{branch}", "sha": sha},
    )
    raise_json_for_status(r)

    # delete tag
    r = requests.delete(f"{api_base_url}/git/refs/tags/{branch}", headers=headers)
    raise_json_for_status(r)

    print(f"{repo}: restored branch '{branch}' from tag '{branch}'", flush=True)


def run(request):
    check(request)

    task = request["action"]
    owner = "conda-forge"
    headers = get_gh_headers()

    failed_feedstocks = {}

    for feedstock, branches in request["feedstocks"].items():
        repo = f"{feedstock}-feedstock"
        failed_branches = []

        for branch in branches:
            try:
                if task == "archive_branch":
                    _archive_branch(owner, repo, branch, headers)
                else:
                    _unarchive_branch(owner, repo, branch, headers)
            except Exception as e:
                print(
                    f"failed to {task} branch '{branch}' on '{feedstock}': {e!r}",
                    flush=True,
                )
                failed_branches.append(branch)

        if failed_branches:
            failed_feedstocks[feedstock] = failed_branches

    if failed_feedstocks:
        request = copy.deepcopy(request)
        request["feedstocks"] = failed_feedstocks
        return request
    else:
        return None
