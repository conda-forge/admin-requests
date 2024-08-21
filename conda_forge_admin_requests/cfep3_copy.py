"""
Copy approved artifacts from an external channel to production conda-forge.
"""

import copy
import os
import subprocess
from typing import Dict, Any


import requests


def check(request: Dict[str, Any]) -> None:
    packages = request.get("anaconda_org_packages")
    if not packages:
        raise ValueError("Must define 'anaconda_org_packages' as a list of str")
    if isinstance(packages, str):
        packages = [packages]
    for package in packages:
        components = package.split("/")
        if len(components) != 5:
            raise ValueError(
                f"Package '{package}' is not valid. "
                "Must be 'owner[@label]/pkg-name/version/subdir/filename.extension'"
            )
        owner, pkg_name, version, subdir, filename = components
        if not filename[-1].endswith((".tar.bz2", ".conda")):
            raise ValueError("Only .conda and .tar.bz2 packages can be copied")
        label = request.get("from_anaconda_org_label")
        if label:
            owner_label = f"{owner}/label/{label}"
        else:
            owner_label = owner
        url = f"https://conda-web.anaconda.org/{owner_label}/{subdir}/{filename}"
        r = requests.head(url)
        if not r.ok:
            raise ValueError(
                f"Package '{package}' at {owner_label} does not seem to exist"
            )


def run(request: Dict[str, Any]) -> Dict[str, Any] | None:
    if "PROD_BINSTAR_TOKEN" not in os.environ:
        return copy.deepcopy(request)
    from_label = request.get("from_anaconda_org_label") or ()
    if from_label:
        from_label = ("--from-label", from_label)
    to_label = request.get("to_anaconda_org_label") or ()
    if to_label:
        to_label = ("--to-label", to_label)
    packages_to_try_again = []
    for package in request["anaconda_org_packages"]:
        cmd = [
            "anaconda",
            "--token",
            os.environ["PROD_BINSTAR_TOKEN"],
            "copy",
            "--to-owner",
            "conda-forge",
            *from_label,
            *to_label,
            package
        ]
        print("Copying", package, "...")
        p = subprocess.run(cmd)
        if p.returncode == 0:
            print("... OK!")
        else:
            print("... failed!")
            packages_to_try_again.append(package)

    
    if packages_to_try_again:
        request = copy.deepcopy(request)
        request["anaconda_org_packages"] = packages_to_try_again
        return request
    else:
        return None
    