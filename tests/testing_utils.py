from time import sleep
from pathlib import Path
import requests

from airgapper.utils import pretty_print_response

#############################################
# Test Helpers
#############################################


def cleanup_output_directory(output_dir):
    print("Cleaning up downloaded whl files..")
    for file in list(Path(output_dir).iterdir()):
        file.unlink(missing_ok=True)

#############################################
# Harbor Helpers
#############################################


# def cleanup_harbor_delete_repo():
#     print(f"Listing all respositories in {harbor_project} in harbor..")
#     items_resp = requests.get(
#         f"http://{harbor_url}/api/v2.0/projects/{harbor_project}/repositories",
#         auth=(harbor_user, harbor_pass),
#     )
#     assert items_resp.status_code == 200

#     print(f"Deleting all files in repository from harbor..")
#     for item in items_resp.json():
#         image_name = item.get("name").replace(f"{harbor_project}/", "")
#         print(f"Deleting {image_name} from project: {harbor_project}..")
#         harbor_delete_file(image_name)
