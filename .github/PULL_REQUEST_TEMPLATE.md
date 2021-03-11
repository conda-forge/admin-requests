<!--
Hi!

Thank you for making an admin request on this repo. We strive to make a decision
on these requests within 24 hours. Note that if you are asking for a package to
be marked as broken, please make sure to explain why in the PR text below.

Cheers and thank you for contributing to conda-forge!
-->

Guidelines for marking packages as broken:

* We prefer to patch the repo data (see [here](https://github.com/conda-forge/conda-forge-repodata-patches-feedstock))
  instead of marking packages as broken. This alternative workflow makes environments more reproducible.
* Packages with requirements/metadata that are too strict but otherwise work are
  not technically broken and should not be marked as such.
* Packages with missing metadata can be marked as broken on a temporary basis
  but should be patched in the repo data and be marked unbroken later.
* In some cases where the number of users of a package is small or it is used by
  the maintainers only, we can allow packages to be marked broken more liberally.
* We (`conda-forge/core`) try to make a decision on these requests within 24 hours.

Checklist:

* [ ] Make sure your package is in the right spot (`broken/*` for adding the
  `broken` label, `not_broken/*` for removing the `broken` label, or `token_reset/*`
  for token resets)
* [ ] Added a description of the problem with the package in the PR description.
* [ ] Added links to any relevant issues/PRs in the PR description.
* [ ] Pinged the team for the package for their input.

<!--
For example if you are trying to mark a `foo` conda package as broken.

  ping @conda-forge/foo

-->
