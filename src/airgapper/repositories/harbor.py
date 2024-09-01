import os
import requests
import subprocess
import getpass
from time import sleep

from airgapper.utils import pretty_print_response, check_docker

class HarborHelper:
    def __init__(self, url, project) -> None:
        self.url = url
        self.project = project
        self.project_url = f"{self.url}/{self.project}"
        
        self.api_url = f"https://{url}/api"
        if os.environ.get("AIRGAPPER_INSECURE"):
            self.api_url = f"http://{url}/api"

        self.get_login_details()

    def login(self):
        check_docker()

        print("Logging in Harbor registry..")
        login_cmd = subprocess.run(
            ["docker", "login", self.url, "-u", self.user, "--password-stdin"],
            capture_output=True,
            text=True,
            input=self.password+'\n'
            )      
        if login_cmd.returncode:
            print("Exception occured during logging in.")
            print(login_cmd.stderr)
            raise Exception("Exception occured during logging in.")
        
        print("Successfully logged in to Harbor registry.")

    def logout(self):
        print("Logging out Harbor registry..")
        subprocess.run(["docker", "logout", self.url])

    def get_login_details(self):
        print("Logging in to Harbor..")
        user = os.getenv("AIRGAPPER_HARBOR_USER")
        pwd = os.getenv("AIRGAPPER_HARBOR_PASS")
        if not user or not pwd:
            user = input("Username:")
            pwd = getpass.getpass(f"Password for {user}:")
        self.user = user
        self.password = pwd


    def api_search_file(self, image_name):
        image_name = image_name.replace('/','%252F')
        for _ in range(3):
            resp = requests.get(
                f"{self.api_url}/v2.0/projects/{self.project}/repositories/{image_name}",
                auth=(self.user, self.password)
            )
            if resp.status_code == 200:
                break
            print("Sleeping for 5s for harbor update..")
            sleep(5)
        pretty_print_response(resp)
        assert resp.status_code == 200
        return resp

    def api_delete_file(self, image_name):
        image_name = image_name.replace('/','%252F')
        resp = requests.delete(
            f"{self.api_url}/v2.0/projects/{self.project}/repositories/{image_name}",
            auth=(self.user, self.password)
        )
        pretty_print_response(resp)
        return resp

    def api_delete_project(self):
        print(f"Listing all respositories in {self.project} in harbor..")
        items_resp = requests.get(
            f"{self.api_url}/v2.0/projects/{self.project}/repositories",
            auth=(self.user, self.password)
        )
        pretty_print_response(items_resp)
        if items_resp.status_code != 200:
            raise Exception(items_resp.text)

        print(f"Deleting all files in repository from harbor..")
        for item in items_resp.json():
            image_name = item.get('name').replace(f"{self.project}/", '')
            print(f"Deleting {image_name} from project: {self.project}..")
            self.api_delete_file(image_name)