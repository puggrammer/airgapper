"""
Super Script to handle all kind of downloads for airgapped applications.
Supports:
    - Helm Chart
        - Currently using VMWare "dt" plugin for wrapping all sub-dependencies; sub-charts + container images 
        - https://github.com/vmware-labs/distribution-tooling-for-helm
        - Example: oci://docker.io/bitnamicharts/kibana
    - Docker
    - Pypi (Pending)
    - Npm (Pending)
    - Maven Central (Pending)

"""

import argparse
from genericpath import isdir
import logging
import sys
from pathlib import Path

from airgapper.modules import *
from airgapper.enum import Module, Action, InputType
from airgapper.modules.dataclasses import Args

# Configs


#===== Parser =====#
parser = argparse.ArgumentParser(
    prog="Airgapped Downloader",
    description="Helper to download packages/images for airgapped apps.",
    epilog="Developed to help us poor devs without internet access.",
)
parser.add_argument(
    "module", choices=[x.value for x in Module], help="Select Module Downloader"
)
parser.add_argument(
    "action", choices=[x.value for x in Action], help="Select to download or upload"
)

parser.add_argument(
    "input",
    help=(
        "[DOWNLOAD] Either single package or a .txt file \n"
        "[UPLOAD] folder directory containing packages. See examples in Repository"
    )
)

# Download
# parser.add_argument(
#     "-f",
#     "--file",
#     dest="input_filepath",
#     required=Action.DOWNLOAD in sys.argv,
#     help="[DOWNLOAD] txt file of list of repository/image:tag or package. E.g. tensorflow/tensorflow",
# )
parser.add_argument(
    "-o",
    "--outputDir",
    dest="output_dir",
    required=Action.DOWNLOAD in sys.argv,
    help="[DOWNLOAD] Output directory for downloaded packages/images",
)


# Upload
# parser.add_argument(
#     '-u',
#     "--uploadDir",
#     dest="upload_dir",
#     required=Action.UPLOAD in sys.argv,
#     help="[UPLOAD] Input directory of packages/images to be uploaded.",
# )
parser.add_argument(
    "--repository",
    dest="repository",
    # required=Action.UPLOAD in sys.argv,
    help="[UPLOAD] Project/Repository where packaged/images to be uploaded to.",
)
parser.add_argument(
    '-r',
    "--registry",
    dest="registry",
    required=Action.UPLOAD in sys.argv,
    help="[UPLOAD] Registry hostname.",
)


def print_intro():
    print("============================================================")
    print(r"""    ___    ________  _________    ____  ____  __________ """)
    print(r"""   /   |  /  _/ __ \/ ____/   |  / __ \/ __ \/ ____/ __ \ """)
    print(r"""  / /| |  / // /_/ / / __/ /| | / /_/ / /_/ / __/ / /_/ /""")
    print(r""" / ___ |_/ // _, _/ /_/ / ___ |/ ____/ ____/ /___/ _, _/ """)
    print(r"""/_/  |_/___/_/ |_|\____/_/  |_/_/   /_/   /_____/_/ |_|  """)
    print("\nTaking the shet pain out of air-gapped environments.")
    print("============================================================\n")

    

# def validate_upload_params(args):
#     # if not args.project:
#     #     raise Exception(f"Missing --project flag for {Action.UPLOAD}!")
    
#     # Check if upload directory exist
#     upload_dir = Path(args.upload_dir)
#     if not upload_dir.exists():
#         raise Exception(f"Filepath {upload_dir} does not exist.")
#     if not upload_dir.is_dir():
#         raise Exception(f"Filepath {upload_dir} is not a directory.")



def main():
    print_intro()

    args = Args(parser.parse_args())
    logging.info(f"Initializing f{args.module}: f{args.action}.")

    # Route Request
    if args.module == Module.HELM:
        if args.action == Action.DOWNLOAD:
            download_helm_chart(args)
        elif args.action == Action.UPLOAD:
            upload_helm_chart(args)
    elif args.module == Module.DOCKER:
        if args.action == Action.DOWNLOAD:
            download_docker_images(args)
        elif args.action == Action.UPLOAD:
            upload_docker_images(args)
    else:
        print("else")
        raise NotImplementedError("Not done yet!")


if __name__ == "__main__":
    main()
