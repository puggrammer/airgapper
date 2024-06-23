""" pytest -rP 
-k "test_XXX" to test a targeted test function
-x stop on first failure
"""

import os
import subprocess
import glob
from pathlib import Path
from time import sleep

import pytest
import requests

from airgapper.enum import DockerRegistry
from airgapper.utils import check_docker, pretty_print_completedprocess, pretty_print_response

output_dir = "./output/test/pypi"
download_txt_file = "input/test/dl_pypi_requirements.txt"

single_package_name = "iniconfig==2.0.0"
single_package_output_whl = Path(f"iniconfig-2.0.0-py3-none-any.whl")

output_whl_fp = None

nexus_url = "127.0.1.1:8091"
nexus_user = "admin"
nexus_pass = "nexus"
nexus_repo = "pypi-hosted"

os.environ["AIRGAPPER_PYPI_USER"] = nexus_user
os.environ["AIRGAPPER_PYPI_PASS"] = nexus_pass

@pytest.fixture(scope="module", autouse=True)
def startup_containers():
    print("Starting up nexus..")
    check_docker()
    proc = subprocess.run(
        ["docker", "compose", "-f","bin/nexus/docker-compose.yml","up","-d"],
        capture_output=True,
        text=True
    )
    pretty_print_completedprocess(proc)
    sleep(5)


def test_pypi_dl_package_pass():
    try:
        proc = subprocess.run(
            ["python", "-m", "airgapper","pypi","download",single_package_name,"-o",output_dir],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        output_whl_fp = Path(output_dir)/single_package_output_whl
        print(f"Checking if {output_whl_fp} exists.")
        assert output_whl_fp.exists()
    finally:
        cleanup_whl_directory()


def test_pypi_dl_file_pass():
    try:
        proc = subprocess.run(
            ["python", "-m", "airgapper","pypi","download",download_txt_file,"-o",output_dir],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        output_files = set([x.name for x in list(Path(output_dir).iterdir())])
        print(f"Files detected in output directory {output_dir}: {output_files}")

        with open(download_txt_file, 'r') as f:
            pkgs = [pkg.strip() for pkg in f.readlines()]
        
        output_pkgs = set([x.split('-')[0] for x in output_files])
        for pkg in pkgs:
            pkg_name = pkg.split("==")[0]
            print(pkg_name)
            assert pkg_name in output_pkgs

    finally:
        cleanup_whl_directory()


def test_pypi_ul_package_nexus_pass():
    try:
        # Download
        proc = subprocess.run(
            ["python", "-m", "airgapper","pypi","download",single_package_name,"-o",output_dir],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        output_whl_fp = Path(output_dir)/single_package_output_whl
        print(f"Checking if {output_whl_fp} exists.")
        assert output_whl_fp.exists()

        # Upload
        proc = subprocess.run(
            ["python", "-m", "airgapper","pypi","upload",output_whl_fp,"-a",DockerRegistry.NEXUS.value,"-r",nexus_url,"--repo",nexus_repo],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print(f"Checking if file is uploaded.")
        resp = nexus_get_file(single_package_name.split("==")[0])
        assert len(resp.json().get("items")) == 1

    finally:
        cleanup_whl_directory()
        cleanup_nexus_delete_repo()


def test_pypi_ul_directory_nexus_pass():
    try:
        # Download
        proc = subprocess.run(
            ["python", "-m", "airgapper","pypi","download",download_txt_file,"-o",output_dir],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0
        
        # Upload
        output_files = list(Path(output_dir).iterdir())
        print(f"Files detected in output directory {output_dir}: {output_files}")

        proc = subprocess.run(
            ["python", "-m", "airgapper","pypi","upload",output_dir,"-a", DockerRegistry.NEXUS.value, "-r", nexus_url, "--repo", nexus_repo],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print(f"Checking if files are uploaded.")
        for file in output_files:
            pkg_name = file.name.split('-')[0]
            resp = nexus_get_file(pkg_name)
            assert len(resp.json().get("items")) == 1
            print(f"{pkg_name} detected in {nexus_repo}")

    finally:
        cleanup_whl_directory()
        cleanup_nexus_delete_repo()


#############################################
# Helper
#############################################

def nexus_get_file(pkg_name):
    for _ in range(3):
        resp = requests.get(
            f"http://{nexus_url}/service/rest/v1/search",
            params={
                "repository": nexus_repo,
                "pypi.description": pkg_name
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


#############################################
# Cleanup
#############################################

def cleanup_whl_directory():
    print("Cleaning up downloaded whl files..")
    for file in list(Path(output_dir).iterdir()):
        file.unlink(missing_ok=True)


def cleanup_nexus_delete_repo():
    # Delete from registry
    print(f"Listing all components in {nexus_repo} in nexus..")
    items_resp = requests.get(
        f"http://{nexus_url}/service/rest/v1/components",
        params={"repository": nexus_repo},
        auth=(nexus_user, nexus_pass)
    )
    print(f"Deleting all files in repository from nexus..")
    for item in items_resp.json().get("items"):
        print(f"Deleting {item.get('name')}:{item.get('version')} from {nexus_repo}..")
        resp = requests.delete(
            f"http://{nexus_url}/service/rest/v1/components/{item.get('id')}",
            auth=(nexus_user, nexus_pass)
        )

