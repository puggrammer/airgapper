""" pytest -rP 
-k "test_XXX" to test a targeted test function
-x stop on first failure
"""

import os
import sys
import subprocess
from time import sleep
from pathlib import Path

import pytest
from dotenv import load_dotenv

from airgapper.enum import DockerRepository
from airgapper.modules.docker import _get_sanitized_tar_filename
from airgapper.utils import (
    pretty_print_completedprocess,
    pretty_print_response,
)
from airgapper.repositories import HarborHelper, NexusHelper

from tests.testing_utils import cleanup_output_directory


load_dotenv()
OUTPUT_DIR = "./output/test/docker"

# Harbor Config
HARBOR_URL = os.environ["AIRGAPPER_HARBOR_URL"]
HARBOR_USER = os.environ["AIRGAPPER_HARBOR_USER"]
HARBOR_PASS = os.environ["AIRGAPPER_HARBOR_PASS"]
HARBOR_PROJECT = os.environ["AIRGAPPER_HARBOR_PROJECT"]

# Nexus Config
NEXUS_URL = os.environ["AIRGAPPER_NEXUS_URL"]
NEXUS_DOCKER_URL = os.environ["AIRGAPPER_NEXUS_DOCKER_URL"]
NEXUS_USER = os.environ["AIRGAPPER_NEXUS_USER"]
NEXUS_PASS = os.environ["AIRGAPPER_NEXUS_PASS"]
NEXUS_REPOSITORY = "docker-hosted"

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


def create_nexus_docker_repository(nexus):
    # Check if nexus have created helm repo
    resp = nexus.api_get_docker_repository(NEXUS_REPOSITORY)
    pretty_print_response(resp)
    if resp.status_code == 200:
        print(f"{NEXUS_REPOSITORY} found.")
    elif resp.status_code != 200:
        print(f"{NEXUS_REPOSITORY} not found. Creating it in nexus..")
        resp = nexus.api_create_docker_repository(NEXUS_REPOSITORY)
        pretty_print_response(resp)
        assert resp.status_code == 201
    else:
        sys.exit(1)


@pytest.fixture(scope="session", name="nexus")
def nexus_fixture():
    nexus_helper = NexusHelper(url=NEXUS_URL, repository=NEXUS_REPOSITORY)
    create_nexus_docker_repository(nexus_helper)
    return nexus_helper


# @pytest.fixture(scope="session")
# def nexus_api():
#     nexus = NexusHelper(url=NEXUS_URL, repository=NEXUS_REPOSITORY)
#     create_nexus_docker_repository(nexus)
#     return nexus


@pytest.fixture(scope="session", name="harbor")
def harbor_fixture():
    return HarborHelper(url=HARBOR_URL, project=HARBOR_PROJECT)


@pytest.mark.parametrize("docker_image", ["alpinelinux/unbound:latest-x86_64"])
def test_docker_dl_package_pass(docker_image):
    try:
        # Download
        proc = _docker_download(docker_image)
        assert proc.returncode == 0

        # Check if file downloaded successfully
        _check_if_download_success(docker_image)

    finally:
        cleanup_docker_download(docker_image)
        cleanup_output_directory(OUTPUT_DIR)


@pytest.mark.parametrize("input_txt_file", ["./input/test/dl_docker.txt"])
def test_docker_dl_txt_file_pass(input_txt_file):

    try:
        # Download
        proc = _docker_download(input_txt_file)
        assert proc.returncode == 0

        with open(input_txt_file, "r", encoding='utf8') as f:
            images = [img.strip() for img in f.readlines()]

        # Check if files downloaded successfully
        for docker_image in images:
            _check_if_download_success(docker_image)

        output_tars = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_tars}")
        assert len(output_tars) == len(images)

    finally:
        cleanup_output_directory(OUTPUT_DIR)
        for image in images:
            cleanup_docker_download(image)


@pytest.mark.parametrize("docker_image", ["alpinelinux/unbound:latest-x86_64"])
def test_docker_ul_package_nexus_pass(docker_image, nexus):
    try:
        # Download
        proc = _docker_download(docker_image)
        assert proc.returncode == 0

        # Upload
        output_files = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_files}")
        proc = _docker_upload_nexus(output_files[0])
        assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if file is uploaded.")
        image_name, image_tag = docker_image.split(":")
        params = {"docker.imageName": image_name, "docker.imageTag": image_tag}
        resp = nexus.api_search_file(**params)
        assert len(resp.json().get("items")) == 1

    finally:
        cleanup_docker_download(docker_image)
        cleanup_output_directory(OUTPUT_DIR)
        nexus.api_delete_repo()


@pytest.mark.parametrize("input_txt_file", ["./input/test/dl_docker.txt"])
def test_docker_ul_directory_nexus_pass(input_txt_file, nexus):
    try:
        # Download txt file
        proc = _docker_download(input_txt_file)
        assert proc.returncode == 0

        # Upload
        output_files = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_files}")
        proc = _docker_upload_nexus(OUTPUT_DIR)
        assert proc.returncode == 0

        with open(input_txt_file, "r", encoding='utf8') as f:
            images = [img.strip() for img in f.readlines()]

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if files are uploaded.")
        for image in images:
            image_name, image_tag = image.split(":")
            params = {"docker.imageName": image_name, "docker.imageTag": image_tag}
            resp = nexus.api_search_file(**params)
            assert len(resp.json().get("items")) == 1

    finally:
        cleanup_output_directory(OUTPUT_DIR)
        for image in images:
            cleanup_docker_download(image)
        nexus.api_delete_repo()


def test_docker_ul_harbor_missing_repo_fail():
    proc = subprocess.run(
        [
            "python",
            "-m",
            "airgapper",
            "docker",
            "upload",
            OUTPUT_DIR,
            "-a",
            DockerRepository.HARBOR,
            "-r",
            HARBOR_URL,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    pretty_print_completedprocess(proc)
    assert proc.returncode > 0


@pytest.mark.parametrize("docker_image", ["alpinelinux/unbound:latest-x86_64"])
def test_docker_ul_package_harbor_pass(docker_image, harbor):
    try:
        # Download
        proc = _docker_download(docker_image)
        assert proc.returncode == 0

        # Upload
        output_files = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_files}")
        proc = _docker_upload_harbor(output_files[0])
        assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if file is uploaded.")
        image_name, image_tag = docker_image.split(":")
        resp = harbor.api_search_file(image_name)
        assert len(resp.json()) >= 1
        print(f"{image_name} detected in {HARBOR_PROJECT}")

    finally:
        cleanup_docker_download(docker_image)
        cleanup_output_directory(OUTPUT_DIR)
        harbor.api_delete_project()


@pytest.mark.parametrize("input_txt_file", ["./input/test/dl_docker.txt"])
def test_docker_ul_directory_harbor_pass(input_txt_file, harbor):
    try:
        # Download txt file
        proc = _docker_download(input_txt_file)
        assert proc.returncode == 0

        # Upload
        output_tars = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_tars}")
        proc = _docker_upload_harbor(OUTPUT_DIR)
        assert proc.returncode == 0

        with open(input_txt_file, "r", encoding="utf8") as f:
            images = [img.strip() for img in f.readlines()]

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if files are uploaded.")
        for image in images:
            image_name, image_tag = image.split(":")
            resp = harbor.api_search_file(image_name)
            assert len(resp.json()) >= 1
            print(f"{image_name} detected in {HARBOR_PROJECT}")

    finally:
        cleanup_output_directory(OUTPUT_DIR)
        for image in images:
            cleanup_docker_download(image)
        harbor.api_delete_project()


def test_docker_ul_package_docker_registry_pass():
    pass


def test_docker_ul_directory_docker_registry_pass():
    pass


#############################################
# Helper
#############################################


def _docker_download(input_str):
    proc = subprocess.run(
        [
            "python",
            "-m",
            "airgapper",
            "docker",
            "download",
            input_str,
            "-o",
            OUTPUT_DIR,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    pretty_print_completedprocess(proc)
    return proc


def _docker_upload_nexus(input_str):
    proc = subprocess.run(
        [
            "python",
            "-m",
            "airgapper",
            "docker",
            "upload",
            input_str,
            "-a",
            DockerRepository.NEXUS.value,
            "-r",
            NEXUS_DOCKER_URL,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    pretty_print_completedprocess(proc)
    return proc


def _docker_upload_harbor(input_str):
    proc = subprocess.run(
        [
            "python",
            "-m",
            "airgapper",
            "docker",
            "upload",
            input_str,
            "-a",
            DockerRepository.HARBOR.value,
            "-r",
            HARBOR_URL,
            "--repo",
            HARBOR_PROJECT,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    pretty_print_completedprocess(proc)
    return proc


def _check_if_download_success(docker_image):
    output_tar_fp = Path(OUTPUT_DIR) / _get_sanitized_tar_filename(docker_image)
    print(f"Checking if {output_tar_fp} exists.")
    assert output_tar_fp.exists()


#############################################
# Cleanup
#############################################
def cleanup_docker_download(image_name):
    print(f"Cleaning up downloaded image {image_name}..")
    subprocess.run(["docker", "rmi", image_name], check=True)


# def cleanup_output_directory():
#     print("Cleaning up downloaded tar files..")
#     for file in list(Path(OUTPUT_DIR).iterdir()):
#         file.unlink(missing_ok=True)
