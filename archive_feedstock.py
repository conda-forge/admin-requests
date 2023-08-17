import os
import sys
import glob
import requests
import subprocess


def get_task_files(task):
    exf = os.path.join(task, "example.txt")
    return [
        f for f in glob.glob(os.path.join(task, "*.txt"))
        if f != exf
    ]


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


def process_feedstocks_in_file(task_file, task):
    pkgs_to_do_again = []
    with open(task_file, "r") as fp:
        for line in fp:
            line = line.strip()
            if line.startswith("#") or len(line) == 0:
                continue

            try:
                process_repo(line + "-feedstock", task)
            except Exception as e:
                print(
                    "failed to %s '%s': %s" % (task, line, repr(e)),
                    flush=True,
                )
                pkgs_to_do_again.append(line)

    if pkgs_to_do_again:
        with open(task_file, "w") as fp:
            fp.write(
                "# %s failed for these feedstocks - "
                "trying again later\n" % task
            )
            for pkg in pkgs_to_do_again:
                fp.write(pkg + "\n")
        subprocess.check_call(f"git add {task_file}", shell=True)
        subprocess.check_call(
            f"git commit --allow-empty -m 'Keeping {task_file} "
            f"after failed {task}'",
            shell=True,
        )
    else:
        subprocess.check_call(f"git rm {task_file}", shell=True)
        subprocess.check_call(
            f"git commit -m 'Remove {task_file} after {task}'",
            shell=True,
        )

    subprocess.check_call("git show", shell=True)


def check_for_feedstocks_in_file(token_reset_file):
    missing_feedstocks = []
    with open(token_reset_file, "r") as fp:
        for line in fp.readlines():
            line = line.strip()
            if line.startswith("#") or len(line) == 0:
                continue

            r = requests.get(
                "https://github.com/conda-forge/%s-feedstock" % line
            )
            if r.status_code != 200:
                missing_feedstocks.append(line)
    return missing_feedstocks


def main(*, check_only):
    missing_feedstocks = []
    for task in "archive", "unarchive":
        task_files = get_task_files(task)
        for task_file in task_files:
            print("working on file %s" % task_file, flush=True)
            if check_only:
                missing_feedstocks.extend(
                    check_for_feedstocks_in_file(task_file)
                )
            else:
                process_feedstocks_in_file(task_file, task)

    if missing_feedstocks:
        raise RuntimeError(
            "feedstocks %s could not be found!" % list(set(missing_feedstocks))
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python archive_feedstock.py [check | archive]")
    check_only = sys.argv[1] == "check"
    main(check_only=check_only)
