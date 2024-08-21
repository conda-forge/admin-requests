import sys
import subprocess
import os
import tempfile
import github
import datetime


def _commit_to_patches(tmpdir):
    subprocess.check_call(
        ["git", "reset", "--hard", "HEAD"],
        cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
    )

    subprocess.check_call(
        ["git", "commit", "--allow-empty", "-am", "resync repo data for weekly cron-job"],
        cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
    )

    subprocess.check_call(
        ["git", "push"],
        cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
    )


def _post_issue_with_diff(diff):
    msg = f"""\
Hi! Our weekly job found a non-zero repodata patch diff:

<details>

```
{diff}
```

</details>
"""

    today = datetime.date.today().strftime("%Y-%m-%d")
    gh = github.Github(os.environ['GITHUB_TOKEN'])
    repo = gh.get_repo("conda-forge/conda-forge-repodata-patches-feedstock")
    repo.create_issue(
        f"[{today}] non-zero repodata patch diff",
        body=msg,
    )


def update_repodata_patches(dry_run):

    skipme = [
        "================================================================================",
        "linux-armv7l",
        "linux-ppc64le",
        "linux-aarch64",
        "noarch",
        "win-32",
        "osx-arm64",
        "osx-64",
        "linux-64",
        "win-64",
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.check_call(
            [
                "git",
                "clone",
                "https://github.com/conda-forge/conda-forge-repodata-patches-feedstock.git",
            ],
            cwd=tmpdir,
        )

        origin_url = (
            "https://x-access-token:${GITHUB_TOKEN}@github.com/"
            "conda-forge/conda-forge-repodata-patches-feedstock.git"
        )
        subprocess.check_call(
            [
                "git",
                "remote",
                "set-url",
                "--push",
                "origin",
                origin_url,
            ],
            cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
        )

        d = subprocess.check_output(
            ["python", "show_diff.py"],
            cwd=os.path.join(
                tmpdir,
                "conda-forge-repodata-patches-feedstock",
                "recipe",
            ),
            text=True,
        )

        empty = True
        for line in d.splitlines():
            line = line.strip()
            if len(line) > 0 and not (
                line.startswith("Downloading")
                or line in skipme
            ):
                empty = False

        print("diff:\n" + d, flush=True)
        print("is empty:", empty, flush=True)

        if len(d) > 0 and not empty:
            if not dry_run:
                _post_issue_with_diff(d)
                _commit_to_patches(tmpdir)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise RuntimeError("Need 0 or 1 arguments")
    if len(sys.argv) == 2 and sys.argv[1] == '--dry-run':
        dry_run = True
    else:
        dry_run = False

    update_repodata_patches(dry_run)
