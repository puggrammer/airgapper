"""
Use VMWare "dt" plugin to download helm chart and all its dependencies at one shot.
Need make sure that the helm chart is OCI-Compliant.

Observed to require linux dt plugin to work on linux destination helm registry.

Example:
./dt unwrap rabbitmq.wrap.tgz harbor.arpa/library --yes
"""

import os
import re
import sys
import logging
import platform
import subprocess
from pathlib import Path

from airgapper.enum import InputType
from airgapper.dataclasses import Args
from airgapper.utils import run_command, pretty_print_response
from airgapper.repositories import NexusHelper, HarborHelper


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
        if self.DT_DIR:
            dt_fp = Path(self.DT_DIR) / "dt"
            if dt_fp.exists() and dt_fp.is_file():
                self.dt_fp = dt_fp.as_posix()
                return

        resp = subprocess.run(
            ["dt", "version"], capture_output=True, text=True, check=False
        )
        if not resp.returncode:
            print(resp.stdout)
            self.dt_fp = "dt"
            return

        raise AssertionError(
            "✖ dt plugin not installed."
            "Please download at github.com/vmware-labs/distribution-tooling-for-helm."
            "Install dt standalone at /usr/local/bin location."
        )

    def download_helm_charts(self, args: Args):
        if platform.system() == "Windows":
            logging.error(
                "CAUTION: Use of Windows' dt plugin doesn't upload properly on linux registry server. Please use Bash."
            )
            sys.exit(1)

        input_list = []
        if args.input_type == InputType.PACKAGE:
            input_list.append(self.extract_chart_and_version(args.input))

        elif args.input_type == InputType.TXT_FILE:
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
        print(f"input_list: {input_list}")
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
        print("Uploading completed.")

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
                unwrap_cmd = run_command(command, text=True)
                if unwrap_cmd.returncode:
                    raise Exception(unwrap_cmd.stderr)
        finally:
            harbor.logout()

    @staticmethod
    def extract_chart_and_version(text):
        RGX_PACKAGE_NAME = "(?P<chart>[^,]+),?(?P<chart_version>[.1-9]+)?"

        rgx_groups = re.search(RGX_PACKAGE_NAME, text)
        if not rgx_groups:
            raise Exception("Unable to extract helm chart name")
        return rgx_groups.groupdict()
