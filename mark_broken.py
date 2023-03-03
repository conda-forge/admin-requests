import sys
from glob import glob
import subprocess
import os
import tempfile
import requests


def split_pkg(pkg):
    if pkg.endswith(".tar.bz2"):
        pkg = pkg[:-len(".tar.bz2")]
    elif pkg.endswith(".conda"):
        pkg = pkg[:-len(".conda")]
    else:
        raise RuntimeError("Can only process packages that end in .tar.bz2 or .conda!")
    plat, pkg_name = pkg.split("/")
    name_ver, build = pkg_name.rsplit('-', 1)
    name, ver = name_ver.rsplit('-', 1)
    return plat, name, ver, build


def get_broken_files():
    return (
        [f for f in glob("broken/*") if f != "broken/example.txt"]
        + [f for f in glob("pkgs/*") if f != "pkgs/example.txt"]
    )


def get_not_broken_files():
    return [f for f in glob("not_broken/*") if f != "not_broken/example.txt"]


def check_packages():
    for channel, filenames in (
        ("conda-forge", get_broken_files()),
        ("conda-forge/label/broken", get_not_broken_files()),
    ):
        for file_name in filenames:
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
                    f"-c {channel} --override-channels",
                    shell=True,
                )


def mark_broken_file(file_name):
    did_one = False

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
            return did_one
        else:
            print("        marked broken", flush=True)
            did_one = True
    subprocess.check_call(f"git rm {file_name}", shell=True)
    subprocess.check_call(
        f"git commit -m 'Remove {file_name} after marking broken'", shell=True)
    subprocess.check_call("git show", shell=True)

    return did_one


def mark_not_broken_file(file_name):
    did_one = False

    with open(file_name, "r") as f:
        pkgs = f.readlines()
        pkgs = [pkg.strip() for pkg in pkgs]
    for pkg in pkgs:
        # ignore blank lines or Python-style comments
        if pkg.startswith('#') or len(pkg) == 0:
            continue
        print("    package: %s" % pkg, flush=True)
        plat, name, ver, build = split_pkg(pkg)
        r = requests.delete(
            "https://api.anaconda.org/channels/conda-forge/broken",
            headers={'Authorization': 'token {}'.format(os.environ["BINSTAR_TOKEN"])},
            json={
                "basename": pkg,
                "package": name,
                "version": ver,
            }
        )
        if r.status_code != 201:
            print("        could not mark not broken", flush=True)
            return did_one
        else:
            print("        marked not broken", flush=True)
            did_one = True
    subprocess.check_call(f"git rm {file_name}", shell=True)
    subprocess.check_call(
        f"git commit -m 'Remove {file_name} after marking not broken'", shell=True)
    subprocess.check_call("git show", shell=True)

    return did_one


def mark_broken():
    if "BINSTAR_TOKEN" not in os.environ:
        return

    did_any = False
    br_files = get_broken_files()
    print("found files: %s" % br_files, flush=True)
    for file_name in br_files:
        print("working on file %s" % file_name, flush=True)
        did_any = did_any or mark_broken_file(file_name)

    nbr_files = get_not_broken_files()
    print("found files: %s" % nbr_files, flush=True)
    for file_name in nbr_files:
        print("working on file %s" % file_name, flush=True)
        did_any = did_any or mark_not_broken_file(file_name)

    if did_any:
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

            all_files = br_files + nbr_files
            fstr = " ".join(f for f in all_files)
            subprocess.check_call(
                "git commit --allow-empty -am 'resync repo data "
                "for broken/notbroken packages in files %s'" % fstr,
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
