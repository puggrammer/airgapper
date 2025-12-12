"""
Use VMWare "dt" plugin to download helm chart and all its dependencies at one shot.
Need make sure that the helm chart is OCI-Compliant.

Observed to require linux dt plugin to work on linux destination helm registry.

Example:
./dt unwrap rabbitmq.wrap.tgz harbor.arpa/library --yes
"""

import logging
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

from airgapper.dataclasses import Args
from airgapper.enum import InputType
from airgapper.repositories import NexusHelper, HarborHelper
from airgapper.utils import run_command, pretty_print_response, pretty_print_summary


class BitnamiHelmHelper:
    DT_DIR = os.environ.get("AIRGAPPER_DT_DIRECTORY")
    DEFAULT_OUTPUT_DIR = Path("./output/helm")

    def __init__(self) -> None:

        # Check Dependencies
        # self.check_helm_installed()
        self.check_dt_installed()

    # def check_helm_installed(self):
    #     resp = subprocess.run(["helm", "version"], capture_output=True, text=True)
    #     if resp.returncode:
    #         print(resp.stdout)
    #         print(resp.stderr)
    #         raise Exception("✖ Helm not installed. Please install helm at https://helm.sh/docs/intro/install/")

    def check_dt_installed(self):
        possible_dt_fps = []
        # Check when env var is inserted
        if self.DT_DIR:
            possible_dt_fps.append(Path(self.DT_DIR) / "dt")                    
        # Check if using Pyinstaller one-file 
        if hasattr(sys, '_MEIPASS'):  # Check if running in PyInstaller bundle, Extracted bundle path for PyInstaller
            possible_dt_fps.append(Path(sys._MEIPASS)/"bin/linux_amd64/dt")
        # Check if Normal script location or using Pyinstaller one-folder bundle 
        possible_dt_fps.append(Path(__file__).parents[3]/"bin/linux_amd64/dt")  
        # Check if installed as executable package in os (eg. /usr/local/bin)
        possible_dt_fps.append(Path("/usr/local/bin/dt"))

        for dt_fp in possible_dt_fps:
            try:
                print(f"Checking for dt executable at {dt_fp}")
                if not dt_fp.exists() or not dt_fp.is_file():
                    print("failed1")
                    continue
                resp = subprocess.run(
                    [dt_fp, "version"], capture_output=True, text=True, check=False, shell=True
                )
                if resp.returncode:
                    print(resp.stderr)
                    print(resp.stdout)
                    continue
                self.dt_fp = dt_fp.as_posix()
                print(f"dt executable detected at {dt_fp}")
                self.dt_fp = dt_fp
                return
            except Exception as e:
                pass
            
        raise AssertionError(
            "✖ dt plugin not installed."
            "Please download at github.com/vmware-labs/distribution-tooling-for-helm."
            "Install dt standalone at /usr/local/bin location."
        )
        
    def validate_dt_executable_fp(self, dt_fp):
        print(f"Checking for dt executable at {dt_fp}")
        if dt_fp.exists() and dt_fp.is_file():
            self.dt_fp = dt_fp.as_posix()
            return


    def download_helm_charts(self, args: Args):
        if platform.system() == "Windows":
            logging.error(
                "CAUTION: Use of Windows' dt plugin doesn't upload properly on linux registry server. Please use Bash."
            )
            sys.exit(1)

        input_list = []
        if args.input_type == InputType.PACKAGE:
            input_list.append(self.extract_chart_and_version(args.input))

        elif args.input_type == InputType.FILE:
            input_fp = Path(args.input)
            with open(input_fp, "r", encoding='utf8') as f:
                for line in f.readlines():
                    input_list.append(self.extract_chart_and_version(line))

        # Check if output dir exist
        output_dir = (
            Path(args.output_dir) if args.output_dir else self.DEFAULT_OUTPUT_DIR
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        # TODO
        """
        See if can use helm pull + docker download to get all the files
        then use dt wrap local directory and dt unwrap.
        See inside what does the wrap.tgz contains
        """
        # Download helm chart
        print(f"input_list of helm charts to download: {input_list}")
        for chart in input_list:
            command = [self.dt_fp, "wrap", chart["chart"]]
            if chart["chart_version"]:
                command.extend(["--version", chart["chart_version"]])
            dl_chart = run_command(command, cwd=args.output_dir, text=True)

            if dl_chart.returncode:
                raise Exception(dl_chart.stderr)

            # Move files
            # for file in glob.glob(f"{self.DT_DIR.as_posix()}/*.wrap.tgz", recursive=False):
            #     output_fp = output_dir/Path(file).name
            #     print(f'Moving {file} to {output_fp}')
            #     shutil.move(file, output_fp)
        pretty_print_summary(f"Completed helm chart image download")

    def upload_helm_chart_nexus(self, args: Args):
        nexus = NexusHelper(url=args.registry, repository=args.repository)
        input_obj = Path(args.input)
        upload_files = []

        if args.input_type == InputType.PACKAGE:
            upload_files.append(input_obj)
        elif args.input_type == InputType.FOLDER:
            upload_files = list(input.glob("**/*.wrap.tgz"))
        else:
            raise ValueError(f"Unknown InputType: {args.input_type}")
        print(f"Files found for upload: {upload_files}")

        for file in upload_files:
            print(f"Uploading bitnami helm chart {file.name}..")
            resp = nexus.api_upload_helm_component(file)
            pretty_print_response(resp)
        pretty_print_summary("Upload helm chart to nexus completed!")

        # try:
        #     nexus.login_docker()
        #     for file in upload_files:
        #         print(f"Uploading bitnami helm chart {file.name}..")
        #         resp = nexus.api_upload_helm_component(file)
        #         pretty_print_response(resp)
        #     print("Uploading completed.")
        # finally:
        #     nexus.logout_docker()

    def upload_helm_chart_harbor(self, args: Args):
        harbor = HarborHelper(url=args.registry, project=args.repository)
        upload_files = []

        if args.input_type == InputType.PACKAGE:
            upload_files.append(args.input)
        elif args.input_type == InputType.FOLDER:
            # List tar files in directory
            upload_files = list(Path(args.input).glob("**/*.wrap.tgz"))
        else:
            raise ValueError(f"Unknown InputType: {args.input_type}")
        print(f"Files found for upload: {upload_files}")

        try:
            harbor.login()
            for file in upload_files:
                print(f"Uploading {file} to {harbor.project_url}..")
                command = [self.dt_fp, "unwrap", file, harbor.project_url, "--yes"]
                if os.environ.get("AIRGAPPER_INSECURE"):
                    print("AIRGAPPER_INSECURE flag. Using http protocol..")
                    command.append("--insecure")
                unwrap_cmd = run_command(command, text=True, bufsize=1)
                if unwrap_cmd.returncode:
                    raise Exception(unwrap_cmd.stderr)
        finally:
            harbor.logout()
        pretty_print_summary("Upload helm chart to harbor completed!")

    @staticmethod
    def extract_chart_and_version(text):
        RGX_PACKAGE_NAME = "(?P<chart>[^,]+),?(?P<chart_version>[.1-9]+)?"

        rgx_groups = re.search(RGX_PACKAGE_NAME, text)
        if not rgx_groups:
            raise Exception("Unable to extract helm chart name")
        return rgx_groups.groupdict()
