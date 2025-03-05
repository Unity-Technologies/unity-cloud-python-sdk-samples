# Changelog

All notable changes to this package will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-02-28

### Added
- Added keybidings to quit the application and to go back to the previous question in interactive mode.

### Changed
- Updated Python SDK dependency for bulk_upload to 0.10.6

## [0.3.0] - 2025-02-04

### Added
- Added the column description in the csv to allow edit of individual asset descriptions.
- Add multiple user input validations during the interactive config mode.
- Added `app_settings.json` file to configure applications amount of parallel workers and environment variables when needed.
- Added the capacity to retry step when there's a failure during the pipeline.
- Added a default timeout of 5 mins for http calls to help with the uploads of bigger files.

### Changed
- Organizations and projects are now selected via a list in the interactive config mode and delete mode.

### Fixed
- Bug with special characters when reading CSV files.
- Bug with boolean metadata always being read as false.
- CSV generated headlessly now respect the same template as CSV generated in an interactive run.
- Relative path used to indicate assets location are now supported.
- Fix tags and collection not being added to config when saving it.

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