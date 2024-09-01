from email.mime import image
import json
import os
import re
from pathlib import Path

from airgapper.enum import InputType
from airgapper.dataclasses import Args
from airgapper.utils import check_docker, run_command, run_command_with_stdout
from airgapper.repositories import HarborHelper, NexusHelper

def download_docker_images(args: Args):
    input_list = []
    if args.input_type == InputType.PACKAGE:
        input_list.append(args.input)
    elif args.input_type == InputType.TXT_FILE:
        with open(Path(args.input), "r") as f:
            input_list = [line.strip() for line in f.readlines()]

    # Check if output dir exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download images
    check_docker()
    print(f"Downloading docker list {input_list}")
    for image_name in input_list:
        dl_image = run_command(["docker", "pull", image_name], text=True)
        if dl_image.returncode:
            print(dl_image.stderr)
            raise Exception("Exception occured during downloading images.")

    # Tar images
    for image_name in input_list:
        tar_fp = output_dir / _get_sanitized_tar_filename(image_name)
        print(f"saving to {tar_fp}")
        tar_image = run_command(["docker","save","--output", tar_fp, image_name])
        if tar_image.returncode:
            print("Exception occured during saving images to tar.")


def upload_docker_images_harbor(args: Args):
    registry = args.registry
    repository = args.repository
    # Validate repository
    if not repository:
        raise Exception("Missing input repository. Harbor upload requires repository.")
    
    try:
        harbor = HarborHelper(url=args.registry, project=args.repository)
        harbor.login()
        
        # List tar files in directory
        upload_list = []
        if args.input_type == InputType.PACKAGE:
            upload_list.append(args.input)
        elif args.input_type == InputType.FOLDER:
            upload_list = list(Path(args.input).glob("**/*.tar"))
        else:
            raise Exception(f"Unrecognized input_type: {args.input_type.value}")
        if not upload_list:
            raise Exception(f"No files found at {Path(args.input)}")
        
        for file in upload_list:
            print(f"Uploading {file}..")
            load_cmd_stdout = _load_docker_tar(file)
            loaded_image_name = _get_loaded_image_name_from_text(load_cmd_stdout)

            # Retag image
            image_new_name = f"{registry}/{repository}/{loaded_image_name}"
            print(f"Retagging image {loaded_image_name} to {image_new_name}.")
            run_command(["docker", "tag", f"{loaded_image_name}", image_new_name])

            _push_docker_registry(image_new_name)

    finally:
        print("Logging out docker..")
        harbor.logout()

def upload_docker_images_nexus(args: Args):
    registry = args.registry

    try:
        nexus = NexusHelper(url=args.registry, repository=args.repository)
        nexus.login_docker()

        # List tar files in directory
        upload_list = []
        if args.input_type == InputType.PACKAGE:
            upload_list.append(args.input)
        elif args.input_type == InputType.FOLDER:
            upload_list = list(Path(args.input).glob("**/*.tar"))
        else:
            raise Exception(f"Unrecognized input_type: {args.input_type.value}")
        if not upload_list:
            raise Exception(f"No files found at {Path(args.input)}")
                    
        for file in upload_list:
            print(f"Uploading {file}..")

            load_cmd_stdout = _load_docker_tar(file)

            loaded_image_name = _get_loaded_image_name_from_text(load_cmd_stdout)

            # Retag image
            image_new_name = f"{registry}/{loaded_image_name}"
            print(f"Retagging image {loaded_image_name} to {image_new_name}.")
            run_command(["docker", "tag", f"{loaded_image_name}", image_new_name])

            _push_docker_registry(image_new_name)

    finally:
        print("Logging out docker..")
        nexus.logout_docker()


def upload_docker_images_generic_registry():
    pass


def _load_docker_tar(file):
    load_cmd, load_cmd_stdout = run_command_with_stdout(["docker", "load", "-i", file], text=True)
    if load_cmd.returncode:
        print("Exception occured during loading image.")
        print(json.dumps(load_cmd_stdout, indent=2))
        raise Exception("Exception occured during loading image.")
    print(f"load_cmd: {load_cmd_stdout}")
    return load_cmd_stdout

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
    run_command(["docker", "push", image_new_name])

def _get_sanitized_tar_filename(image_name):
    tar_name = image_name.split('/')[-1]
    tar_name = re.sub(r'[^\w_.)( -]', '', tar_name)
    return f"{tar_name}.tar"

