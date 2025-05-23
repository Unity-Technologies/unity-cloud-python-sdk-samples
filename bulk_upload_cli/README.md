# Bulk upload CLI

The Bulk upload Command-Line Interface (CLI) is a cross-platform command-line tool to connect to Asset Manager and execute administrative commands. It allows you to create configuration files that you can save and run from a terminal. Using CLI, you can create and update assets in bulk from your local disk to Asset Manager based on several inputs to match your folder structure. This tool offers an interactive mode where you are prompted to provide the necessary information to create and save configuration files for future asset updates.

Find and connect support services on the [Help & Support](https://cloud.unity.com/home/dashboard-support) page.

## Table of contents
- [Bulk upload CLI](#bulk-upload-cli)
  - [Table of contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
    - [Before you start](#before-you-start)
    - [Licenses](#licenses)
  - [How do I...?](#how-do-i)
    - [Install the tool](#install-the-tool)
    - [Run the tool in interactive mode](#run-the-tool-in-interactive-mode)
    - [Select the input method](#select-the-input-method)
	- [Validation step](#validation-step)
	- [Use the template.csv file for asset ingestion](#use-the-templatecsv-file-for-asset-ingestion)
	- [Creating a csv from a Unity Cloud project](#creating-a-csv-from-a-unity-cloud-project)
    - [Editing metadata in the csv file](#editing-metadata-in-the-csv-file)
    - [Use an existing configuration file](#use-an-existing-configuration-file)
    - [Fine-tune the asset creation and upload](#fine-tune-the-asset-creation-and-upload)
    - [Use keybindings](#use-keybindings)
  - [Troubleshoot](#troubleshoot)
  - [See also](#see-also)
  - [Tell us what you think](#tell-us-what-you-think)

## Prerequisites

> **Note**: To create and update assets from the CLI tool to Asset Manager, you need the [`Asset Manager Admin`](https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#organization-level-roles) role at the organization level or the [`Asset Manager Contributor`]( https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#project-level-roles) add-on role at the project level. Asset Manager Contributors can update assets only for the specific projects to which they have access. You can upload up to 10 GB on the free tier of Unity Cloud.

### Before you start

Before you create and update assets from the CLI tool to Asset Manager, make sure you have the following:

  - Python installed on your machine.
  - The required permissions. Read more about [verifying permissions](https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#verify-your-permissions).

   >  **Note**: Asset Manager roles define the permissions that you have for a single Asset Manager project. Depending on your work, permissions may vary across projects.

  - A Unity Cloud project with the Asset Manager service enabled to upload assets. Read more about [creating a project in Unity Cloud](https://docs.unity.com/cloud/en-us/asset-manager/new-asset-manager-project) page.
  - An assigned seat if you are part of an entitled organization, that is, an organization with a Pro license or an Enterprise license. Read more about [checking your assigned seat](https://docs.unity.com/cloud/en-us/asset-manager/org-project-roles#project-level-roles).

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

Select one of the two possible actions:

- **Upload local assets**: Select this option to upload assets from your local machine to the cloud. See the [Select the input method](#select-the-input-method) section for more information.
- **Update assets' metadata**: Select this option to update the metadata of assets in the cloud. See the [Creating a csv from a Unity Cloud project](#creating-a-csv-from-a-unity-cloud-project) section for more information.
### Select the input method

Select one of the four strategies as the input method for bulk asset creation:

- **listed in a csv respecting the CLI tool template**: Select this option if you built a CSV listing your assets location and details using the provided template.
  * Provide the path to the csv file.
- **in a .unitypackage file**: Select this option if your assets are in a .unitypackage file. The tool extracts the assets from the .unitypackage file and uploads them to the cloud.
  * Provide the path to the .unitypackage file.
- **in a local unity project**: Select this option if your assets are in a local Unity project.
  * Provide the path to the asset folder of the Unity project.
- **in a folder**: Select this option if your assets are in a folder on your local machine.
  * Chose the grouping strategy for the assets:
    - group files by name: Select this option if your assets are following a naming convention, for example, blueasset.fbx, blueasset.png.
![Using the group by name convention](./documentation/group-by-name.png)
    - group files by folder: Select this option if your assets are organized by folder, that is, all relevant files are in distinct folders.
![Using the group by folder convention](./documentation/group-by-folder.png)
    - one file = one asset: Select this option if no grouping is necessary. Each file in the asset folder and its subfolders is created as an asset.
    - Confirm if you want automatic preview detection:
      - If you said yes: any picture file with the suffix `_preview` will be associated to the file of the same name as a preview.

### Validation step

Before creating assets and uploading their files to the cloud, the CLI tool displays the number of assets to be created and the total size in bytes of the files that will be uploaded. 
The tool prompts you to create a .csv file to review the upload plan. Edit the .csv file to modify the upload plan. If the results are not satisfactory, stop the process and start a new run.

>  **Note**: The .csv file created at this step is applicable for use in subsequent asset ingestions because it follows the required template.

### Use the template.csv file for asset ingestion

To manage and customize the upload of assets, create an upload plan as follows:

1. Go to the `template.csv` file in your project directory.
2. Fill out the `template.csv` to create an upload plan that allows customization at the asset level.
3. Run the CLI tool, and when prompted about having a .csv file, answer yes and link the .csv file that you created.
4. This process maps all your assets and their customizations. Update and reuse the same .csv file over time to manage your assets in the cloud.

### Creating a csv from a Unity Cloud project

To create a .csv file from a Unity Cloud project, follow these steps:
1. Run the CLI tool with the `--create` flag.
2. When prompted to chose an action, select `Update assets' metadata`.
3. Answer the next questions normally.
>  **Note**: The files won't be downloaded nor will they appear in the .csv file. Using the `Unity Cloud` assets source will only allow you to update assets tags and metadata.
>  **Note**: The collection won't appear in the csv as this is a known limitation at the moment. You can still edit this colum in the csv file to update the collection of the assets.

### Editing metadata in the csv file

The csv file generated by the CLI tool can be edited to update the metadata of the assets. To do so, you must add, in the csv, a column for each metadata you want to update. The column name must be the metadata name. The column name is the field definition key. The value of the cell must be the new value of the metadata.
To find the field definition key of a metadata, you can use directly the python SDK. Alternatively, you can create a csv file from a Unity Cloud project and look at the metadata column names for assets already containing the metadata you want to update.

Depending on the metadata type, the value of the cell must be formatted differently:
- For a number, the value must be a a valid number and written without quotes. (e.g. `42`)
- For a multi-select metadata, the value must be a valid json array of strings with single quotes. (e.g. `['value1', 'value2']`)
- For everything else, the value must be a string and written with quotes. (e.g. `"value"`)

### Use an existing configuration file

To use an existing configuration file, follow these steps:
1. Run the CLI tool with the `--create` flag.
2. At the end, when prompted to create a configuration file, answer yes and give it a name of your choice.
3. On the next run with the `--create` flag, you can add the `--config` flag followed by the name of the configuration file you created. All the answers you gave during the first run will be loaded from the configuration file.
4. Alternatively, you can use the `--config-select` flag to select a configuration file from the list of existing configuration files.

### Fine-tune the asset creation and upload

With the `app_settings.json` file, you can fine-tune the amount of assets created and uploaded in parallel. Depending on your network, the number of assets, and the size of the assets, you can adjust the following settings:
- `parallelCreationEdit`: The number of assets created and updated in parallel. This settings can be kept high as it is not resource intensive.
- `parallelAssetUpload`: The number of assets that will have their files uploaded in parallel. This setting should be adjusted depending on the size of the assets and the network speed. When dealing with large files (>100MB), it is recommended to keep this setting low (3-4) to avoid time out.
- `parallelFileUploadPerAsset`: The number of files uploaded in parallel for each asset. This setting should be adjusted depending on the number of files and the network speed. It is recommended to adjust it according to `parallelAssetUpload`, as the total number of files uploaded in parallel will be `parallelAssetUpload * parallelFileUploadPerAsset`.
- `httpTimeout`: The time (in seconds) before the http client triggers a timeout exception. When handling very large files (> 1GB) or when on a slow connection, it might be necessary to raise this value.

In the `app_settings.json` file, you can also add environment variables that will be set at runtime. This is useful when running the CLI tool in a private network environment.

### Use keybindings

When used in interactive mode, the CLI tool provides keybindings to help you navigate the tool more efficiently. The keybindings are as follows:
- `Ctrl + Q`: Exit the tool.
- `Ctrl + Z`: Go back to the previous question.

### Replicate the folder structure with collections

During step 4 of the CLI tool, you will be prompted about replicating the folder structure with collections. If you answer yes, the CLI tool will create collections in the cloud to match the folder structure of the assets. This is useful when you want to keep the same organization in the cloud as on your local machine or a unity project.
You can still add afterward a global collection to be applied to all assets, since assets can be in multiple collections.

>  **Note**: This question will only appear if you are uploading a unity package, a local unity project or using the `one file = one asset` strategy. When uploading a unity package or a unity project, the question won't appear when using the embedded dependency strategy.

## Troubleshoot

Here's a list of common problems you might encounter while using the CLI Tool.
- `error ModuleNotFoundError: No module named ...`: This can be caused by a uncompleted installation. Start by uninstalling `unity_cloud` with `pip(3) uninstall unity_cloud`, then re-run the CLI tool installation.
- Timeout exception during the upload step: When uploading large files, it is recommended to lower the amount of parallel uploads allowed. To do so, refer to the [Fine-tune the asset creation and upload](#fine-tune-the-asset-creation-and-upload) section.

## See also
For more information, see the [Unity Cloud Python SDK](https://docs.unity.com/cloud/en-us/asset-manager/python-sdk) documentation.

## Tell us what you think

Thank you for exploring our project! Please help us improve and deliver greater value by providing your feedback in our [Help & Support](https://cloud.unity.com/home/dashboard-support) page. We appreciate your input!