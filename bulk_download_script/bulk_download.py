from concurrent.futures.thread import ThreadPoolExecutor

import unity_cloud as uc
from pathlib import PurePath, Path
from unity_cloud.models import *


def login_with_user_account():
    uc.identity.user_login.use()
    auth_state = uc.identity.user_login.get_authentication_state()
    if auth_state != uc.identity.user_login.Authentication_State.LOGGED_IN:
        uc.identity.user_login.login()


def download_asset(organization_id: str, project_id: str, asset: Asset, download_path: str, overwrite: bool = False):
    dataset = uc.assets.get_dataset_list(organization_id, project_id, asset.id, asset.version)[0]
    asset_files = uc.assets.get_file_list(organization_id, project_id, asset.id, asset.version, dataset.id)

    with ThreadPoolExecutor(max_workers=10) as executor:
        for file in asset_files:
            file_download_info = FileDownloadInformation(organization_id, project_id, asset.id, asset.version,
                                                         dataset.id, file.path, PurePath(download_path))

            target_file = Path(download_path) / file.path

            if not overwrite and target_file.exists():
                print(f"Skipping download of {file.path} as it already exists", flush=True)
                continue

            print(f"Downloading file: {file.path}", flush=True)
            executor.submit(uc.assets.download_file, file_download_info)


def download_assets(assets: [Asset], org_id: str, project_id: str, download_path: str, overwrite: bool = False):
    for asset in assets:
        print(f"Downloading files for asset: {asset.name}", flush=True)
        download_asset(org_id, project_id, asset, download_path, overwrite)


if __name__ == '__main__':

    uc.initialize()
    login_with_user_account()

    org_id = '<org id>'
    project_id = '<project id>'
    download_directory = 'C:\\path\\to\\download\\directory\\'
    overwrite = False

    include_filter = dict()

    #to search by status uncomment one of the following lines
    #include_filter[SearchableProperties.STATUS] = "Published"
    #include_filter[SearchableProperties.STATUS] = "Draft"

    #to search by tags uncomment one of the following lines and replace <tag_name> with the tag you want to search for
    #include_filter[SearchableProperties.TAGS] = ["<tag_name>""]
    #include_filter[SearchableProperties.FILES_TAGS] = ["<tag_name>""]

    collections = []
    # collections = ['<collection_name>']

    assets = uc.assets.search_assets_in_projects(org_id=org_id, project_ids=[project_id], include_filter=include_filter,
                                                 collections=collections)
    download_assets(assets, org_id, project_id, download_directory, overwrite=overwrite)
