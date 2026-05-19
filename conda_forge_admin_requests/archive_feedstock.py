import copy
import io
import os
import re
import subprocess
import tempfile

from ruamel.yaml import YAML

import requests

from .utils import GH_ORG, get_gh_headers, raise_json_for_status

RECIPE_CANDIDATES = ("recipe/recipe.yaml", "recipe/meta.yaml")


def _find_recipe_file(feedstock_dir):
    for rel in RECIPE_CANDIDATES:
        path = os.path.join(feedstock_dir, rel)
        if os.path.isfile(path):
            return path
    return None


def _set_maintainers_in_recipe_yaml(path, new_maintainers):
    """Round-trip edit a rattler-build recipe.yaml. Returns True if modified."""
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    with open(path) as fh:
        data = yaml.load(fh)

    if data is None:
        return False

    existing = None
    if "extra" in data and isinstance(data["extra"], dict):
        existing = data["extra"].get("recipe-maintainers")

    if existing is not None and list(existing) == list(new_maintainers):
        return False

    if "extra" not in data or not isinstance(data.get("extra"), dict):
        data["extra"] = {}
    data["extra"]["recipe-maintainers"] = list(new_maintainers)

    buf = io.StringIO()
    yaml.dump(data, buf)
    with open(path, "w") as fh:
        fh.write(buf.getvalue())
    return True


# Matches a `recipe-maintainers:` key with either a block list (indented `-`
# items on following lines) or an inline flow list `[a, b, ...]` on the same
# line. The block form consumes subsequent lines that are either blank, a
# comment at deeper indent, or a list item at deeper indent.
_MAINTAINERS_BLOCK_RE = re.compile(
    r"""
    ^(?P<indent>[ \t]*)recipe-maintainers:[ \t]*
    (?:
        (?P<flow>\[[^\]\n]*\])[ \t]*\n
      |
        \n
        (?P<block>
          (?:[ \t]*(?:\#[^\n]*)?\n)*
          (?:(?P=indent)[ \t]+-[ \t]+[^\n]*\n
             (?:[ \t]*(?:\#[^\n]*)?\n)*
          )+
        )
    )
    """,
    re.MULTILINE | re.VERBOSE,
)


def _set_maintainers_in_meta_yaml(path, new_maintainers):
    """Regex-based edit of a Jinja-templated meta.yaml. Returns True if modified."""
    with open(path) as fh:
        text = fh.read()

    match = _MAINTAINERS_BLOCK_RE.search(text)
    if match is None:
        print(
            f"warning: could not locate recipe-maintainers block in {path}; "
            "skipping maintainer update",
            flush=True,
        )
        return False

    indent = match.group("indent")
    if new_maintainers:
        replacement_lines = [f"{indent}recipe-maintainers:"]
        for name in new_maintainers:
            replacement_lines.append(f"{indent}  - {name}")
        replacement = "\n".join(replacement_lines) + "\n"
    else:
        replacement = f"{indent}recipe-maintainers: []\n"

    new_text = text[: match.start()] + replacement + text[match.end() :]

    if new_text == text:
        return False

    # Sanity check: the count of *line-anchored* recipe-maintainers keys
    # should be preserved (1 → 1). Using a line-anchored pattern avoids
    # false positives from the string appearing inside quoted values or
    # comments elsewhere in the file.
    line_key_re = re.compile(r"(?m)^[ \t]*recipe-maintainers:")
    if len(line_key_re.findall(new_text)) != len(line_key_re.findall(text)):
        print(
            f"warning: post-edit sanity check failed for {path}; "
            "skipping maintainer update",
            flush=True,
        )
        return False

    with open(path, "w") as fh:
        fh.write(new_text)
    return True


def set_recipe_maintainers(feedstock_dir, new_maintainers):
    """Rewrite the recipe's extra.recipe-maintainers list.

    Returns True if the recipe file was modified, False otherwise.
    Pass an empty list to clear the maintainers (used on archive).
    """
    path = _find_recipe_file(feedstock_dir)
    if path is None:
        print(
            f"warning: no recipe file found under {feedstock_dir}; "
            "skipping maintainer update",
            flush=True,
        )
        return False

    if path.endswith("recipe.yaml"):
        return _set_maintainers_in_recipe_yaml(path, new_maintainers)
    return _set_maintainers_in_meta_yaml(path, new_maintainers)


def _update_and_push_maintainers(repo, default_branch, new_maintainers, commit_msg):
    """Clone feedstock, rewrite maintainers, commit, and push.

    Swallows errors (logs them) — the archive/unarchive state change is the
    primary intent of the request and must not be re-queued if this step fails.
    """
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            feedstock_dir = os.path.join(tmp_dir, repo)
            subprocess.check_call(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    default_branch,
                    f"https://github.com/{GH_ORG}/{repo}.git",
                    feedstock_dir,
                ]
            )

            if not set_recipe_maintainers(feedstock_dir, new_maintainers):
                print(
                    f"feedstock {repo}: no recipe-maintainers change needed",
                    flush=True,
                )
                return

            recipe_path = _find_recipe_file(feedstock_dir)
            rel = os.path.relpath(recipe_path, feedstock_dir)

            subprocess.check_call(["git", "add", rel], cwd=feedstock_dir)
            subprocess.check_call(
                [
                    "git",
                    "-c",
                    "user.name=conda-forge-admin",
                    "-c",
                    "user.email=conda-forge-admin@conda-forge.org",
                    "commit",
                    "-m",
                    commit_msg,
                ],
                cwd=feedstock_dir,
            )
            push_url = (
                f"https://x-access-token:{os.environ['GITHUB_TOKEN']}"
                f"@github.com/{GH_ORG}/{repo}.git"
            )
            subprocess.check_call(
                ["git", "push", push_url, f"HEAD:{default_branch}"],
                cwd=feedstock_dir,
            )
            print(
                f"feedstock {repo}: pushed recipe-maintainers update to "
                f"{default_branch}",
                flush=True,
            )
    except Exception as e:
        print(
            f"failed to update recipe-maintainers for {repo}: {e!r} "
            "(archive/unarchive state change was not reverted)",
            flush=True,
        )


def process_repo(repo, task, new_maintainers):
    owner = GH_ORG
    headers = get_gh_headers()

    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
    )
    raise_json_for_status(r)

    data = r.json()
    default_branch = data.get("default_branch", "main")

    if task == "archive":
        target_status = "archived"
    else:
        target_status = "unarchived"

    if task == "archive" and data["archived"]:
        print(f"feedstock {repo} is already {target_status}", flush=True)
        return

    if task == "unarchive" and not data["archived"]:
        print(f"feedstock {repo} is already {target_status}", flush=True)
        return

    if task == "archive":
        # Clear maintainers *before* flipping to archived; archived repos
        # reject pushes.
        _update_and_push_maintainers(
            repo,
            default_branch,
            [],
            "[ci skip] [skip ci] [cf admin skip] ***NO_CI*** "
            "Clear recipe-maintainers on feedstock archive",
        )

    r = requests.patch(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        json={"archived": task == "archive"},
    )
    raise_json_for_status(r)

    print(f"feedstock {repo} was {target_status}", flush=True)

    if task == "unarchive":
        _update_and_push_maintainers(
            repo,
            default_branch,
            new_maintainers,
            "[ci skip] [skip ci] [cf admin skip] ***NO_CI*** "
            "Set recipe-maintainers on feedstock unarchive: "
            + ", ".join(new_maintainers),
        )


def _iter_feedstock_maintainers(request):
    """Yield (feedstock, new_maintainers) pairs for a request.

    archive: feedstocks is a list of strings; new_maintainers is [].
    unarchive: feedstocks is a dict {name: [maintainers]}.
    """
    task = request["action"]
    feedstocks = request["feedstocks"]
    if task == "unarchive":
        for feedstock, maintainers in feedstocks.items():
            yield feedstock, list(maintainers)
    else:
        for feedstock in feedstocks:
            yield feedstock, []


def run(request):
    task = request["action"]

    failed_list = []
    failed_map = {}
    for feedstock, new_maintainers in _iter_feedstock_maintainers(request):
        try:
            process_repo(f"{feedstock}-feedstock", task, new_maintainers)
        except Exception as e:
            print(f"failed to {task} '{feedstock}': {e!r}", flush=True)
            if task == "unarchive":
                failed_map[feedstock] = new_maintainers
            else:
                failed_list.append(feedstock)

    if task == "unarchive" and failed_map:
        request = copy.deepcopy(request)
        request["feedstocks"] = failed_map
        return request
    if task != "unarchive" and failed_list:
        request = copy.deepcopy(request)
        request["feedstocks"] = failed_list
        return request
    return None


def _check_github_user_exists(username):
    headers = {"User-Agent": "conda-forge/admin-requests"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(
        f"https://api.github.com/users/{username}",
        headers=headers,
    )
    return r.status_code == 200


def check(request):
    assert "feedstocks" in request
    task = request["action"]

    if task == "unarchive":
        feedstocks = request["feedstocks"]
        assert isinstance(feedstocks, dict), (
            "unarchive requests must now provide a mapping of "
            "{feedstock: [new-maintainer-usernames]}; see "
            "examples/example-unarchive.yml"
        )

        all_usernames = set()
        for feedstock, maintainers in feedstocks.items():
            assert isinstance(maintainers, list) and maintainers, (
                f"unarchive request for '{feedstock}' must list at least one "
                "new maintainer username"
            )
            all_usernames.update(maintainers)

        missing_users = sorted(
            u for u in all_usernames if not _check_github_user_exists(u)
        )
        if missing_users:
            raise RuntimeError(f"GitHub user(s) not found: {missing_users}")

        feedstock_names = list(feedstocks.keys())
    else:
        assert isinstance(request["feedstocks"], list)
        feedstock_names = request["feedstocks"]

    missing_feedstocks = []
    for feedstock in feedstock_names:
        r = requests.get(f"https://github.com/conda-forge/{feedstock}-feedstock")
        if r.status_code != 200:
            missing_feedstocks.append(feedstock)

    if missing_feedstocks:
        raise RuntimeError(
            f"{list(set(missing_feedstocks))} feedstocks could not be found!"
        )
