import os
import subprocess
from pathlib import Path

from airgapper.dataclasses import Args
from airgapper.enum import InputType
from airgapper.repositories import NexusHelper
from airgapper.utils import run_command, pretty_print_summary


class MavenHelper:

    def __init__(self) -> None:
        self.MAVEN_DIR = os.environ.get("AIRGAPPER_MAVEN_DIRECTORY")
        DEFAULT_OUTPUT_DIR = Path("./output/maven")
        
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
                    self.mvn_fp,
                    "dependency:copy-dependencies",
                    "-Dmdep.addParentPoms=true",
                    "-Dmdep.copyPom=true",
                    f"-Dmaven.repo.local={args.output_dir}/m2-cache/",
                    f"-DoutputDirectory={args.output_dir}",
                    "-f",
                    args.input,
                ])
            pretty_print_summary(f"Completed maven download with status code {proc.returncode}")
        else:
            raise Exception("No implementation for provided InputType.")

    def upload_maven_packages(self, args: Args):
        nexus = NexusHelper(url=args.registry, repository=args.repository)
        output_dir = Path(args.input)
        for pomFile in output_dir.rglob("*.pom"):
            jarFile = Path(str(pomFile).replace(".pom", ".jar"))
            packageName = pomFile.with_suffix("").name
            if jarFile.exists():
                print(f"Uploading pom + jar for {packageName}")
                nexus.api_upload_maven_component(pom_fp=pomFile, jar_fp=jarFile)
            else:
                print(f"Uploading pom for {packageName}")
                nexus.api_upload_maven_component(pom_fp=pomFile)
        pretty_print_summary("Upload maven packages to nexus completed!")
        

    def __check_mvn_installed(self):
        if self.MAVEN_DIR:
            mvn_fp = Path(f"{self.MAVEN_DIR}/bin/mvn")
            if mvn_fp.exists() and mvn_fp.is_file():
                self.mvn_fp = mvn_fp
                print("Found!")
                return
            else:
                raise FileNotFoundError(f"mvn not found in provided maven directory {self.MAVEN_DIR}/bin")
        
        try:
            resp = subprocess.run(["mvn","-v"], capture_output=True, text=True, check=False)
            if resp.returncode == 0:
                self.mvn_fp = "mvn"

        except FileNotFoundError:
            raise FileNotFoundError(
                "✖ mvn binary tool not found/installed."
                "Please download at https://maven.apache.org/download.cgi."
                "Then add Maven executable to PATH."
        
        )
