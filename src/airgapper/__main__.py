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
import sys

from airgapper.modules import download_docker_images, upload_docker_images_harbor
from airgapper.enum import DockerRepository, Module, Action
from airgapper.dataclasses import Args
from airgapper.modules.docker import upload_docker_images_nexus
from airgapper.modules import PypiHelper, BitnamiHelmHelper

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
        "[DOWNLOAD] Either single package name or a .txt file \n"
        "[UPLOAD] Either single file or folder directory containing packages. See examples in Repository"
    )
)

parser.add_argument(
    "-a",
    "--app",
    dest="application",
    default=None,
    help="[UPLOAD] Specific application name to upload to"
)

parser.add_argument(
    "-o",
    "--outputDir",
    dest="output_dir",
    required=Action.DOWNLOAD in sys.argv,
    help="[DOWNLOAD] Output directory for downloaded packages/images",
)

parser.add_argument(
    "--repo",
    "--repository",
    dest="repository",
    default=None,
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


def main():
    print_intro()

    args = Args(parser.parse_args())
    print(f"Initializing {args.module}: {args.action}.")
    print(f"Args: {args}")

    # Route Request
    if args.module == Module.BITNAMI_HELM:
        module = BitnamiHelmHelper()
        if args.action == Action.DOWNLOAD:
            module.download_helm_charts(args)
        elif args.action == Action.UPLOAD:
            if args.application == DockerRepository.HARBOR:
                module.upload_helm_chart_harbor(args)
            elif args.application == DockerRepository.NEXUS:
                module.upload_helm_chart_nexus(args)
            else:
                raise NotImplementedError

    elif args.module == Module.DOCKER:
        if args.action == Action.DOWNLOAD:
            download_docker_images(args)
        elif args.action == Action.UPLOAD:
            if args.application == DockerRepository.HARBOR:
                upload_docker_images_harbor(args)
            elif args.application == DockerRepository.NEXUS:
                upload_docker_images_nexus(args)
            else:
                raise NotImplementedError

    elif args.module == Module.PYPI:
        module = PypiHelper()
        if args.action == Action.DOWNLOAD:
            module.download_pypi_packages(args)
        elif args.action == Action.UPLOAD:
            if args.application == DockerRepository.NEXUS:
                module.upload_pypi_packages_nexus(args)

    else:
        print("else")
        raise NotImplementedError("Not done yet!")


if __name__ == "__main__":
    main()
