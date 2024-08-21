"""
Copy approved artifacts from an external channel to production conda-forge.
"""

import copy
import hmac
import os
import subprocess
from typing import Dict, Any

import requests

from .utils import split_label_from_channel, parse_filename


def check_one(package: str, sha256: str):
    if not isinstance(sha256, str) or len(sha256) != 64:
        raise ValueError(
            f"Key '{sha256}' must be SHA256 for the artifact (64 hexadecimal characters)"
        )
    
    channel, subdir, artifact = package.rsplit("/", 3)
    channel, _ = split_label_from_channel(channel)
    pkg_name, version, _, _ = parse_filename(artifact)

    # Check existence
    url = f"https://conda-web.anaconda.org/{channel}/{subdir}/{artifact}"
    r = requests.head(url)
    if not r.ok:
        raise ValueError(f"Package '{package}' at {channel} does not seem to exist")
    
    # Check SHA256
    r = requests.get(
        f"https://api.anaconda.org/dist/{channel}/{pkg_name}/{version}/{subdir}/{artifact}",
        timeout=10,
    )
    r.raise_for_status()
    api_sha256 = r.json()["sha256"]
    if not hmac.compare_digest(sha256, api_sha256):
        raise ValueError(
            f"User-provided SHA256 {sha256} does not match expected value {api_sha256}"
        )


def check(request: Dict[str, Any]) -> None:
    packages = request.get("anaconda_org_packages")
    if not packages or not isinstance(packages, dict):
        raise ValueError(
            "Must define 'anaconda_org_packages' as a dict of [sha256, owner/subdir/artifact]"
    )
    for sha256, package in packages.items():
        check_one(package, sha256)


def run(request: Dict[str, Any]) -> Dict[str, Any] | None:
    if "PROD_BINSTAR_TOKEN" not in os.environ:
        return copy.deepcopy(request)

    to_label = request.get("to_anaconda_org_label") or ()
    if to_label:
        to_label = ("--to-label", to_label)
    packages_to_try_again = []
    for sha256, package in request["anaconda_org_packages"].items():
        check_one(package, sha256)
        channel, subdir, artifact = package.rsplit("/", 3)
        channel, label = split_label_from_channel(channel)
        from_label = ("--from-label", label) if label != "main" else ()
        pkg_name, version, _, _ = parse_filename(artifact)
        spec = f"{channel}/{pkg_name}/{version}/{subdir}/{artifact}"
        cmd = [
            "anaconda",
            "--token",
            os.environ["PROD_BINSTAR_TOKEN"],
            "copy",
            "--to-owner",
            "conda-forge",
            *from_label,
            *to_label,
            spec
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
    