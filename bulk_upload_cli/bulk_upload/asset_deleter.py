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

    organizations = uc.identity.get_organization_list()
    if len(organizations) == 0:
        print("No organizations found. Please create an organization first.")
        exit(1)
    org_selected = inquirer.select(message="Select an organization:",
                                   choices=[org.name for org in organizations]).execute()
    org_id = [org.id for org in organizations if org.name == org_selected][0]

    projects = uc.identity.get_project_list(org_id)
    if len(projects) == 0:
        print("No projects found. Please create a project first.")
        exit(1)

    selected_project = inquirer.select(message="Select a project:",
                                       choices=[project.name for project in projects]).execute()
    project_id = [project.id for project in projects if project.name == selected_project][0]

    project_assets = uc.assets.get_asset_list(org_id, project_id)
    confirm = inquirer.confirm(message=f"Are you sure you want to delete {len(project_assets)} assets?").execute()
    if not confirm:
        print("Deletion canceled. Program will exit.")
        exit(0)

    assets_chunks = [project_assets[i:i + 50] for i in range(0, len(project_assets), 50)]

    for chunk in assets_chunks:
        uc.assets.unlink_assets_from_project(org_id, project_id, [asset.id for asset in chunk])

    print(f"Deleted {len(project_assets)} assets.")