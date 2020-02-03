import sys
from glob import glob
import subprocess
import os

def split_pkg(pkg):
    if not pkg.endswith(".tar.bz2"):
        raise RuntimeError("Can only process packages that end in .tar.bz2")
    pkg = pkg[:-8]
    plat, pkg_name = pkg.split("/")
    name_ver, build = pkg_name.rsplit('-', 1)
    name, ver = name_ver.rsplit('-', 1)
    return plat, name, ver, build


def get_files():
    return [f for f in glob("pkgs/*.txt") if f != "pkgs/example.txt"]


def check_packages():
    for file_name in get_files():
        with open(file_name, "r") as f:
            pkgs = f.readlines()
            pkgs = [pkg.strip() for pkg in pkgs]
        for pkg in pkgs:
            plat, name, ver, build = split_pkg(pkg)
            subprocess.check_call(f"CONDA_SUBDIR={plat} conda search {name}={ver}={build} -c conda-forge --override-channels", shell=True)


token_path = os.path.expanduser("~/.config/binstar/https%3A%2F%2Fapi.anaconda.org.token")


def mark_broken_file(file_name):
    with open(file_name, "r") as f:
        pkgs = f.readlines()
        pkgs = [pkg.strip() for pkg in pkgs]
    for pkg in pkgs:
        plat, name, ver, build = split_pkg(pkg)
        try:
            subprocess.check_call(f"anaconda -t {token_path} -v move conda-forge/{name}/{ver}/{pkg} --from-label main --to-label broken", shell=True)
        except subprocess.CalledProcessError:
            return
    subprocess.check_call(f"git rm {file_name}", shell=True)
    subprocess.check_call(f"git commit -m 'Remove {file_name} after marking broken'", shell=True)
    subprocess.check_call("git show", shell=True)


def mark_broken():
    if not "BINSTAR_TOKEN" in os.environ:
        return

    os.makedirs(os.path.expanduser("~/.config/binstar"))
    with open(token_path, "w") as f:
        f.write(os.environ["BINSTAR_TOKEN"])

    try:
        for file_name in get_files():
            mark_broken_file(file_name)
    finally:
        os.remove(token_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise RuntimeError("Need 1 and only 1 argument")
    if sys.argv[1] == 'check':
        check_packages()
    elif sys.argv[1] == 'mark':
        mark_broken()
    else:
        raise RuntimeError(f"Unrecognized argument {sys.argv[1]}")

