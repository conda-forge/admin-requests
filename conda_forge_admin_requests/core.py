import subprocess
import os
import tempfile
import requests
import copy
from conda_smithy.github import Github
import csv


def _get_core(url):
    res = requests.get(url)
    data = csv.reader(res.content.decode("utf-8").splitlines(), delimiter=',')
    return set([row[0] for row in list(data)[1:]])


def get_core():
    URL_BASE = "https://raw.githubusercontent.com/conda-forge/conda-forge.github.io/main/src/"
    return _get_core(f"{URL_BASE}/core.csv") | _get_core(f"{URL_BASE}/emeritus.csv")


def check(request):
    action = request["action"]
    assert action == "core"

    assert "github" in request
    gh_handle = request["github"]
    # TODO: check that the PR was submitted by the user

    pr_author = os.environ["GITHUB_PR_AUTHOR"]
    assert pr_author == gh_handle

    core = get_core()
    assert pr_author in core


def run(request):
    action = request.pop("action")
    assert action == "core"
    assert "github" in request

    gh_handle = request.pop("github")
    gh = Github(os.environ['GITHUB_TOKEN'])
    org = gh.get_organization("conda-forge")
    core = org.get_team_by_slug("Core")
    user = gh.get_user(gh_handle)

    assert core.has_in_members(user)

    if "heroku" in request and "HEROKU_API_KEY" in os.environ:
        heroku_email = request.pop("heroku")

        def auth_header(r):
            r.headers["Authorization"] = f"Bearer {os.environ['HEROKU_API_KEY']}"
            return r

        res = requests.post("https://api.heroku.com/apps/conda-forge/collaborators",
            data={"silent": False, "user": heroku_email},
            headers={"Accept": "application/vnd.heroku+json; version=3"},
            auth=auth_header)

        res.raise_for_status()

    if "anaconda" in request and "BINSTAR_TOKEN" in os.environ:
        anaconda_user = request.pop("anaconda")
        res = requests.post(
            f"https://api.anaconda.org/group/conda-forge/Owners/members/{anaconda_user}",
            headers={'Authorization': 'token {}'.format(os.environ["BINSTAR_TOKEN"])}
        )
        res.raise_for_status()

    return request if request else None
