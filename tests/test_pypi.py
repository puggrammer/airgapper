""" pytest -rP 
-k "test_XXX" to test a targeted test function
-x stop on first failure
"""

import os
import sys
import subprocess
from glob import glob
from pathlib import Path
from time import sleep

import pytest
from dotenv import load_dotenv

from airgapper.enum import DockerRepository
from airgapper.utils import (
    check_docker,
    pretty_print_completedprocess,
    pretty_print_response,
)
from airgapper.repositories import NexusHelper

load_dotenv()
OUTPUT_DIR = "./output/test/pypi"

# Nexus Config
NEXUS_URL = os.environ["AIRGAPPER_NEXUS_URL"]
NEXUS_DOCKER_URL = os.environ["AIRGAPPER_NEXUS_DOCKER_URL"]
NEXUS_USER = os.environ["AIRGAPPER_NEXUS_USER"]
NEXUS_PASS = os.environ["AIRGAPPER_NEXUS_PASS"]
NEXUS_REPOSITORY = "pypi-hosted"


def create_nexus_pypi_repository(nexus):
    # Check if nexus have created helm repo
    resp = nexus.api_get_pypi_repository(NEXUS_REPOSITORY)
    pretty_print_response(resp)
    if resp.status_code == 200:
        print(f"{NEXUS_REPOSITORY} found.")
    elif resp.status_code != 200:
        print(f"{NEXUS_REPOSITORY} not found. Creating it in nexus..")
        resp = nexus.api_create_pypi_repository(NEXUS_REPOSITORY)
        pretty_print_response(resp)
        assert resp.status_code == 201
    else:
        sys.exit(1)


@pytest.fixture(scope="session", name="nexus")
def nexus_fixture():
    nexus = NexusHelper(url=NEXUS_URL, repository=NEXUS_REPOSITORY)
    create_nexus_pypi_repository(nexus)
    return nexus


@pytest.fixture(scope="module", autouse=True)
def startup_containers():
    print("Starting up nexus..")
    check_docker()
    proc = subprocess.run(
        ["docker", "compose", "-f", "bin/nexus/docker-compose.yml", "up", "-d"],
        capture_output=True,
        text=True,
        check=True,
    )
    pretty_print_completedprocess(proc)
    sleep(5)


@pytest.mark.parametrize("package", ["colorama", "iniconfig==2.0.0"])
def test_pypi_dl_package_pass(package):
    try:
        # Download
        proc = _pypi_download(package)
        assert proc.returncode == 0

        # Check if file downloaded successfully
        _check_if_download_success(package)

    finally:
        cleanup_whl_directory(OUTPUT_DIR)


@pytest.mark.parametrize("input_txt_file", ["input/test/dl_pypi_requirements.txt"])
def test_pypi_dl_file_pass(input_txt_file):
    try:
        # Download
        proc = _pypi_download(input_txt_file)
        assert proc.returncode == 0

        # Check if file downloaded successfully
        with open(input_txt_file, "r", encoding='utf8') as f:
            input_list = f.readlines()
        print(input_list)
        # Check output file count match
        assert len(input_list) == len(os.listdir(OUTPUT_DIR))

        # Check if file names match
        for package in input_list:
            _check_if_download_success(package)

    finally:
        cleanup_whl_directory(OUTPUT_DIR)


@pytest.mark.parametrize("package", ["colorama", "iniconfig==2.0.0"])
def test_pypi_ul_package_nexus_pass(package, nexus):
    try:
        # Download
        proc = _pypi_download(package)
        assert proc.returncode == 0

        # Upload
        # One package download can end up with multiple files
        output_files = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_files}")
        for file in output_files:
            proc = _pypi_upload_nexus(file)
            assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if file is uploaded.")
        package_name = package.split('-')[0]
        params = {"pypi.description": package_name}
        resp = nexus.api_search_file(**params)
        assert len(resp.json().get("items")) == 1
        print(f"{package_name} detected in {NEXUS_REPOSITORY}")

    finally:
        cleanup_whl_directory(OUTPUT_DIR)
        nexus.api_delete_repo()


@pytest.mark.parametrize("input_txt_file", ["input/test/dl_pypi_requirements.txt"])
def test_pypi_ul_directory_nexus_pass(input_txt_file, nexus):
    try:
        # Download
        proc = _pypi_download(input_txt_file)
        assert proc.returncode == 0

        # Upload
        # One package download can end up with multiple files
        output_files = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_files}")
        proc = _pypi_upload_nexus(OUTPUT_DIR)
        assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if files are uploaded.")
        for file in output_files:
            package_name = file.name.split("-")[0]
            params = {"pypi.description": package_name}
            resp = nexus.api_search_file(**params)
            assert len(resp.json().get("items")) == 1
            print(f"{package_name} detected in {NEXUS_REPOSITORY}")

    finally:
        cleanup_whl_directory(OUTPUT_DIR)
        nexus.api_delete_repo()


#############################################
# Helper
#############################################


def _pypi_download(input_str):
    proc = subprocess.run(
        ["python", "-m", "airgapper", "pypi", "download", input_str, "-o", OUTPUT_DIR],
        capture_output=True,
        text=True,
        check=True,
    )
    pretty_print_completedprocess(proc)
    return proc


def _pypi_upload_nexus(input_str):
    proc = subprocess.run(
        [
            "python",
            "-m",
            "airgapper",
            "pypi",
            "upload",
            input_str,
            "-a",
            DockerRepository.NEXUS.value,
            "-r",
            NEXUS_URL,
            "--repo",
            NEXUS_REPOSITORY,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    pretty_print_completedprocess(proc)
    return proc


def _check_if_download_success(package):
    # single_package_output_whl = Path(f"iniconfig-2.0.0-py3-none-any.whl")
    package_name = package.split('=')[0]
    package_fp_prefix = f"{Path(OUTPUT_DIR).as_posix()}/{package_name}*.whl"
    print(f"Checking if file with prefix {package_fp_prefix} exists.")
    paths = list(glob(package_fp_prefix))
    print(f"Paths detected with prefix: {paths}")
    assert len(paths) > 0


#############################################
# Cleanup
#############################################


def cleanup_whl_directory(output_dir):
    print("Cleaning up downloaded whl files..")
    for file in list(Path(output_dir).iterdir()):
        file.unlink(missing_ok=True)
