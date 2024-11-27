from InquirerPy import inquirer
import unity_cloud as uc


def ask_for_login():
    login_type = inquirer.select(message="Choose authentication method?",
                                 choices=["User login", "Service account"]).execute()

    if login_type == "Service account":
        key_id = inquirer.text(message="Enter your key ID:").execute()
        key = inquirer.secret(message="Enter your key:").execute()

        return key_id, key

    return "", ""


def login(key_id=None, key=None):
    try:
        uc.initialize()
    except Exception as e:
        pass

    if key is not None and key_id != "" and key_id is not None and key != "":
        uc.identity.service_account.use(key_id, key)
    else:
        print("Logging in with user account in progress", flush=True)
        login_with_user_account()


def login_with_user_account():
    uc.identity.user_login.use()
    auth_state = uc.identity.user_login.get_authentication_state()
    if auth_state != uc.identity.user_login.Authentication_State.LOGGED_IN:
        uc.identity.user_login.login()


def delete_assets_in_project():
    key_id, key = ask_for_login()
    login(key_id, key)

    org_id = inquirer.text(message="Enter your organization ID:").execute()
    project_id = inquirer.text(message="Enter your project ID:").execute()

    project_assets = uc.assets.get_asset_list(org_id, project_id)
    confirm = inquirer.confirm(message=f"Are you sure you want to delete {len(project_assets)} assets?").execute()
    if not confirm:
        print("Deletion canceled. Program will exit.")
        exit(0)

    assets_chunks = [project_assets[i:i + 50] for i in range(0, len(project_assets), 50)]

    for chunk in assets_chunks:
        uc.assets.unlink_assets_from_project(org_id, project_id, [asset.id for asset in chunk])

    print(f"Deleted {len(project_assets)} assets.")