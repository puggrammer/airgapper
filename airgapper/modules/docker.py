import logging
import re
import subprocess
from pathlib import Path

from airgapper.enum import InputType
from airgapper.modules.dataclasses import Args

def download_docker_images(args: Args):
    DEFAULT_OUTPUT_DIR = "./output/docker"
    print(f"Args: {args}")

    input_list = []
    if args.input_type == InputType.FILE:
        input_list.append(args.input)
    elif args.input_type == InputType.TXT_FILE:
        with open(Path(args.input), "r") as f:
            input_list = [line.strip() for line in f.readlines()]

    # Check if output dir exist
    output_dir = Path(args.output_dir if args.output_dir else DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download images
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


def upload_docker_images(args):
    DOCKER_REGISTRY = args.registry
    PROJECT_NAME = args.project
    UPLOAD_DIR = Path(args.upload_dir)

    try:
        print("Logging in docker..")
        login_cmd = subprocess.run(["docker", "login", DOCKER_REGISTRY])
        if login_cmd.returncode:
            print("Exception occured during logging in.")
            print(f"{login_cmd=}")
            exit(1)

        # List tar files in directory
        files = list(UPLOAD_DIR.glob("**/*.tar"))
        for file in files:
            print(f"Uploading {file}..")
            load_cmd = subprocess.run(["docker", "load", "-i", file], capture_output=True, text=True)
            if load_cmd.returncode:
                print("Exception occured during loading image.")
                print(f"{login_cmd=}")

            image_name_rgx = re.search(r"Loaded image: ([\w\d:.\-/]+)\n", load_cmd.stdout)
            if not image_name_rgx:
                print(f"{image_name_rgx=}")
                raise Exception("Unable to locate loaded image name using regex.")
            loaded_image_name = image_name_rgx.group(1)

            # Retag image
            image_new_name = f"{DOCKER_REGISTRY}/{PROJECT_NAME}/{loaded_image_name}"
            print(f"Retagging image {loaded_image_name} to {image_new_name}.")
            subprocess.run(["docker", "tag", f"{loaded_image_name}", image_new_name])

            # Push image to registry
            print(f"Pushing repository {image_new_name} to registry {DOCKER_REGISTRY}.")
            subprocess.run(["docker", "push", image_new_name])
    finally:
        print("Logging out docker..")
        subprocess.run(["docker", "logout", DOCKER_REGISTRY])   

def _get_sanitized_tar_filename(image_name):
    tar_name = image_name.split('/')[-1]
    tar_name = re.sub(r'[^\w_.)( -]', '', tar_name)
    return f"{tar_name}.tar"
