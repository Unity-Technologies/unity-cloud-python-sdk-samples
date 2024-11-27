# Bulk download script

This sample script demonstrates how you can use Python SDK to download assets from Unity Cloud Asset Manager.

Find and connect support services on the [Help & Support](https://cloud.unity.com/home/dashboard-support) page.

## Table of contents
- [Bulk download script](#bulk-download-script)
  - [Table of contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
    - [Before you start](#before-you-start)
    - [Licenses](#licenses)
  - [Run the sample](#run-the-sample)
  - [See also](#see-also)
  - [Tell us what you think](#tell-us-what-you-think)

## Prerequisites

> **Note**: To download assets from Asset Manager, you need the [`Asset Manager Admin`](https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#organization-level-roles) role at the organization level or the [`Asset Manager Contributor`]( https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#project-level-roles) add-on role at the project level. Asset Manager Contributors can update assets only for the specific projects to which they have access.

### Before you start

Before you download assets from Unity Cloud Asset Manager, make sure you have the following:

- Python installed on your machine.
- An up-to-date Python SDK wheel installed ( > 0.5.0).
- The required permissions. Read more about [verifying permissions](https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#verify-your-permissions).

   >  **Note**: Asset Manager roles define the permissions that you have for a single Asset Manager project. Depending on your work, permissions may vary across projects.

- A Unity Cloud source project with the Asset Manager service enabled to download assets. Read more about [creating a project in Unity Cloud](https://docs.unity.com/cloud/en-us/asset-manager/new-asset-manager-project) page.

- A Unity Cloud source project with asset manager service enabled to download assets and assets already uploaded in it. For more information on how to create a new project on Unity Cloud, see the [Create a new project](https://docs.unity.com/cloud/en-us/asset-manager/new-asset-manager-project) page.

### Licenses

The bulk download sample script is provided under the [Unity ToS license](../LICENSE.md).

## Run the sample

To run the sample, follow these steps:

1. Link the sample to your project by editing the following information in the `main` conditional section of the `bulk_download.py` script.

   - org_id: Enter your organization ID.
   - project_id: Enter your project ID.
   - download_directory: Enter the path to the directory where you download the assets.
   - overwrite: Set to `True` to overwrite already existing files in the download directory. If you set it to `False`, the script skips the download process for existing files.
   - include_filter, exclude_filter, or any_filter: If you want to add include, exclude, or any filters to your request, build them as described in the [Unity Cloud Python SDK](https://docs.unity.com/cloud/en-us/asset-manager/python-sdk/manage-assets#create-filter-for-a-search-query) documentation.
   
   >  **Note**: The script contains commented code that shows an example of filter usage to help you with the integration of custom filters. However, these comments do not cover the entire filter creation process. For comprehensive details, see the [Unity Cloud Python SDK](https://docs.unity.com/cloud/en-us/asset-manager/python-sdk/manage-assets#create-filter-for-a-search-query) documentation. 
   
   - collections: Fill the `collections` list with the names of those collections from which you want to fetch your assets. Leave the `collections` list empty if you want to search through the whole project.

2. Run the script:

   1. Go to the current folder with a command line tool.
   2. Run the following command:  `python bulk_download.py`.

## See also

For more information, see the [Unity Cloud Python SDK](https://docs.unity.com/cloud/en-us/asset-manager/python-sdk) documentation.

## Tell us what you think

Thank you for exploring our project! Please help us improve and deliver greater value by providing your feedback in our [Help & Support](https://cloud.unity.com/home/dashboard-support) page. We appreciate your input!
