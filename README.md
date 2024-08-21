# admin requests

[![repodata_patching](https://github.com/conda-forge/admin-requests/actions/workflows/repodata_patching.yml/badge.svg)](https://github.com/conda-forge/admin-requests/actions/workflows/repodata_patching.yml) [![run](https://github.com/conda-forge/admin-requests/actions/workflows/main.yml/badge.svg)](https://github.com/conda-forge/admin-requests/actions/workflows/main.yml) [![create_feedstocks](https://github.com/conda-forge/admin-requests/actions/workflows/create_feedstocks.yml/badge.svg)](https://github.com/conda-forge/admin-requests/actions/workflows/create_feedstocks.yml)

This repo is for making requests to `conda-forge/core` for various administrative
tasks.


## Mark packages as broken on conda-forge

If you want to mark a package as broken on `conda-forge`, send a Pull Request
adding a new `.yml` file in `requests` folder with a list of the full names of the packages
for which the `broken` label will be added. See `examples/example-broken.yml` for an example.

Guidelines for marking packages as broken:

* If the package is functional but with incorrect metadata (e.g. missing dependencies), then
  we prefer to patch the repo data (see [here](https://github.com/conda-forge/conda-forge-repodata-patches-feedstock))
  instead of marking packages as broken. This alternative workflow makes environments more reproducible.
* Packages with requirements/metadata that are too strict but otherwise work are
  not technically broken and should not be marked as such.
* Packages with missing metadata can be marked as broken on a temporary basis
  but should be patched in the repo data and be marked unbroken later.
* In some cases where the number of users of a package is small or it is used by
  the maintainers only, we can allow packages to be marked broken more liberally.
* We (`conda-forge/core`) try to make a decision on these requests within 24 hours.


## Mark packages as not broken on conda-forge

If you want to remove the broken label from packages on `conda-forge`, send a Pull Request
adding a new `.yml` file in `requests` folder with a list of the full names of the packages
for which the label `broken` will be removed. See `examples/example-not-broken.yml` for an example.


## Reset your Feedstock Token

If you want to reset your feedstock token to fix issues with uploads, send a Pull Request
adding a new `.yml` file in `requests` folder with a list of the feedstock names
without `-feedstock`. See `examples/example-token-reset.yml` for an example.
(e.g., for `python-feedstock`, the feedstocks list must contain `python`).


## Archive or unarchive a feedstock

If you want to request a feedstock to be archived, send a Pull Request
adding a new `.yml` file in `requests` folder with a list of the feedstock names
without `-feedstock`. See `examples/example-archive.yml` for an example.
(e.g., for `python-feedstock`, the feedstocks list must contain `python`).
For unarchiving, see `examples/example-unarchive.yml` for an example.

For feedstocks that need to be archived, please leave an open issue with some details about
why that decision was taken (e.g. it has been deprecated by a new feedstock),
and link it in your PR description.


## Request / revoke access to CI resources

Certain CI resources are opt-in only. If you want to request access to these resources, please
submit a PR adding your feedstock name to a new `.yml` file in `requests` folder.

Available opt-in resources:

- Travis CI: See `examples/example-travis.yml`
- [`open-gpu-server`](https://github.com/Quansight/open-gpu-server) (includes GPU CI and long-running builds): See `examples/example-open-gpu-server.yml`. 

## Request a CFEP-3 copy to conda-forge

CFEP-3 specifies the process to add foreign builds to conda-forge. [Read the CFEP](https://github.com/conda-forge/cfep/blob/main/cfep-03.md) for more details.
This workflow allows users to request a copy once the manual review has been passed.

To do so, please create a new `.yml` file in the `requests` folder. Check `examples/example-cfep-3.yml` for the required metadata.

For provenance and transparency, the PR description must include a link to the original PR and the logs, along with the artifact(s) to be reviewed.
