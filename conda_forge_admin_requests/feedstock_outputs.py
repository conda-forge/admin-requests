import io
import json
import os
import requests

import ruamel.yaml
from conda_forge_metadata.feedstock_outputs import sharded_path as _get_sharded_path
import github


def _test_and_raise_besides_file_not_exists(e: github.GithubException):
    if isinstance(e, github.UnknownObjectException):
        return
    if e.status == 404 and "No object found" in e.data["message"]:
        return
    raise e


def _add_feedstock_output(
    feedstock,
    pkg_name,
):
    gh_token = os.environ['GITHUB_TOKEN']
    gh = github.Github(auth=github.Auth.Token(gh_token))
    repo = gh.get_repo("conda-forge/feedstock-outputs")
    try:
        contents = repo.get_contents(_get_sharded_path(pkg_name))
    except github.GithubException as e:
        _test_and_raise_besides_file_not_exists(e)
        contents = None

    if contents is None:
        data = {"feedstocks": [feedstock]}
        repo.create_file(
            _get_sharded_path(pkg_name),
            f"[cf admin skip] ***NO_CI*** add output {pkg_name} for conda-forge/{feedstock}-feedstock",
            json.dumps(data),
        )
        print(f"    output {pkg_name} added for feedstock conda-forge/{feedstock}-feedstock", flush=True)
    else:
        data = json.loads(contents.decoded_content.decode("utf-8"))
        if feedstock not in data["feedstocks"]:
            data["feedstocks"].append(feedstock)
            repo.update_file(
                contents.path,
                f"[cf admin skip] ***NO_CI*** add output {pkg_name} for conda-forge/{feedstock}-feedstock",
                json.dumps(data),
                contents.sha,
            )
            print(f"    output {pkg_name} added for feedstock conda-forge/{feedstock}-feedstock", flush=True)
        else:
            print(f"    output {pkg_name} already exists for feedstock conda-forge/{feedstock}-feedstock", flush=True)


def _add_feedstock_output_glob(
    feedstock,
    glob_str,
):
    gh_token = os.environ['GITHUB_TOKEN']
    gh = github.Github(auth=github.Auth.Token(gh_token))
    repo = gh.get_repo("conda-forge/feedstock-outputs")
    contents = repo.get_contents("feedstock_outputs_autoreg_allowlist.yml")

    yaml = ruamel.yaml.YAML(typ="rt")  # use round-trip to preserve comments
    data = yaml.load(contents.decoded_content.decode("utf-8"))
    current_globs = data.get(feedstock, [])
    if glob_str not in current_globs:
        current_globs.append(glob_str)
    data[feedstock] = current_globs
    fp = io.StringIO()
    yaml.dump(data, fp)
    repo.update_file(
        contents.path,
        f"[cf admin skip] ***NO_CI*** add glob {glob_str} for conda-forge/{feedstock}-feedstock",
        fp.getvalue(),
        contents.sha,
    )
    print(f"    glob {glob_str} added for feedstock conda-forge/{feedstock}-feedstock", flush=True)


def check(request):
    action = request["action"]
    assert action == "add_feedstock_output"

    assert request.get("feedstock_to_output_mapping")
    for req in request["feedstock_to_output_mapping"]:
        for feedstock, _ in req.items():
            if feedstock.endswith("-feedstock"):
                feedstock = feedstock[:-10]

            r = requests.head(
                f"https://github.com/conda-forge/{feedstock}-feedstock"
            )
            r.raise_for_status()


def run(request):
    action = request["action"]
    assert action == "add_feedstock_output"

    assert request.get("feedstock_to_output_mapping")
    items_to_keep = []
    for req in request["feedstock_to_output_mapping"]:
        for feedstock, pkg_name in req.items():
            try:
                if feedstock.endswith("-feedstock"):
                    feedstock = feedstock[:-10]
                if any(_c in pkg_name for _c in ["*", "?", "[", "]", "!"]):
                    _add_feedstock_output_glob(feedstock, pkg_name)
                else:
                    _add_feedstock_output(feedstock, pkg_name)
            except Exception as e:
                print(f"    could not add output {pkg_name} for feedstock conda-forge/{feedstock}-feedstock: {e}", flush=True)
                items_to_keep.append({feedstock: pkg_name})

    if items_to_keep:
        request["feedstock_to_output_mapping"] = items_to_keep
        return request
    else:
        return None
