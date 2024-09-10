# Deploy samples to the public folder

## Preparing the release branch

1. Create a release branch in internal repo from develop.
2. Update changelog to bump the version of the sample.
3. Create a PR to merge this release branch into main in internal repo. Do not merge yet.
4. Share the release branch candidate with QA


## Publishing the release

1. Make sure you have admin rights on the public repo. https://github.com/Unity-Technologies/unity-cloud-python-sdk-samples
2. Run the script `release\generate_release.py`.
3. In the public repo, publish a PR to the newly created branch. The description of the PR should be latest changelog.
4. Merge release PRs in both internal and public repo.