import json
import os

from InquirerPy import prompt
from InquirerPy.base.control import Choice

from bulk_upload.models import ProjectUploaderConfig, Strategy
from bulk_upload.assets_uploader import ProjectUploader

project_uploader = ProjectUploader()


def run(write_config: bool = False):
    project_uploader = ProjectUploader()
    key_id, key = ask_for_login()
    project_uploader.login(key_id, key)

    questions = [
        {
            "type": "confirm",
            "message": "Are you uploading assets from a Unity project?",
            "default": False
        }
    ]

    result = prompt(questions=questions)
    if result[0]:
        ask_unity_project_questions(write_config=write_config)
    else:
        ask_non_unity_project_questions(write_config=write_config)


def ask_unity_project_questions(write_config: bool = False):
    questions = [
        {
            "type": "list",
            "message": "Where are the assets located?",
            "choices": ["in a .unitypackage file", "in a folder", Choice(value=None, name="Exit")],
            "default": 0,
        }
    ]
    result = prompt(questions=questions)

    if result[0] == "in a .unitypackage file":
        run_unity_package_strategy(write_config)
    elif result[0] == "in a folder":
        run_non_packaged_strategy(Strategy.SINGLE_FILE_ASSET, write_config)


def ask_non_unity_project_questions(write_config: bool = False):
    questions = [
        {
            "type": "list",
            "message": "Select a strategy:",
            "choices": ["group files by name", "group files by folder", Choice(value=None, name="Exit")],
            "default": 0,
        }
    ]
    result = prompt(questions=questions)

    if result[0] == "group files by name":
        run_non_packaged_strategy(Strategy.NAME_GROUPING, write_config)
    elif result[0] == "group files by folder":
        run_non_packaged_strategy(Strategy.FOLDER_GROUPING, write_config)


def run_non_packaged_strategy(strategy: Strategy, write_config: bool = False):
    config = ProjectUploaderConfig()
    config.strategy = strategy

    questions = [
        {
            "type": "input",
            "message": "Enter the path to the root folder of the assets:",
            "default": ""
        },
        {
            "type": "input",
            "message": "Enter your organization ID:",
            "default": ""
        },
        {
            "type": "input",
            "message": "Enter your project ID:",
            "default": ""
        },
        {
            "type": "confirm",
            "message": "Would you like to update existing assets?",
            "default": True
        },
        {
            "type": "input",
            "message": "Enter the tags to apply to the assets (comma separated; leave empty to assign no tag):",
        }
    ]

    if strategy == Strategy.NAME_GROUPING or strategy == Strategy.SINGLE_FILE_ASSET:
        questions.append({
            "type": "input",
            "message": "Enter the file extensions to include (comma separated; leave empty to include everything in the search):",
            "default": ""
        })

    if strategy == Strategy.NAME_GROUPING:
        questions.append({
            "type": "confirm",
            "message": "Is the asset name case sensitive?",
            "default": False
        })
        questions.append({
            "type": "input",
            "message": "Enter the files that are common to every asset (comma separated; leave empty if there are none):",
            "default": ""
        })

    result = prompt(questions=questions)

    config.assets_path = sanitize_string(result[0])
    config.org_id = result[1]
    config.project_id = result[2]
    config.update_files = result[3]

    config.tags = sanitize_tags(result[4])

    if strategy == Strategy.NAME_GROUPING or strategy == Strategy.SINGLE_FILE_ASSET:
        config.file_extensions = result[5].split(",") if result[5] != "" else []

    if strategy == Strategy.NAME_GROUPING:
        config.case_sensitive = result[6]
        config.files_common_to_every_assets = result[7].split(",") if result[7] != "" else []

    try:
        collections = project_uploader.get_collections(config.org_id, config.project_id)
    except Exception as e:
        collections = []

    collections.append(Choice(value=None, name="No collection"))

    questions = [
        {
            "type": "list",
            "message": "Select the collection you want to link the assets to.",
            "choices": collections,
            "default": 0,
        }]

    result = prompt(questions=questions)
    config.collection = result[0] if result[0] != "No collection" else ""

    if write_config:
        write_config_file(config)
    else:
        questions = [{
            "type": "confirm",
            "message": "Would you like to save the config of this run?",
            "default": False
        }]

        result = prompt(questions=questions)

        if result[0]:
            write_config_file(config)

        project_uploader.run(config, True)


def run_unity_package_strategy(write_config: bool = False):
    questions = [
        {
            "type": "input",
            "message": "Enter the path to the Unity package:",
            "default": ""
        },
        {
            "type": "input",
            "message": "Enter your organization ID:",
            "default": ""
        },
        {
            "type": "input",
            "message": "Enter your project ID:",
            "default": ""
        },
        {
            "type": "confirm",
            "message": "Would you like to update existing assets?",
            "default": True
        },
        {
            "type": "input",
            "message": "Enter the tags to apply to the assets (comma separated; leave empty to assign no tag):",
        }
    ]

    result = prompt(questions=questions)

    config = ProjectUploaderConfig()
    config.strategy = Strategy.UNITY_PACKAGE
    config.assets_path = sanitize_string(result[0])
    config.org_id = result[1]
    config.project_id = result[2]
    config.update_files = result[3]
    config.tags = sanitize_tags(result[4])

    try:
        collections = project_uploader.get_collections(config.org_id, config.project_id)
    except Exception as e:
        collections = []

    collections.append(Choice(value=None, name="No collection"))

    questions = [
        {
            "type": "list",
            "message": "Select the collection you want to link the assets to.",
            "choices": collections,
            "default": 0,
        }]

    result = prompt(questions=questions)
    config.collection = result[0] if result[0] != "No collection" else ""


    if write_config:
        write_config_file(config)
    else:
        questions = [{
            "type": "confirm",
            "message": "Would you like to save the config of this run?",
            "default": False
        }]

        result = prompt(questions=questions)

        if result[0]:
            write_config_file(config)

        project_uploader.run(config, True)


def ask_for_login():
    questions = [{
        "type": "list",
        "message": "Choose authentication method?",
        "choices": ["User login", "Service account"],
        "default": 0,
    }]

    result = prompt(questions=questions)

    if result[0] == "Service account":
        questions = [
            {
                "type": "input",
                "message": "Enter your key ID:",
                "default": ""
            },
            {
                "type": "password",
                "message": "Enter your key:",
                "default": ""
            }
        ]

        result = prompt(questions=questions)

        return result[0], result[1]

    return "", ""


def write_config_file(config: ProjectUploaderConfig):
    questions = [
        {
            "type": "input",
            "message": "Enter the name to save the configuration file:",
            "default": ""
        }
    ]
    result = prompt(questions=questions)
    file_name = result[0] if result[0].endswith(".json") else result[0] + ".json"
    with open(file_name, "w") as f:
        f.write(config.to_json())
    print("Configuration saved to", file_name)


def run_with_config_select():
    config_files = [f for f in os.listdir() if f.endswith(".json")]
    if len(config_files) == 0:
        print("No configuration files found in the current directory. Please create a configuration file first.")
        return

    questions = [
        {
            "type": "list",
            "message": "Select a configuration file:",
            "choices": config_files,
            "default": 0
        }
    ]

    result = prompt(questions=questions)
    with open(result[0], "r") as f:
        config = ProjectUploaderConfig()
        config.load_from_json(json.load(f))
        project_uploader.run(config, False)


def sanitize_tags(tags: str) -> list[str]:

    tags = [tag for tag in tags.split(",") if tag != ""]
    return_tags = []
    for tag in tags:
        if tag == "":
            continue

        tag = sanitize_string(tag)
        return_tags.append(tag)

    return return_tags


def sanitize_string(value: str) -> str:
    while value.startswith(" ") or value.endswith(" "):
        if value.startswith(" "):
            value = value[1:]
        if value.endswith(" "):
            value = value[:-1]

    return value