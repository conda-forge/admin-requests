# admin requests

This repo is for making requests to `conda-forge/core` for various administrative
tasks.

## Mark packages as broken on conda-forge

If you want to mark a package as broken on `conda-forge`, send a Pull Request
adding a new `.txt` file in `broken/` with a list of the full names of the packages
to which the `broken` label will be added. See `broken/example.txt` for an example.

## Mark packages as not broken on conda-forge

If you want to remove the broken label from packages on `conda-forge`, send a Pull Request
adding a new `.txt` file in `not_broken/` with a list of the full names of the packages
for which the label `broken` will be removed. See `not_broken/example.txt` for an example.
