import sys
import subprocess
import os
import tempfile
import github
import datetime


def _commit_to_patches(tmpdir):
    subprocess.check_call(
        "git reset --hard HEAD",
        cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
        shell=True,
    )

    subprocess.check_call(
        "git commit --allow-empty -am 'resync repo data for weekly cron-job'",
        cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
        shell=True,
    )

    subprocess.check_call(
        "git push",
        cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
        shell=True,
    )


def _post_issue_with_diff(diff):
    msg = """\
Hi! Our weekly job found a non-zero repodata patch diff:

<details>

```
%s
```

</details>
""" % diff

    dstr = datetime.date.today().strftime("%Y-%m-%d")
    gh = github.Github(os.environ['GITHUB_TOKEN'])
    repo = gh.get_repo("conda-forge/conda-forge-repodata-patches-feedstock")
    repo.create_issue(
        "[%s] non-zero repodata patch diff" % dstr,
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
            "git clone https://github.com/conda-forge/"
            "conda-forge-repodata-patches-feedstock.git",
            cwd=tmpdir,
            shell=True,
        )

        subprocess.check_call(
            "git remote set-url --push origin "
            "https://x-access-token:${GITHUB_TOKEN}@github.com/conda-forge/"
            "conda-forge-repodata-patches-feedstock.git",
            cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
            shell=True,
        )

        d = subprocess.check_output(
            "python show_diff.py",
            cwd=os.path.join(
                tmpdir,
                "conda-forge-repodata-patches-feedstock",
                "recipe"
            ),
            shell=True,
        ).decode("utf-8")

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
