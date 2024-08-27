# Bulk download script

The sample script demonstrates how to use Python SDK to download assets from Unity Cloud Asset Manager.

To connect and find support, join the [Help & Support page](https://cloud.unity.com/home/dashboard-support)!

## Table of contents
- [Bulk download script](#bulk-download-script)
  - [Table of contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
    - [System requirements](#system-requirements)
    - [Licenses](#licenses)
  - [How do I run the sample ?](#how-do-i-run-the-sample-)
    - [1. Edit the  `bulk_download.py` script with your requirements](#1-edit-the--bulk_downloadpy-script-with-your-requirements)
    - [2. Run the script](#2-run-the-script)
  - [See also](#see-also)
  - [Tell us what you think!](#tell-us-what-you-think)

## Prerequisites

### System requirements

To run the script, you need:
- Blender 3.x installed on your machine
- An up-to-date Python SDK wheel installed ( > 0.5.0).
- The right permissions to use Asset Manager. See [Get Started with Asset Manager](https://docs.unity.com/cloud/en-us/asset-manager/get-started) for more details.
- A source project with assets manager enable and assets already uploaded in it.

### Licenses

The bulk download sample script is made available under the [Unity ToS license](./LICENSE.md).

## How do I run the sample ?

To run the sample, follow these steps:

### 1. Edit the  `bulk_download.py` script with your requirements

In the `main` conditional section, you must edit some information to link the sample to your project.

- org_id: Your organization id.
- project_id: Your project id.
- download_directory: must be edited with the path where the assets will be downloaded.
- overwrite: When set to `True`, the script will overwrite the files in the download directory if they already exist. Otherwise, it will skip the download.
- include_filter/exclude_filter/any_filter: This dictionary contains the search criteria to fetch the assets. Some example are written in comments, otherwise please refer to [the Python SDK documentation](https://docs.unity.com/cloud/en-us/asset-manager/python-sdk/manage-assets#create-filter-for-a-search-query) to learn how to use search criteria.
- collections: This list contains the collections to fetch the assets from. Leave it empty to search through all the assets in the project.

### 2. Run the script

With you favorite command line tool, run `python bulk_download.py` in this folder.

## See also

- [Unity Cloud Python SDK documentation](https://docs.unity.com/cloud/en-us/asset-manager/python-sdk)

## Tell us what you think!

Thank you for taking a look at the project! To help us improve and provide greater value, please consider providing feedback in our [Help & Support page](https://cloud.unity.com/home/dashboard-support). Thank you!