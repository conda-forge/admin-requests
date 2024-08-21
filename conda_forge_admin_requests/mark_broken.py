import subprocess
import os
import tempfile
import requests
import copy


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


def check(request):
    action = request["action"]
    assert action in ("broken", "not_broken")

    if action == "broken":
        channel = "conda-forge"
    else:
        channel = "conda-forge/label/broken"

    assert "packages" in request
    pkgs = request["packages"]

    for pkg in pkgs:
        # check to ensure the artifact exists
        r = requests.head(f"https://conda.anaconda.org/conda-forge/{pkg}")
        r.raise_for_status()

        # check it is on the right channel
        plat, name, ver, build = split_pkg(pkg)
        env = os.environ.copy()
        env["CONDA_SUBDIR"] = plat
        subprocess.check_call(
            ["conda", "search", f"{name}={ver}={build}", "-c", channel, "--override-channels"],
            env=env,
        )


def mark_broken_pkg(pkg, action):
    plat, name, ver, build = split_pkg(pkg)

    if action == "broken":
        func = requests.post
    else:
        func = requests.delete

    r = func(
        "https://api.anaconda.org/channels/conda-forge/broken",
        headers={'Authorization': 'token {}'.format(os.environ["PROD_BINSTAR_TOKEN"])},
        json={
            "basename": pkg,
            "package": name,
            "version": ver,
        }
    )
    if r.status_code != 201:
        print(f"        could not mark {action}", flush=True)
        return False
    else:
        print(f"        marked {action}", flush=True)
        return True


def run(request):
    if "PROD_BINSTAR_TOKEN" not in os.environ:
        return copy.deepcopy(request)

    packages = request["packages"]
    action = request["action"]

    pkgs_to_try_again = []
    did_any = False
    for package in packages:
        print(f"working on package {package}", flush=True)
        success = mark_broken_pkg(package, action)
        if success:
            did_any = True
        else:
            pkgs_to_try_again.append(package)

    if did_any:
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
                "https://x-access-token:${GITHUB_TOKEN}@github.com/conda-forge/"
                "conda-forge-repodata-patches-feedstock.git"
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

            success_pkgs = set(packages) - set(pkgs_to_try_again)
            fstr = " ".join(f for f in success_pkgs)
            subprocess.check_call(
                [
                    "git",
                    "commit",
                    "--allow-empty",
                    "-am",
                    f"resync repo data for broken/not-broken packages {fstr}",
                ],
                cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
            )

            subprocess.check_call(
                ["git", "push"],
                cwd=os.path.join(tmpdir, "conda-forge-repodata-patches-feedstock"),
            )

    if pkgs_to_try_again:
        request = copy.deepcopy(request)
        request["packages"] = pkgs_to_try_again
        return request
    else:
        return None
