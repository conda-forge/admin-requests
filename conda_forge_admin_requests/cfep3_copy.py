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

    channel_and_maybe_label, subdir, artifact = package.rsplit("/", 2)
    channel, _ = split_label_from_channel(channel_and_maybe_label)
    pkg_name, version, _, _ = parse_filename(artifact)

    # Check existence
    url = (
        f"https://conda-web.anaconda.org/{channel_and_maybe_label}/{subdir}/{artifact}"
    )
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
    if not packages or not isinstance(packages[0], dict):
        raise ValueError(
            "Must define 'anaconda_org_packages' as a list of dicts with keys "
            "{'package': channel/subdir/artifact, 'sha256': SHA256}"
        )
    for item in packages:
        if not item.get("package") or not item.get("sha256"):
            raise ValueError(
                "Each 'anaconda_org_packages' entry must be a dict with keys "
                "{'package': channel/subdir/artifact, 'sha256': SHA256}"
            )
        check_one(item["package"], item["sha256"])


def run(request: Dict[str, Any]) -> Dict[str, Any] | None:
    if "PROD_BINSTAR_TOKEN" not in os.environ:
        return copy.deepcopy(request)

    to_label = request.get("to_anaconda_org_label") or ()
    if to_label:
        to_label = ("--to-label", to_label)
    packages_to_try_again = []
    for item in request["anaconda_org_packages"]:
        check_one(item["package"], item["sha256"])
        channel_and_maybe_label, subdir, artifact = item["package"].rsplit("/", 2)
        channel, label = split_label_from_channel(channel_and_maybe_label)
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
            spec,
        ]
        print("Copying", item["package"], "...")
        p = subprocess.run(cmd)
        if p.returncode == 0:
            print("... OK!")
        else:
            print("... failed!")
            packages_to_try_again.append(item)

    if packages_to_try_again:
        request = copy.deepcopy(request)
        request["anaconda_org_packages"] = packages_to_try_again
        return request
    else:
        return None
