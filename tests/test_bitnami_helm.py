""" pytest -rP 
-k "test_XXX" to test a targeted test function
-x stop on first failure
"""

import re
import os
import sys
import subprocess
from pathlib import Path
from glob import glob
from time import sleep

import pytest
from dotenv import load_dotenv

from airgapper.enum import DockerRepository
from airgapper.repositories import NexusHelper, HarborHelper
from airgapper.utils import pretty_print_completedprocess, pretty_print_response
from tests.testing_utils import cleanup_output_directory

# helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

load_dotenv()

OUTPUT_DIR = "./output/test/helm"

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
NEXUS_REPOSITORY = "helm-hosted"

RGX_PACKAGE_NAME = ".+/(?P<chart_name>[a-z]+),?(?P<chart_version>[.1-9]+)?"
RGX_WRAP_FILE = "(?P<chart_name>[a-z]+)-?(?P<chart_version>[.1-9]+)?.wrap.tgz"


# @pytest.fixture(scope="session")
def create_nexus_helm_repository(nexus):
    # Check if nexus have created helm repo
    resp = nexus.api_get_helm_repository(NEXUS_REPOSITORY)
    pretty_print_response(resp)
    if resp.status_code == 200:
        print(f"{NEXUS_REPOSITORY} found.")
    elif resp.status_code != 200:
        print(f"{NEXUS_REPOSITORY} not found. Creating it in nexus..")
        resp = nexus.api_create_helm_repository(NEXUS_REPOSITORY)
        pretty_print_response(resp)
        assert resp.status_code == 201
    else:
        sys.exit(1)


@pytest.fixture(scope="session", name="nexus")
def nexus_fixture():
    nexus = NexusHelper(url=NEXUS_URL, repository=NEXUS_REPOSITORY)
    create_nexus_helm_repository(nexus)
    return nexus


@pytest.fixture(scope="session", name="harbor")
def harbor_fixture():
    return HarborHelper(url=HARBOR_URL, project=HARBOR_PROJECT)


#############################################
# Download
#############################################


@pytest.mark.parametrize(
    "helm_chart_package",
    [
        "oci://registry-1.docker.io/bitnamicharts/kibana,11.2.17",
        "oci://registry-1.docker.io/bitnamicharts/kibana",
    ],
)
def test_helm_dl_package_pass(helm_chart_package):
    try:
        # Download
        proc = _bitnami_helm_download(helm_chart_package)
        assert proc.returncode == 0

        # Check if file downloaded successfully
        _check_if_download_success(helm_chart_package)

    finally:
        cleanup_output_directory(OUTPUT_DIR)


@pytest.mark.parametrize("input_txt_file", ["./input/test/dl_bitnami_helm.txt"])
def test_helm_dl_txt_file_pass(input_txt_file):
    try:
        # Download
        proc = _bitnami_helm_download(input_txt_file)
        assert proc.returncode == 0

        # Check if file downloaded successfully
        with open(input_txt_file, "r", encoding='utf8') as f:
            input_list = f.readlines()
        print(input_list)
        # Check output file count match
        assert len(input_list) == len(os.listdir(OUTPUT_DIR))

        # Check if file names match
        for chart_package in input_list:
            _check_if_download_success(chart_package)

    finally:
        cleanup_output_directory(OUTPUT_DIR)


@pytest.mark.parametrize("helm_chart_package", ["oci://registry-1.docker.io/bitnamicharts/kibana,11.2.17"])
def test_helm_dl_package_change_dt_dir_pass(helm_chart_package):
    os.environ["AIRGAPPER_DT_DIRECTORY"] = "/home/lchengju/Documents/airgapper/bin/distribution-tooling-for-helm"
    test_helm_dl_package_pass(helm_chart_package)


#############################################
# Upload
#############################################


@pytest.mark.parametrize("helm_chart_package", ["oci://registry-1.docker.io/bitnamicharts/kibana,11.2.17"])
def test_helm_ul_package_nexus_pass(helm_chart_package, nexus):
    try:
        # Download
        proc = _bitnami_helm_download(helm_chart_package)
        assert proc.returncode == 0

        # Upload
        output_files = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_files}")
        assert len(output_files) == 1, "count of package in output dir does not tally."

        proc = _bitnami_helm_upload_nexus(output_files[0])
        assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if files are uploaded.")
        for file in output_files:
            print(file.name)
            rgx_groups = re.search(RGX_WRAP_FILE, file.name)
            if not rgx_groups:
                print("Unable to extract helm chart name")
                raise Exception("Unable to extract helm chart name")
            rgx_groups = rgx_groups.groupdict()
            print(f"regex groups found: {rgx_groups}")

            params = {"name": rgx_groups["chart_name"]}
            if rgx_groups["chart_version"]:
                params["version"] = rgx_groups["chart_version"]
            resp = nexus.api_search_file(**params)

            assert len(resp.json().get("items")) == 1
            print(f"{rgx_groups["chart_name"]} detected in {NEXUS_REPOSITORY}")

    finally:
        cleanup_output_directory(OUTPUT_DIR)
        nexus.api_delete_repo()


@pytest.mark.parametrize("input_txt_file", ["./input/test/dl_bitnami_helm.txt"])
def test_helm_ul_directory_nexus_pass(input_txt_file, nexus):
    try:
        # Download txt file with multiple packages
        proc = _bitnami_helm_download(input_txt_file)
        assert proc.returncode == 0

        # Upload
        output_files = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_files}")

        proc = _bitnami_helm_upload_nexus(OUTPUT_DIR)
        assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if files are uploaded.")
        for file in output_files:
            rgx_groups = re.search(RGX_WRAP_FILE, file.name)
            if not rgx_groups:
                raise Exception("Unable to extract helm chart name")
            rgx_groups = rgx_groups.groupdict()
            print(f"regex groups found: {rgx_groups}")

            params = {"name": rgx_groups["chart_name"]}
            if rgx_groups["chart_version"]:
                params["version"] = rgx_groups["chart_version"]
            resp = nexus.api_search_file(**params)

            assert len(resp.json().get("items")) >= 1
            print(f"{rgx_groups["chart_name"]} detected in {NEXUS_REPOSITORY}")
    finally:
        cleanup_output_directory(OUTPUT_DIR)
        nexus.api_delete_repo()


@pytest.mark.parametrize("helm_chart_package", ["oci://registry-1.docker.io/bitnamicharts/kibana,11.2.17"])
def test_helm_ul_package_harbor_pass(helm_chart_package, harbor):
    try:
        # Download
        proc = _bitnami_helm_download(helm_chart_package)
        assert proc.returncode == 0

        # Upload
        output_files = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_files}")
        proc = _bitnami_helm_upload_harbor(output_files[0])
        assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if files are uploaded.")
        for file in output_files:
            rgx_groups = re.search(RGX_WRAP_FILE, file.name)
            if not rgx_groups:
                raise Exception("Unable to extract helm chart name")
            rgx_groups = rgx_groups.groupdict()
            print(f"regex groups found: {rgx_groups}")

            # params = {"name": rgx_groups["chart_name"]}
            # if rgx_groups["chart_version"]:
            #     params["version"] = rgx_groups["chart_version"]
            resp = harbor.api_search_file(rgx_groups["chart_name"])

            assert len(resp.json()) >= 1
            print(f"{rgx_groups["chart_name"]} detected in {HARBOR_PROJECT}")
    finally:
        cleanup_output_directory(OUTPUT_DIR)
        harbor.api_delete_project()


@pytest.mark.parametrize("input_txt_file", ["./input/test/dl_bitnami_helm.txt"])
def test_helm_ul_directory_harbor_pass(input_txt_file, harbor):
    try:
        # Download
        proc = _bitnami_helm_download(input_txt_file)
        assert proc.returncode == 0

        # Upload
        output_files = list(Path(OUTPUT_DIR).iterdir())
        print(f"Files detected in output directory {OUTPUT_DIR}: {output_files}")

        proc = _bitnami_helm_upload_harbor(OUTPUT_DIR)
        assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if files are uploaded.")
        for file in output_files:
            rgx_groups = re.search(RGX_WRAP_FILE, file.name)
            if not rgx_groups:
                raise Exception("Unable to extract helm chart name")
            rgx_groups = rgx_groups.groupdict()
            print(f"regex groups found: {rgx_groups}")

            # params = {"name": rgx_groups["chart_name"]}
            # if rgx_groups["chart_version"]:
            #     params["version"] = rgx_groups["chart_version"]
            resp = harbor.api_search_file(rgx_groups["chart_name"])

            assert len(resp.json()) >= 1
            print(f"{rgx_groups["chart_name"]} detected in {HARBOR_PROJECT}")
    finally:
        cleanup_output_directory(OUTPUT_DIR)
        harbor.api_delete_project()


def _bitnami_helm_download(input_str):
    # Download
    proc = subprocess.run(
        [
            "python",
            "-m",
            "airgapper",
            "bitnami_helm",
            "download",
            input_str,
            "-o",
            OUTPUT_DIR,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    pretty_print_completedprocess(proc)
    return proc


def _bitnami_helm_upload_nexus(input_str):
    proc = subprocess.run(
        [
            "python",
            "-m",
            "airgapper",
            "bitnami_helm",
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
        check=False,
    )
    pretty_print_completedprocess(proc)
    return proc


def _bitnami_helm_upload_harbor(input_str):
    proc = subprocess.run(
        [
            "python",
            "-m",
            "airgapper",
            "bitnami_helm",
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
        check=False,
    )
    pretty_print_completedprocess(proc)
    return proc


def _check_if_download_success(helm_chart_package):
    # Check if file downloaded successfully
    rgx_groups = re.search(RGX_PACKAGE_NAME, helm_chart_package)
    if not rgx_groups:
        raise Exception("Unable to extract helm chart name")
    rgx_groups = rgx_groups.groupdict()
    if not rgx_groups["chart_version"]:
        rgx_groups["chart_version"] = ""  # Set empty string as default value
    # print(rgx_groups)
    helm_chart_file_prefix = (
        f"{Path(OUTPUT_DIR).as_posix()}/{rgx_groups['chart_name']}*{rgx_groups['chart_version']}*.wrap.tgz"
    )
    print(f"Checking if file with prefix {helm_chart_file_prefix} exists.")
    paths = list(glob(helm_chart_file_prefix))
    print(f"Paths detected with prefix: {paths}")
    assert len(paths) > 0
