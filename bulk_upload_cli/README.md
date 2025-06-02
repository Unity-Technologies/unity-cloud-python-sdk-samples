# Bulk upload CLI

The Bulk upload Command-Line Interface (CLI) is a cross-platform tool that connects to Asset Manager and executes administrative commands. It lets you to create configuration files that you can save and run from a terminal. Using CLI, you can create and update assets in bulk from your local disk to Asset Manager based on several inputs to match your folder structure. This tool includes an interactive mode that prompts you to provide the necessary information to create and save configuration files for future asset updates.

For more related resources and support services, see [Help & Support](https://cloud.unity.com/home/dashboard-support) page.

## Table of contents
- [Bulk upload CLI](#bulk-upload-cli)
  - [Table of contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
    - [Before you start](#before-you-start)
    - [Licenses](#licenses)
  - [How do I...?](#how-do-i)
    - [Install the tool](#install-the-tool)
    - [Run the tool in interactive mode](#run-the-tool-in-interactive-mode)
    - [Select an action](#select-an-action)
    - [Select the input method](#select-the-input-method)
    - [Validation step](#validation-step)
    - [Use the template.csv file for asset ingestion](#use-the-templatecsv-file-for-asset-ingestion)
    - [Creating a CSV from a Unity Cloud project](#creating-a-csv-from-a-unity-cloud-project)
    - [Edit metadata in the CSV file](#edit-metadata-in-the-csv-file)
    - [Use an existing configuration file](#use-an-existing-configuration-file)
    - [Optimize asset creation and upload](#optimize-asset-creation-and-upload)
    - [Use keybindings](#use-keybindings)
    - [Replicate the folder structure with collections](#replicate-the-folder-structure-with-collections)
    - [Use the CLI tool with a Virtual Private Cloud](#use-the-cli-tool-with-a-virtual-private-cloud)
  - [Troubleshoot](#troubleshoot)
  - [See also](#see-also)
  - [Tell us what you think](#tell-us-what-you-think)

## Prerequisites

> **Note**: To create and update assets from the CLI tool to Asset Manager, you need either the [`Asset Manager Admin`](https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#organization-level-roles) role at the organization level or the [`Asset Manager Contributor`]( https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#project-level-roles) add-on role at the project level. Asset Manager Contributors can update assets only for the projects they have access to. You can upload up to 10 GB on the free tier of Unity Cloud.

### Before you start

Before you create and update assets from the CLI tool to Asset Manager, make sure you have the following:

  - Python installed on your machine.
  - The required permissions. Read more about [how to verify permissions](https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#verify-your-permissions).

   >  **Note**: Asset Manager roles define the permissions that you have for a single Asset Manager project. Your permissions may vary across projects.

  - A Unity Cloud project with the Asset Manager service enabled to upload assets. Learn more about [creating a project in Unity Cloud](https://docs.unity.com/cloud/en-us/asset-manager/new-asset-manager-project) page.
  - An assigned seat if you are part of an entitled organization, that is, an organization with a Pro license or an Enterprise license. Learn more about [how to check your assigned seat](https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#project-level-roles).

### Licenses

The bulk upload sample script is provided under the [Unity ToS license](../LICENSE.md).

## How do I...?

### Install the tool

1. Go to the current folder with your terminal.
2. Run the following help command to install the tool:

   * On Mac: `python3 bulk_cli.py --install`
   * On Windows: `python bulk_cli.py --install`

### Run the tool in interactive mode

1. Go to the current folder with your terminal.
2. Run the following command:

   * On Mac: `python3 bulk_cli.py --create`
   * On Windows: `python bulk_cli.py --create`

### Select an action

Select one of the following actions:

- **Upload local assets**: Upload assets from your local machine to the cloud. See [Select the input method](#select-the-input-method) section for more information.
- **Update assets' metadata**: Update the metadata of existing assets in the cloud. See [Creating a csv from a Unity Cloud project](#creating-a-csv-from-a-unity-cloud-project) section for more information.
### Select the input method

Select one of the following strategies as the input method for bulk asset creation:

- **Listed in a csv respecting the CLI tool template**: Select this option if you built a CSV listing your asset location and details using the provided template.
  * Provide the path to the csv file.
- **In a .unitypackage file**: Select this option if your assets are in a .unitypackage file. The tool extracts the assets from the .unitypackage file and uploads them to the cloud.
  * Provide the path to the .unitypackage file.
- **In a local unity project**: Select this option if your assets are in a local Unity project.
  * Provide the path to the asset folder of the Unity project.
- **In a folder**: Select this option if your assets are in a folder on your local machine.
  * Choose a grouping strategy for the assets:
    - Group files by name: Select this if your assets are following a naming convention, for example, blueasset.fbx, blueasset.png.
![Using the group by name convention](./documentation/group-by-name.png)
    - Group files by folder: Select this if your assets are organized into folders, that is, all relevant files are in distinct folders.
![Using the group by folder convention](./documentation/group-by-folder.png)
    - One file = one asset: Select this if no grouping is necessary. Each file in the asset folder and its subfolders is created as an asset.
    - Confirm if you want automatic preview detection:
      - If you select Yes: any image file with the suffix `_preview` is associated as a preview to a file with the same name .

### Validation step

Before creating assets and uploading their files to the cloud, the CLI tool displays the number of assets to be created and the total file size in bytes. 
The tool prompts you to create a .csv file to review the upload plan. You can edit the .csv file to modify the upload plan. If the results are unsatisfactory, stop the process and start a new run.

>  **Note**: The .csv file created at this step follows the required template and can be reused in subsequent asset ingestions.

### Use the template.csv file for asset ingestion

To manage and customize asset uploads, follow these steps:

1. Open the `template.csv` file in your project directory.
2. Fill out the `template.csv` to create an upload plan that allows customization at the asset level.
3. Run the CLI tool. When prompted, confirm that you have a .csv file and provide its path.
4. This process maps all your assets and their customizations. You can update and reuse the same .csv file over time.

### Creating a CSV from a Unity Cloud project

To create a .csv file from a Unity Cloud project, follow these steps:
1. Run the CLI tool with the `--create` flag.
2. When prompted to choose an action, select `Update assets' metadata`.
3. Answer the subsequent questions normally.
>  **Note**: The files won’t be downloaded or included in the .csv file. Using the `Unity Cloud` assets source will only allow you to update assets tags and metadata.
>  **Note**: Collections won't appear in the .csv file. However, you can still edit this column in the .csv file to update asset collections.

### Edit metadata in the CSV file

You can edit the .csv file to update asset metadata:

- Add a column for each metadata field you want to update.
- The column name must match the metadata name. The column name is the field definition key. 
- The value of the cell must be the new value of the metadata.
- Depending on the metadata type, the value of the cell must be formatted correctly:
  * **Numbers**: Ener a valid number without quotes, for example, `42`.
  * **Multi-select metadata**: Enter a valid JSON array of strings with single quotes, for example, `['value1', 'value2']`.
  * **Other types**: Enter a string double quotes, for example, `"value"`.

>  **Note**: Use the Python SDK to find field definition key of a metadata, or you can create a .csv file from a Unity Cloud project to inspect metadata column names for assets already containing the metadata you want to update.

### Use an existing configuration file

To use an existing configuration file, follow these steps:
1. Run the CLI tool with the `--create` flag.
2. At the end, when prompted to create a configuration file, answer Yes and provide a name of your choice.
3. On the next run with the `--create` flag, you can add the `--config` flag followed by the name of the configuration file you created. All your answers from the first run will be loaded from the configuration file.
4. Alternatively, you can use the `--config-select` flag to select from a list of existing configuration files.

### Optimize asset creation and upload

Depending on your network, the number of assets, and the size of the assets, you can adjust the following settings in the `app_settings.json` file to optimize asset creation and upload:

- `parallelCreationEdit`: The number of assets created and updated in parallel. This setting can be kept high as it's not resource intensive.
- `parallelAssetUpload`: The number of assets that will have their files uploaded in parallel. This setting should be adjusted depending on the size of the assets and the network speed. For large files (>100MB), keep this setting low (3-4) to avoid timeouts.
- `parallelFileUploadPerAsset`: The number of files uploaded in parallel for each asset. This setting should be adjusted depending on the number of files and the network speed. It is recommended to adjust it according to `parallelAssetUpload`, as the total number of files uploaded in parallel will be `parallelAssetUpload * parallelFileUploadPerAsset`.
- `httpTimeout`: The time in seconds before the HTTP client triggers a timeout exception. For very large files (> 1GB) or when on a slow connection, you may need to raise this value.

### Use keybindings

In the interactive mode, to help you navigate the tool more efficiently, the CLI tool provides the following keybindings:
- `Ctrl + Q`: Exit the tool.
- `Ctrl + Z`: Go back to the previous question.

### Replicate the folder structure with collections

During step 4 of the CLI tool, you are prompted to replicate the folder structure with collections. If you select Yes, the CLI tool creates collections in the cloud to match the folder structure of the assets. This is useful when you want to keep the same organization in the cloud as your local machine or Unity project.
You can later apply a global collection to all assets, as assets can belong to multiple collections.


>  **Note**: This question will only appear if you are uploading a Unity package, a local Unity project or using the one file = one asset strategy. When uploading a Unity package or a Unity project, the question won't appear if you're using the embedded dependency strategy.

### Detect previews automatically

When mapping assets using strategies `group files by folder` and `One file = one asset`, you can choose to automatically detect previews. 
The CLI tool will look for image files with one of the following prefixes: `preview`, `previews`, `thumbnail` or `thumbnails`. 
Those files will then be associated to the corresponding asset with the same name.  .This is useful when you have a naming convention for your preview images.

Additionally, no matter the strategy, when an asset contains only an audio file (or an audio file with its .meta file), the preview will be automatically set to the audio file. This won't be shown in the CSV file, but the preview will be set in the cloud nonetheless if no other preview is found.

### Use the CLI tool with a Virtual Private Cloud

To use the CLI tool with a Virtual Private Cloud, you need to set the appropriate environment variables in the `app_settings.json` file. The CLI tool will use these environment variables to connect to the Virtual Private Cloud instead of the Public Cloud.

Here's an example of how to set the environment variables in the `app_settings.json` file:

```json
{
  "environmentVariables": {
    "UNITY_CLOUD_SERVICES_FQDN": "https://your-private-cloud-url.com",
    "UNITY_CLOUD_SERVICES_FQDN_PATH_PREFIX": "/backend",
    "UNITY_CLOUD_SERVICES_OPENID_CONFIGURATION_URL": "https://your-private-cloud-url.com/auth/realms/unity/.well-known/openid-configuration"
  }
}
```

## Troubleshoot

Below are a list of common issues you might encounter while using the CLI Tool:
- `error ModuleNotFoundError: No module named ...`: This can be caused by a incomplete installation. Try uninstalling `unity_cloud` using `pip(3) uninstall unity_cloud`, then reinstall the CLI tool.
- Timeout exception during the upload step: When uploading large files, it is recommended to lower the amount of parallel uploads allowed. To do so, refer to the [Optimize asset creation and upload](#optimize-asset-creation-and-upload) section.

## See also
For more information, see the [Unity Cloud Python SDK](https://docs.unity.com/cloud/en-us/asset-manager/python-sdk) documentation.

## Tell us what you think

Thank you for exploring our project! Please help us improve and deliver greater value by providing your feedback in our [Help & Support](https://cloud.unity.com/home/dashboard-support) page. We appreciate your input!