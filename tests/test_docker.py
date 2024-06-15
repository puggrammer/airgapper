""" pytest -rP 
-k "test_XXX" to test a targeted test function
-x stop on first failure
"""

import json
from time import sleep
import requests
import subprocess
from pathlib import Path
import pytest

from airgapper.enum import DockerRegistry
from airgapper.modules.docker import _get_sanitized_tar_filename

output_dir = "./output/test/docker"
download_txt_file = "input/test/dl_docker.txt"

single_image_name = "alpinelinux/unbound:latest-x86_64"
single_image_output_tar = _get_sanitized_tar_filename(single_image_name)

output_tar_fp = None

harbor_url = "127.0.1.1:8090"
harbor_user = "admin"
harbor_pass = "Harbor12345"

nexus_url = "127.0.1.1:8091"
nexus_user = "admin"
nexus_pass = "nexus"
nexus_docker_url = "127.0.1.1:8092"


@pytest.fixture(scope="module", autouse=True)
def startup_containers():
    print("Starting up harbor..")
    proc = subprocess.run(
        ["docker", "compose", "-f","bin/harbor/docker-compose.yml","up","-d"],
        capture_output=True,
        text=True
    )
    pretty_print_completedprocess(proc)
    sleep(5)

    print("Starting up nexus..")
    proc = subprocess.run(
        ["docker", "compose", "-f","bin/nexus/docker-compose.yml","up","-d"],
        capture_output=True,
        text=True
    )
    pretty_print_completedprocess(proc)
    sleep(5)


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
    except Exception as ex:
        print(proc.stderr)
        raise ex
    finally:
        cleanup_docker_download(single_image_name)
        cleanup_output_tar(output_tar_fp)


def test_docker_dl_directory_pass():

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
        assert proc.stderr == ''

        sanitized_tar_filenames = set([Path(f"{output_dir}/{_get_sanitized_tar_filename(image)}") for image in images])

        output_tars = list(Path(output_dir).iterdir())
        print(f"Files detected in output directory {output_dir}: {output_tars}")

        assert len(output_tars) == images_count
        assert sanitized_tar_filenames == set(output_tars)

    finally:
        for image in images:
            cleanup_docker_download(image)
        for tar in output_tars:
            cleanup_output_tar(tar)


def test_docker_ul_package_nexus_pass():
    single_image_id = None

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
        print("pre-logging in for non-interactive tty")
        login_cmd = subprocess.run([
            "docker", "login", nexus_docker_url,"-u",nexus_user,"-p",nexus_pass], capture_output=True,
            text=True)
        pretty_print_completedprocess(login_cmd)

        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","upload",output_dir, "-a", DockerRegistry.NEXUS.value, "-r",nexus_docker_url],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0
        assert proc.stderr == ''

        print("Sleeping for 5s for nexus update..")
        sleep(5)
        print(f"Checking if file is uploaded.")
        repo_name = single_image_name.split(":")[0]
        resp = requests.get(
            f"http://{nexus_url}/service/rest/v1/search",
            params={
                "repository": "docker-hosted",
                "docker.imageName": repo_name
            },
            auth=(nexus_user, nexus_pass)
        )
        pretty_print_response(resp)
        assert resp.status_code == 200
        assert len(resp.json().get("items")) == 1

        single_image_id = resp.json().get("items")[0].get("id")

    finally:
            cleanup_docker_download(single_image_name)
            cleanup_output_tar(output_tar_fp)

            # Delete from registry
            if single_image_id:
                print(f"Deleting {repo_name} from nexus..")
                resp = requests.delete(
                    f"http://{nexus_url}/service/rest/v1/components/{single_image_id}",
                    auth=(nexus_user, nexus_pass)
                )
                pretty_print_response(resp)
                assert resp.status_code == 204
            else:
                print("Unable to delete due to missing single_image_id")


def test_docker_ul_package_harbor_pass():
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
        print("pre-login for non-interactive tty")
        login_cmd = subprocess.run(["docker", "login", harbor_url,"-u",harbor_user,"-p",harbor_pass], capture_output=True,
            text=True)
        pretty_print_completedprocess(login_cmd)

        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","upload",output_dir, "-a", DockerRegistry.HARBOR, "-r", harbor_url, "--repo","library"],
            capture_output=True,
            text=True
        )
        pretty_print_completedprocess(proc)
        assert proc.returncode == 0
        assert proc.stderr == ''

        print(f"Checking if file is uploaded.")
        repo_name = single_image_name.split(":")[0]
        resp = requests.get(
            f"http://{harbor_url}/api/v2.0/projects/library/repositories/{repo_name.replace('/','%252F')}",
            auth=(harbor_user, harbor_pass)
        )
        pretty_print_response(resp)
        assert resp.status_code == 200
        assert resp.json().get("artifact_count") == 1

    finally:
            cleanup_docker_download(single_image_name)
            cleanup_output_tar(output_tar_fp)

            # Delete from registry
            print(f"Deleting {repo_name} from harbor..")
            resp = requests.delete(
                f"http://{harbor_url}/api/v2.0/projects/library/repositories/{repo_name.replace('/','%252F')}",
                auth=(harbor_user, harbor_pass)
            )
            pretty_print_response(resp)


def test_docker_ul_package_docker_registry_pass():
    pass

def test_docker_ul_directory_docker_registry_pass():
    pass


def pretty_print_completedprocess(resp: subprocess.CompletedProcess):
    if resp.returncode == 0:
        print(resp.stdout)
    elif resp.returncode:
        print(resp.stderr)

def pretty_print_response(resp: requests.Response):
    print(f"{resp.status_code}: {resp.reason}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except:
        print(resp.text)

def cleanup_docker_download(image_name):
    print(f"Cleaning up downloaded image {image_name}..")
    subprocess.run(["docker","rmi",image_name])


def cleanup_output_tar(output_tar_fp: Path):
    if output_tar_fp:
        print("Cleaning up docker downloaded ouput tar..")
        output_tar_fp.unlink(missing_ok=True)