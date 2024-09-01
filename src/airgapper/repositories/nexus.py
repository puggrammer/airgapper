import requests
import os
import getpass
import subprocess
from time import sleep
from pathlib import Path

from airgapper.utils import pretty_print_response, check_docker

class NexusHelper:
    def __init__(self, url, repository) -> None:
        self.url = url
        self.repository = repository
        self.api_url = f"{url}/service/rest"

        self.get_login_details()

    def get_login_details(self):
        user = os.getenv("AIRGAPPER_NEXUS_USER")
        pwd = os.getenv("AIRGAPPER_NEXUS_PASS")
        if not user or not pwd:
            print("Please enter credentials for Nexus..")
            user = input("Username:")
            pwd = getpass.getpass(f"Password for {user}:")
        self.user = user
        self.password = pwd

    def login_docker(self):
        check_docker()

        print("Logging in Nexus docker registry..")
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
        print("Successfully logged in to Nexus docker registry.")

    def logout_docker(self):
        print("Logging out Nexus docker registry..")
        subprocess.run(["docker", "logout", self.url])

    def api_search_file(self, **kwargs):
        for _ in range(3):
            resp = requests.get(
                f"{self.api_url}/v1/search",
                params={"repository": self.repository, **kwargs},
                auth=(self.user, self.password),
            )
            if resp.status_code == 200:
                break
            print("Sleeping for 5s for nexus update..")
            sleep(5)
        return resp

    def api_delete_file(self, image_id):
        resp = requests.delete(
            f"{self.api_url}/v1/components/{image_id}",
            auth=(self.user, self.password)
        )
        return resp

    def api_delete_repo(self):
        # Delete from registry
        print(f"Listing all components in {self.repository} in nexus..")
        items_resp = requests.get(
            f"{self.api_url}/v1/components",
            params={"repository": self.repository},
            auth=(self.user, self.password),
        )
        print(f"Deleting all files in repository from nexus..")
        for item in items_resp.json().get("items"):
            print(
                f"Deleting {item.get('name')}:{item.get('version')} from {self.repository}.."
            )
            self.api_delete_file(item.get("id"))

    def api_get_repository(self, repository_type, repository):
        resp = requests.get(
            f"{self.api_url}/v1/repositories/{repository_type}/hosted/{repository}",
            auth=(self.user, self.password)
        )
        return resp
    
    def api_get_helm_repository(self, repository):
        return self.api_get_repository("helm", repository)
    
    def api_get_pypi_repository(self, repository):
        return self.api_get_repository("pypi", repository)

    def api_get_docker_repository(self, repository):
        return self.api_get_repository("docker", repository)
        
    def api_create_helm_repository(self, repository):
        resp = requests.post(
            f"{self.api_url}/v1/repositories/helm/hosted",
            auth=(self.user, self.password),
            json={
                "name": repository,
                "online":True,
                "storage": {
                    "blobStoreName": "default",
                    "writePolicy": "allow",
                    "strictContentTypeValidation": True
                }}
        )
        assert resp.status_code == 201
        print(f"Repo {repository} created in Nexus!")
        self.repository = repository
        return resp

    def api_create_pypi_repository(self, repository):
        resp = requests.post(
            f"{self.api_url}/v1/repositories/pypi/hosted",
            auth=(self.user, self.password),
            json={
                "name": repository,
                "online":True,
                "storage": {
                    "blobStoreName": "default",
                    "writePolicy": "allow",
                    "strictContentTypeValidation": True
                }}
        )
        assert resp.status_code == 201
        print(f"Repo {repository} created in Nexus!")
        self.repository = repository
        return resp

    def api_create_docker_repository(self, repository):
        resp = requests.post(
            f"{self.api_url}/v1/repositories/docker/hosted",
            auth=(self.user, self.password),
            json={
                "name": repository,
                "online":True,
                "storage": {
                    "blobStoreName": "default",
                    "writePolicy": "allow",
                    "strictContentTypeValidation": True
                },
                "docker": {
                    "v1Enabled": False,
                    "forceBasicAuth": True,
                    "httpPort": 8092,
                }
            }
        )
        assert resp.status_code == 201
        print(f"Repo {repository} created in Nexus!")
        self.repository = repository
        return resp
    
    def api_upload_helm_component(self, file:Path):
        resp = requests.post(
            f"{self.api_url}/v1/components",
            params={"repository": self.repository},
            headers={"accept": "application/json"}, # "Content-Type": "multipart/form-data"
            files={"helm.asset": (file.name, open(file, 'rb'))},
            auth=(self.user, self.password)
            )
        return resp
    
    def api_upload_pypi_component(self, file):
        resp = requests.post(
            f"{self.api_url}/v1/components",
            params={"repository": self.repository},
            headers={"accept": "application/json"}, # "Content-Type": "multipart/form-data"
            files={"pypi.asset": (file.name, open(file, 'rb'))},
            auth=(self.user, self.password)
            )
        return resp
