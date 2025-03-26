"""pytest -rP
-k "test_XXX" to test a targeted test function
-x stop on first failure
"""

import os
import sys
import subprocess
from pathlib import Path
from time import sleep

import pytest
from dotenv import load_dotenv


from airgapper.utils import (
    pretty_print_completedprocess,
    pretty_print_response,
)
from airgapper.__main__ import main
from airgapper.repositories import NexusHelper
from airgapper.enum import MavenRepository
from testing_utils import cleanup_output_directory

load_dotenv()
OUTPUT_DIR = "./output/test/maven"


# Nexus Config
NEXUS_URL = os.environ["AIRGAPPER_NEXUS_URL"]
NEXUS_USER = os.environ["AIRGAPPER_NEXUS_USER"]
NEXUS_PASS = os.environ["AIRGAPPER_NEXUS_PASS"]
NEXUS_REPOSITORY = "maven-hosted"


def create_nexus_maven_repository(nexus):
    # Check if nexus have created helm repo
    resp = nexus.api_get_maven_repository(NEXUS_REPOSITORY)
    pretty_print_response(resp)
    if resp.status_code == 200:
        print(f"{NEXUS_REPOSITORY} found.")
    elif resp.status_code != 200:
        print(f"{NEXUS_REPOSITORY} not found. Creating it in nexus..")
        resp = nexus.api_create_maven_repository(NEXUS_REPOSITORY)
        pretty_print_response(resp)
        assert resp.status_code == 201
    else:
        sys.exit(1)


@pytest.fixture(scope="session", name="nexus")
def nexus_fixture():
    nexus = NexusHelper(url=NEXUS_URL, repository=NEXUS_REPOSITORY)
    create_nexus_maven_repository(nexus)
    return nexus


@pytest.mark.parametrize("input_xml", ["input/test/dl_pom.xml"])
def test_mvn_dl_pom_pass(input_xml):
    try:
        # Download pom.xml
        proc = _maven_download(input_xml)
        assert proc.returncode == 0

        # Check if file downloaded successfully
        _check_if_downloaded_files()

    finally:
        # cleanup artifacts
        cleanup_output_directory(OUTPUT_DIR)


@pytest.mark.parametrize("input_xml", ["input/test/dl_pom.xml"])
def test_mvn_ul_pom_pass(input_xml, nexus, monkeypatch):
    try:
        # Download
        proc = _maven_download(input_xml)
        assert proc.returncode == 0

        # Upload
        monkeypatch.setattr('sys.argv', [
            "airgapper.py", 
            "maven",
            "upload",
            OUTPUT_DIR,
            "-a",
            MavenRepository.NEXUS.value,
            "-r",
            NEXUS_URL,
            "--repo",
            NEXUS_REPOSITORY,
        ])
        main()
        # captured = capsys.readouterr()
        # print(captured)

        # Check Upload
        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print("Checking if file is uploaded.")
        params = {"q": "gson", "repository": "maven-hosted"}
        resp = nexus.api_search_file(**params)
        assert len(resp.json().get("items")) > 0
        print(f"gson detected in {NEXUS_REPOSITORY}")

    finally:
        # Cleanup
        cleanup_output_directory(OUTPUT_DIR)
        nexus.api_delete_repo()


@pytest.mark.parametrize("input_xml", ["input/test/dl_pom.xml"])
def test_mvn_tool_missing_throw_exception(input_xml):
    """Test exception thrown when mvn tool not installed"""
    custom_env = os.environ.copy()
    del custom_env["AIRGAPPER_MAVEN_DIRECTORY"]
    proc = subprocess.run(
        ["python", "-m", "airgapper", "maven", "download", input_xml, "-o", OUTPUT_DIR],
        env=custom_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    print(proc.stderr)
    assert "FileNotFoundError" in proc.stderr


@pytest.mark.parametrize("input_xml", ["input/test/dl_pom.xml"])
def test_mvn_directory_wrong_throw_exception(input_xml):
    """Test exception thrown when AIRGAPPER_MAVEN_DIRECTORY misconfigured"""
    custom_env = os.environ.copy()
    custom_env["AIRGAPPER_MAVEN_DIRECTORY"] = "./fake-apache-maven-3.9"
    proc = subprocess.run(
        ["python", "-m", "airgapper", "maven", "download", input_xml, "-o", OUTPUT_DIR],
        env=custom_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "FileNotFoundError" in proc.stderr


#############################################
# Helper
#############################################


def _maven_download(input_xml):
    proc = subprocess.run(
        ["python", "-m", "airgapper", "maven", "download", input_xml, "-o", OUTPUT_DIR],
        capture_output=True,
        text=True,
        check=False,
    )
    pretty_print_completedprocess(proc)
    return proc


def _check_if_downloaded_files():
    assert len(list(Path(OUTPUT_DIR).iterdir())) > 0
