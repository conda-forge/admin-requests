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
* You can use `pixi run find-name {matchspec}` to get a list of filenames matching given spec.
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


## Archive or unarchive a branch on a feedstock

Branches in conda-forge should generally not be deleted, because it is important to keep the
history for the state of the feedstock for any packages that got published. To avoid the
accumulation of many branches (esp. on feedstocks with regular LTS versions), it's possible
to archive a branch by converting it into a tag (and vice-versa). The naming relationship
between the branch and tag is fixed: for a branch `foo`, the tag will be called `foo_archived`.

If you want to archive branches on a feedstock, send a Pull Request
adding a new `.yml` file in `requests` folder with a dictionary of feedstock names
(without `-feedstock`) mapping to a list of branch names that should be archived.
See `examples/example-archive-branch.yml` for an example.
For unarchiving, see `examples/example-unarchive-branch.yml` for an example.


## Request / revoke access to CI resources

Certain CI resources are opt-in only. If you want to request access to these resources, please
submit a PR adding your feedstock name to a new `.yml` file in `requests` folder.

Available opt-in resources:

### [Travis CI](https://www.travis-ci.com)

- `action` key: `travis`
- Example `examples/example-travis.yml`

### Larger runners for Github Actions

- We have partnered with different providers for [self-hosted runners for Github Actions](https://conda-forge.org/docs/how-to/advanced/self-hosted-runners/).
- `action` key: `namespace` ([namespace.so](https://namespace.so)) or `blacksmith` ([blacksmith.sh](https://blacksmith.sh))
- Example `examples/example-gha-self-hosted.yml`

Github Actions labels for `conda_build_config.yaml`:

| `github_actions_labels` value              | Platform        | CPUs    | RAM   |
| :----------------------------------------- | :-------------: | :-----: | :---: |
| `namespace-profile-8cpu-on-linux-64`       | `linux-64`      | 8       | 32 GB |
| `namespace-profile-16cpu-on-linux-64`      | `linux-64`      | 16      | 64 GB |
| `namespace-profile-8cpu-on-linux-aarch64`  | `linux-aarch64` | 8       | 32 GB |
| `namespace-profile-16cpu-on-linux-aarch64` | `linux-aarch64` | 16      | 64 GB |
| `namespace-profile-6cpu-on-osx-arm64`      | `osx-arm64`     | 6       | 14 GB |
| `namespace-profile-12cpu-on-osx-arm64`     | `osx-arm64`     | 12      | 28 GB |
| `namespace-profile-8cpu-on-win-64` ‡       | `win-64`        | 8       | 32 GB |
| `namespace-profile-16cpu-on-win-64` ‡      | `win-64`        | 16      | 64 GB |
| | | | |
| `blacksmith-8vcpu-ubuntu-2404`             | `linux-64`      | 8       | 32 GB |
| `blacksmith-16vcpu-ubuntu-2404`            | `linux-64`      | 16      | 64 GB |
| `blacksmith-8vcpu-ubuntu-2404-arm`         | `linux-aarch64` | 8       | 24 GB |
| `blacksmith-16vcpu-ubuntu-2404-arm`        | `linux-aarch64` | 16      | 48 GB |
| `blacksmith-6vcpu-macos-latest`            | `osx-arm64`     | 6       | 24 GB |
| `blacksmith-12vcpu-macos-latest`           | `osx-arm64`     | 12      | 48 GB |
| `blacksmith-8vcpu-windows-2025`            | `win-64`        | 8       | 28 GB |
| `blacksmith-16vcpu-windows-2025`           | `win-64`        | 16      | 56 GB |

> ‡ Namespace runners on Windows need to use `D:` as the main drive for the installation and build workspace directories. In `conda-forge.yml`:
>
> ```yaml
> workflow_settings:
>   tools_install_dir:
>     - provider: github_actions
>       platform: win
>       value: D:\Miniforge3
>   build_workspace_dir:
>     - provider: github_actions
>       platform: win
>       value: D:\bld
> ```

Other providers may be available via [cirun.io](https://cirun.io) (`action: cirun`, see `examples/example-cirun.yml`).
Check the [`conda-forge/.cirun`](https://github.com/conda-forge/.cirun) repository for more details.

## Request a CFEP-3 copy to conda-forge

CFEP-3 specifies the process to add foreign builds to conda-forge. [Read the CFEP](https://github.com/conda-forge/cfep/blob/main/cfep-03.md) for more details.
This workflow allows users to request a copy once the manual review has been passed.

To do so, please create a new `.yml` file in the `requests` folder. Check `examples/example-cfep-3.yml` for the required metadata.

For provenance and transparency, the PR description must include a link to the original PR and the logs, along with the artifact(s) to be reviewed.

## Add a package output to a feedstock

By default, `conda-forge` feedstocks cannot push packages to our channel that another feedstock makes. If you encountered an error
when building your package indicating that the given package was not allowed for your feedstock (e.g., you moved a package
build from one feedstock to another), you should request the output be added to the new feedstock via this repository. An example request
is located in [examples/example-add-feedstock-output.yml](examples/example-add-feedstock-output.yml). You can add both glob patterns
and package names.

While glob patterns are support, they should be used with care as they
essentially "squat" on all future matched. If you are requesting a specific
package output, please use the full name of the package output. We support the
glob syntax of the Python `fnmatch` module. Make a PR putting your `.yml`
request file in the `requests` directory and the `conda-forge/core` team will
review it.
