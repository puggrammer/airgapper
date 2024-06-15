from email.mime import image
import json
import re
import subprocess
from pathlib import Path

from airgapper.enum import InputType
from airgapper.modules.dataclasses import Args

def download_docker_images(args: Args):
    print(f"Args: {args}")

    input_list = []
    if args.input_type == InputType.FILE:
        input_list.append(args.input)
    elif args.input_type == InputType.TXT_FILE:
        with open(Path(args.input), "r") as f:
            input_list = [line.strip() for line in f.readlines()]

    # Check if output dir exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download images
    _check_docker()
    print(f"Downloading docker list {input_list}")
    for image_name in input_list:
        dl_image = subprocess.run(["docker", "pull", image_name],capture_output=True, text=True)
        if dl_image.returncode:
            print(dl_image.stderr)
            raise Exception("Exception occured during downloading images.")

    # Tar images
    for image_name in input_list:
        tar_fp = output_dir / _get_sanitized_tar_filename(image_name)
        print(f"saving to {tar_fp}")
        tar_image = subprocess.run(["docker","save","--output", tar_fp, image_name])
        if tar_image.returncode:
            print("Exception occured during saving images to tar.")


def upload_docker_images_harbor(args: Args):
    registry = args.registry
    repository = args.repository
    upload_dir = Path(args.input)

    try:
        _login_docker_registry(registry)

        # List tar files in directory
        files = list(upload_dir.glob("**/*.tar"))
        for file in files:
            print(f"Uploading {file}..")

            load_cmd = _load_docker_tar(file)

            loaded_image_name = _get_loaded_image_name_from_text(load_cmd.stdout)

            # Retag image
            image_new_name = f"{registry}/{repository}/{loaded_image_name}"
            print(f"Retagging image {loaded_image_name} to {image_new_name}.")
            subprocess.run(["docker", "tag", f"{loaded_image_name}", image_new_name])

            _push_docker_registry(image_new_name)

    finally:
        print("Logging out docker..")
        subprocess.run(["docker", "logout", registry])   

def upload_docker_images_nexus(args: Args):
    registry = args.registry
    upload_dir = Path(args.input)

    try:
        _login_docker_registry(registry)

        # List tar files in directory
        files = list(upload_dir.glob("**/*.tar"))
        for file in files:
            print(f"Uploading {file}..")

            load_cmd = _load_docker_tar(file)

            loaded_image_name = _get_loaded_image_name_from_text(load_cmd.stdout)

            # Retag image
            image_new_name = f"{registry}/{loaded_image_name}"
            print(f"Retagging image {loaded_image_name} to {image_new_name}.")
            subprocess.run(["docker", "tag", f"{loaded_image_name}", image_new_name])

            _push_docker_registry(image_new_name)

    finally:
        print("Logging out docker..")
        subprocess.run(["docker", "logout", registry])   


def upload_docker_images_generic_registry():
    pass


def _login_docker_registry(registry):
    print("Logging in docker..")
    _check_docker()
    login_cmd = subprocess.run(["docker", "login", registry], capture_output=True,
        text=True)
    if login_cmd.returncode:
        print("Exception occured during logging in.")
        print(f"{login_cmd=}")
        raise Exception("Exception occured during logging in.")

def _load_docker_tar(file):
    load_cmd = subprocess.run(["docker", "load", "-i", file], capture_output=True, text=True)
    if load_cmd.returncode:
        print("Exception occured during loading image.")
        print(json.dumps(load_cmd, indent=2))
        raise Exception("Exception occured during loading image.")
    return load_cmd

def _get_loaded_image_name_from_text(text):
    image_name_rgx = re.search(r"Loaded image: ([\w\d:.\-/]+)\n", text)
    if not image_name_rgx:
        print(f"{image_name_rgx=}")
        raise Exception("Unable to locate loaded image name using regex.")
    loaded_image_name = image_name_rgx.group(1)
    return loaded_image_name


def _push_docker_registry(image_new_name):
    # Push image to registry
    print(f"Pushing repository {image_new_name} to registry.")
    subprocess.run(["docker", "push", image_new_name])

def _get_sanitized_tar_filename(image_name):
    tar_name = image_name.split('/')[-1]
    tar_name = re.sub(r'[^\w_.)( -]', '', tar_name)
    return f"{tar_name}.tar"

def _check_docker():
    resp = subprocess.run(["docker", "--version"], capture_output=True, text=True)
    if resp.returncode:
        print(resp.stdout)
        print(resp.stderr)
        raise Exception("✖ Need to install/start docker first and run this script again.")
    