# Changelog

All notable changes to this package will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-11-19

### Added
- Introduced validation step
- Introduced a confirmation prompt in the console showing the amount of assets and total size in bytes that is going to be uploaded
- Automatic collection creation
- Added strategy one file equal one asset
- In the folder grouping strategy, added an automatic detection of any picture file named "preview", "previews", "thumbanil or "thumbnails" as the asset preview. Picture files in a sub-folder with those name will also be considered previews.
- In the folder grouping strategy, added the capacity to change the depth sub-folder for where to start the grouping.
- Added the capacity to use a csv to map assets and all other steps.
- Added support for metadata for the asset customization.
- Added the Unity Cloud asset source to allow updating metadata and tags of assets in the cloud.
- Added the support for every custom metadata types in the csv file.

### Changed
- Install command now use the pip command to download and install the python SDK.
- Refactored the bulk_upload_cli tool to use a pipeline pattern
- Various user experience and bug fixes

## [0.1.0] - 2024-09-04

Initial release

Features:
- Source code of `bulk_upload_cli`
- Source code of `bulk_download_script`