# admin requests

This repo is for making requests to `conda-forge/core` for various administrative
tasks.


## Mark packages as broken on conda-forge

If you want to mark a package as broken on `conda-forge`, send a Pull Request
adding a new `.txt` file in `broken/` with a list of the full names of the packages
to which the `broken` label will be added. See `broken/example.txt` for an example.

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
adding a new `.txt` file in `not_broken/` with a list of the full names of the packages
for which the label `broken` will be removed. See `not_broken/example.txt` for an example.


## Reset your Feedstock Token

If you want to reset your feedstock token to fix issues with uploads, place the name of your feedstock in
a new `.txt` file in `token_reset/`. See `token_reset/example.txt` for an example. You should use the name
without `-feedstock` (e.g., for `python-feedstock`, you put in just `python`).
