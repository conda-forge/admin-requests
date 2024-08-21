<!--
Hi!

Thank you for making an admin request on this repo. We strive to make a decision
on these requests within 24 hours. 

Please use the text below to add context about this PR, especially if:
- You want to mark packages as broken
- You want to archive a feedstock
- You want to request access to opt-in CI resources

Cheers and thank you for contributing to conda-forge!
-->

## Guidelines for marking packages as broken:

* We prefer to patch the repo data (see [here](https://github.com/conda-forge/conda-forge-repodata-patches-feedstock))
  instead of marking packages as broken. This alternative workflow makes environments more reproducible.
* Packages with requirements/metadata that are too strict but otherwise work are
  not technically broken and should not be marked as such.
* Packages with missing metadata can be marked as broken on a temporary basis
  but should be patched in the repo data and be marked unbroken later.
* In some cases where the number of users of a package is small or it is used by
  the maintainers only, we can allow packages to be marked broken more liberally.
* We (`conda-forge/core`) try to make a decision on these requests within 24 hours.

What will happen when a package is marked broken?

* Our bots will add the `broken` label to the package. The `main` label will remain on the package and this is normal.
* Our bots will rebuild our repodata patches to remove this package from the repodata.
* In a few hours after the `anaconda.org` CDN picks up the new patches, you will no longer be able to install the package from the `main` channel.


## Checklist:

* [ ] I want to mark a package as broken (or not broken):
  * [ ] Added a description of the problem with the package in the PR description.
  * [ ] Pinged the team for the package for their input.

* [ ] I want to archive a feedstock:
  * [ ] Pinged the team for that feedstock for their input.
  * [ ] Make sure you have opened an issue on the feedstock explaining why it was archived.
  * [ ] Linked that issue in this PR description.
  * [ ] Added links to any other relevant issues/PRs in the PR description.

* [ ] I want to request (or revoke) access to an opt-in CI resource:
  * [ ] Pinged the relevant feedstock team(s)
  * [ ] Added a small description explaining why access is needed

* [ ] I want to copy an artifact following [CFEP-3](https://github.com/conda-forge/cfep/blob/main/cfep-03.md):
  * [ ] Pinged the relevant feedstock team(s)
  * [ ] Added a reference to the original PR
  * [ ] Posted a link to the conda artifacts
  * [ ] Posted a link to the build logs

<!--
For example if you are trying to mark a `foo` conda package as broken.

  ping @conda-forge/foo

-->
