""" pytest -rP 
-k "test_XXX" to test a targeted test function
-x stop on first failure
"""

import os
import sys

import pytest
from dotenv import load_dotenv


from airgapper.utils import (
    pretty_print_completedprocess,
    pretty_print_response,
)
from airgapper.repositories import NexusHelper

load_dotenv()
OUTPUT_DIR = "./output/test/maven"


# Nexus Config
NEXUS_URL = os.environ["AIRGAPPER_NEXUS_URL"]
NEXUS_USER = os.environ["AIRGAPPER_NEXUS_USER"]
NEXUS_PASS = os.environ["AIRGAPPER_NEXUS_PASS"]
NEXUS_REPOSITORY = "maven-hosted"


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


@pytest.mark.parametrize("package", ["colorama", "iniconfig==2.0.0"])
def test_mvn_dl_package_pass():
    pass


@pytest.mark.parametrize("input_xml", ["input/test/dl_pom.xml"])
def test_mvn_dl_pom_pass(input_xml):
    pass


@pytest.mark.parametrize("package", ["colorama", "iniconfig==2.0.0"])
def test_pypi_ul_package_nexus_pass(package, nexus):
    pass


@pytest.mark.parametrize("input_xml", ["input/test/dl_pom.xml"])
def test_mvn_ul_pom_pass(input_xml, nexus):
    pass

def test_mvn_tool_missing_exception_pass():
    """ Test exception thrown when mvn tool not installed """
    pass