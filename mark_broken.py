import sys
from glob import glob
import subprocess
import os
import tempfile
import requests


def split_pkg(pkg):
    if not pkg.endswith(".tar.bz2"):
        raise RuntimeError("Can only process packages that end in .tar.bz2")
    pkg = pkg[:-8]
    plat, pkg_name = pkg.split("/")
    name_ver, build = pkg_name.rsplit('-', 1)
    name, ver = name_ver.rsplit('-', 1)
    return plat, name, ver, build


def get_files():
    return [f for f in glob("pkgs/*") if f != "pkgs/example.txt"]


def check_packages():
    for file_name in get_files():
        with open(file_name, "r") as f:
            pkgs = f.readlines()
            pkgs = [pkg.strip() for pkg in pkgs]
        for pkg in pkgs:
            # ignore blank lines or Python-style comments
            if pkg.startswith('#') or len(pkg) == 0:
                continue
            plat, name, ver, build = split_pkg(pkg)
            subprocess.check_call(
                f"CONDA_SUBDIR={plat} conda search {name}={ver}={build} "
                "-c conda-forge --override-channels",
                shell=True,
            )


token_path = os.path.expanduser(
    "~/.config/binstar/https%3A%2F%2Fapi.anaconda.org.token")


def mark_broken_file(file_name):
    with open(file_name, "r") as f:
        pkgs = f.readlines()
        pkgs = [pkg.strip() for pkg in pkgs]
    for pkg in pkgs:
        # ignore blank lines or Python-style comments
        if pkg.startswith('#') or len(pkg) == 0:
            continue
        print("    package: %s" % pkg, flush=True)
        plat, name, ver, build = split_pkg(pkg)
        r = requests.post(
            "https://api.anaconda.org/channels/conda-forge/broken",
            headers={'Authorization': 'token {}'.format(os.environ["BINSTAR_TOKEN"])},
            json={
                "basename": pkg,
                "package": name,
                "version": ver,
            }
        )
        if r.status_code != 201:
            print("        could not mark broken", flush=True)
            return
        else:
            print("        marked broken", flush=True)
    subprocess.check_call(f"git rm {file_name}", shell=True)
    subprocess.check_call(
        f"git commit -m 'Remove {file_name} after marking broken'", shell=True)
    subprocess.check_call("git show", shell=True)


def mark_broken():
    if "BINSTAR_TOKEN" not in os.environ:
        return

    files = get_files()
    print("found files: %s" % files, flush=True)
    for file_name in files:
        print("working on file %s" % file_name, flush=True)
        mark_broken_file(file_name)

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.check_call(
            "git clone https://github.com/conda-forge/"
            "conda-forge-repodata-patches-feedstock.git",
            cwd=tmpdir,
            shell=True,
        )

        subprocess.check_call(
            "git remote set-url --push origin "
            "https://${GITHUB_TOKEN}@github.com/conda-forge/"
            "conda-forge-repodata-patches-feedstock.git",
            cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
            shell=True,
        )

        fstr = " ".join(f for f in files)
        subprocess.check_call(
            "git commit --allow-empty -am 'resync repo data "
            "for broken packages in files %s'" % fstr,
            cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
            shell=True,
        )

        subprocess.check_call(
            "git push",
            cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
            shell=True,
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise RuntimeError("Need 1 and only 1 argument")
    if sys.argv[1] == 'check':
        check_packages()
    elif sys.argv[1] == 'mark':
        mark_broken()
    else:
        raise RuntimeError(f"Unrecognized argument {sys.argv[1]}")
