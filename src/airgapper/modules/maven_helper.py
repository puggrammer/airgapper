import os
from pathlib import Path
from airgapper.dataclasses import Args
from airgapper.enum import InputType
from airgapper.utils import run_command


class MavenHelper:
    MVN_DIR = os.environ.get("AIRGAPPER_MVN_DIRECTORY")
    DEFAULT_OUTPUT_DIR = Path("./output/maven")

    def __init__(self) -> None:
        # Check Dependencies
        self.__check_mvn_installed()

    def download_maven_packages(self, args: Args):
        print("Downloading maven packages..")


        # Check if output dir exist
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Download maven packages
        if args.input_type == InputType.FILE:
            # Validate input as .xml format
            if '.xml' not in args.input:
                raise Exception("Input is not a .xml file")
            proc = run_command(
                [
                    "mvn",
                    "dependency:copy-dependencies",
                    "-Dmdep.addParentPoms=true",
                    "-Dmdep.copyPom=true",
                    f"-Dmaven.repo.local={args.output_dir}/m2-cache/",
                    f"-DoutputDirectory={args.output_dir}",
                    "-f",
                    args.input,
                ]
            )
        else:
            raise Exception("No implmentation for provided InputType.")

    def upload_maven_packages(self, args: Args):
        pass

    def __check_mvn_installed(self):
