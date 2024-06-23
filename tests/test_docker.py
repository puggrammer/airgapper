""" pytest -rP 
-k "test_XXX" to test a targeted test function
-x stop on first failure
"""

import json
import os
from time import sleep
from urllib import request
import requests
import subprocess
from pathlib import Path
import pytest

from airgapper.enum import DockerRegistry
from airgapper.modules.docker import _get_sanitized_tar_filename
from airgapper.utils import check_docker, pretty_print_completedprocess, pretty_print_response

output_dir = "./output/test/docker"
download_txt_file = "input/test/dl_docker.txt"

single_image_name = "alpinelinux/unbound:latest-x86_64"
single_image_output_tar = _get_sanitized_tar_filename(single_image_name)

output_tar_fp = None

harbor_url = "127.0.1.1:8090"
harbor_user = "admin"
harbor_pass = "Harbor12345"
harbor_project = "library"

nexus_url = "127.0.1.1:8091"
nexus_user = "admin"
nexus_pass = "nexus"
nexus_docker_url = "127.0.1.1:8092"
nexus_repository = "docker-hosted"


# @pytest.fixture(scope="module", autouse=True)
# def startup_containers():
#     print("Starting up harbor..")
#     check_docker()
#     proc = subprocess.run(
#         ["docker", "compose", "-f","bin/harbor/docker-compose.yml","up","-d"],
#         capture_output=True,
#         text=True
#     )
#     pretty_print_completedprocess(proc)
#     sleep(5)

#     print("Starting up nexus..")
#     proc = subprocess.run(
#         ["docker", "compose", "-f","bin/nexus/docker-compose.yml","up","-d"],
#         capture_output=True,
#         text=True
#     )
#     pretty_print_completedprocess(proc)
#     sleep(5)


def test_docker_dl_package_pass():
    try:
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","download",single_image_name,"-o", output_dir],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        output_tar_fp = Path(output_dir)/single_image_output_tar
        print(f"Checking if {output_tar_fp} exists.")
        assert output_tar_fp.exists()
    finally:
        cleanup_docker_download(single_image_name)
        cleanup_output_directory()


def test_docker_dl_file_pass():
    with open(download_txt_file, 'r') as f:
        images = [img.strip() for img in f.readlines()]
        images_count = len(images)
    try:
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","download",download_txt_file,"-o",output_dir],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        txt_file_expected_tars = set([Path(f"{output_dir}/{_get_sanitized_tar_filename(image)}") for image in images])
        output_tars = list(Path(output_dir).iterdir())
        print(f"Files detected in output directory {output_dir}: {output_tars}")

        assert len(output_tars) == images_count
        assert txt_file_expected_tars == set(output_tars)

    finally:
        cleanup_output_directory()
        for image in images:
            cleanup_docker_download(image)


def test_docker_ul_package_nexus_pass():
    os.environ["AIRGAPPER_DOCKER_USER"] = nexus_user
    os.environ["AIRGAPPER_DOCKER_PASS"] = nexus_pass

    try:
        # Download
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","download",single_image_name,"-o", output_dir],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        output_tar_fp = Path(output_dir)/single_image_output_tar
        print(f"Checking if {output_tar_fp} exists.")
        assert output_tar_fp.exists()

        # print("pre-logging in for non-interactive tty")
        # login_cmd = subprocess.run([
        #     "docker", "login", nexus_docker_url,"-u",nexus_user,"-p",nexus_pass], capture_output=True,
        #     text=True)
        # pretty_print_completedprocess(login_cmd)

        # Upload
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","upload",output_tar_fp, "-a", DockerRegistry.NEXUS.value, "-r",nexus_docker_url],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print(f"Checking if file is uploaded.")
        image_name = single_image_name.split(":")[0]
        image_tag = single_image_name.split(":")[1]
        resp = nexus_get_file(image_name, image_tag)
        assert len(resp.json().get("items")) == 1

    finally:
            cleanup_docker_download(single_image_name)
            cleanup_output_directory()
            cleanup_nexus_delete_repo()


def test_docker_ul_directory_nexus_pass():
    os.environ["AIRGAPPER_DOCKER_USER"] = nexus_user
    os.environ["AIRGAPPER_DOCKER_PASS"] = nexus_pass

    try:
        # Download txt file
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","download",download_txt_file,"-o",output_dir],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        with open(download_txt_file, 'r') as f:
            images = [img.strip() for img in f.readlines()]
        txt_file_expected_tars = set([Path(f"{output_dir}/{_get_sanitized_tar_filename(image)}") for image in images])
        output_tars = list(Path(output_dir).iterdir())
        print(f"Files detected in output directory {output_dir}: {output_tars}")
        assert txt_file_expected_tars == set(output_tars), "images in txt file != downloaded tars. Have bug somewhere"

        # Upload
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","upload",output_dir, "-a", DockerRegistry.NEXUS.value, "-r",nexus_docker_url],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        # Validate
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if files are uploaded.")
        for image in images:
            image_name = image.split(":")[0]
            image_tag = image.split(":")[1]
            resp = nexus_get_file(image_name, image_tag)
            assert len(resp.json().get("items")) == 1

    finally:
        cleanup_output_directory()
        for image in images:
            cleanup_docker_download(image)
        cleanup_nexus_delete_repo()


def test_docker_ul_harbor_missing_repo_fail():
    proc = subprocess.run(
        ["python", "-m", "airgapper","docker","upload",output_dir, "-a", DockerRegistry.HARBOR, "-r", harbor_url],
        capture_output=True,
        text=True
    )
    pretty_print_completedprocess(proc)
    assert proc.returncode > 0


def test_docker_ul_package_harbor_pass():
    os.environ["AIRGAPPER_DOCKER_USER"] = harbor_user
    os.environ["AIRGAPPER_DOCKER_PASS"] = harbor_pass

    try:
        # Download
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","download",single_image_name,"-o", output_dir],
            capture_output=True,
            text=True
        )
        assert proc.returncode == 0
        output_tar_fp = Path(output_dir)/single_image_output_tar
        print(f"Checking if {output_tar_fp} exists.")
        assert output_tar_fp.exists()

        # Upload
        # print("pre-login for non-interactive tty")
        # login_cmd = subprocess.run(["docker", "login", harbor_url,"-u",harbor_user,"-p",harbor_pass], capture_output=True,
        #     text=True)
        # pretty_print_completedprocess(login_cmd)

        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","upload",output_dir, "-a", DockerRegistry.HARBOR, "-r", harbor_url, "--repo", harbor_project],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0
        assert proc.stderr == ''

        print(f"Checking if file is uploaded.")
        repo_name = single_image_name.split(":")[0]
        harbor_get_file(repo_name)

    finally:
        cleanup_docker_download(single_image_name)
        cleanup_output_directory()
        cleanup_harbor_delete_repo()


def test_docker_ul_directory_harbor_pass():
    os.environ["AIRGAPPER_DOCKER_USER"] = harbor_user
    os.environ["AIRGAPPER_DOCKER_PASS"] = harbor_pass

    try:
        # Download txt file
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","download",download_txt_file,"-o",output_dir],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        with open(download_txt_file, 'r') as f:
            images = [img.strip() for img in f.readlines()]
        txt_file_expected_tars = set([Path(f"{output_dir}/{_get_sanitized_tar_filename(image)}") for image in images])
        output_tars = list(Path(output_dir).iterdir())
        print(f"Files detected in output directory {output_dir}: {output_tars}")
        assert txt_file_expected_tars == set(output_tars), "images in txt file != downloaded tars. Have bug somewhere"

        # Upload
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker", "upload",output_dir,
             "-a", DockerRegistry.HARBOR.value, "-r",harbor_url,"--repo", harbor_project],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        # Validate
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if files are uploaded.")
        for image in images:
            image_name = image.split(":")[0]
            image_tag = image.split(":")[1]
            resp = harbor_get_file(image_name)
            assert resp.json().get("artifact_count") == 1


    finally:
        cleanup_output_directory()
        for image in images:
            cleanup_docker_download(image)
        cleanup_harbor_delete_repo()

    
def test_docker_ul_package_docker_registry_pass():
    pass

def test_docker_ul_directory_docker_registry_pass():
    pass



#############################################
# Helper
#############################################
def harbor_get_file(image_name):
    for _ in range(3):
        resp = requests.get(
            f"http://{harbor_url}/api/v2.0/projects/{harbor_project}/repositories/{image_name.replace('/','%252F')}",
            auth=(harbor_user, harbor_pass)
        )
        if resp.status_code == 200:
            break
        print("Sleeping for 5s for harbor update..")
        sleep(5)
    pretty_print_response(resp)
    assert resp.status_code == 200
    return resp

def harbor_delete_file(image_name):
    resp = requests.delete(
        f"http://{harbor_url}/api/v2.0/projects/{harbor_project}/repositories/{image_name.replace('/','%252F')}",
        auth=(harbor_user, harbor_pass)
    )
    pretty_print_response(resp)
    return resp

def nexus_get_file(image_name, image_tag):
    for _ in range(3):
        resp = requests.get(
            f"http://{nexus_url}/service/rest/v1/search",
            params={
                "repository": nexus_repository,
                "docker.imageName": image_name,
                "docker.imageTag": image_tag
            },
            auth=(nexus_user, nexus_pass)
        )
        if resp.status_code == 200:
            break
        print("Sleeping for 5s for nexus update..")
        sleep(5)
    pretty_print_response(resp)
    assert resp.status_code == 200
    return resp

def nexus_delete_file(image_id):
    resp = requests.delete(
        f"http://{nexus_url}/service/rest/v1/components/{image_id}",
        auth=(nexus_user, nexus_pass)
    )
    pretty_print_response(resp)
    assert resp.status_code == 204
    return resp

#############################################
# Cleanup
#############################################
def cleanup_docker_download(image_name):
    print(f"Cleaning up downloaded image {image_name}..")
    subprocess.run(["docker","rmi",image_name])


def cleanup_output_directory():
    print("Cleaning up downloaded tar files..")
    for file in list(Path(output_dir).iterdir()):
        file.unlink(missing_ok=True)


def cleanup_nexus_delete_repo():
    # Delete from registry
    print(f"Listing all components in {nexus_repository} in nexus..")
    items_resp = requests.get(
        f"http://{nexus_url}/service/rest/v1/components",
        params={"repository": nexus_repository},
        auth=(nexus_user, nexus_pass)
    )
    print(f"Deleting all files in repository from nexus..")
    for item in items_resp.json().get("items"):
        print(f"Deleting {item.get('name')}:{item.get('version')} from {nexus_repository}..")
        nexus_delete_file(item.get('id'))


def cleanup_harbor_delete_repo():
    print(f"Listing all respositories in {harbor_project} in harbor..")
    items_resp = requests.get(
        f"http://{harbor_url}/api/v2.0/projects/{harbor_project}/repositories",
        auth=(harbor_user, harbor_pass)
    )
    assert items_resp.status_code == 200

    print(f"Deleting all files in repository from harbor..")
    for item in items_resp.json():
        image_name = item.get('name').replace(f"{harbor_project}/", '')
        print(f"Deleting {image_name} from project: {harbor_project}..")
        harbor_delete_file(image_name)
