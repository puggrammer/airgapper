"""
Use VMWare "dt" plugin to download helm chart and all its dependencies at one shot.
Need make sure that the helm chart is OCI-Compliant.

Observed to require linux dt plugin to work on linux destination helm registry.

Example:
./dt unwrap rabbitmq.wrap.tgz harbor.arpa/library --yes
"""

import glob
import shutil
import logging
import platform
import subprocess
from pathlib import Path

from airgapper.enum import InputType
from airgapper.modules.dataclasses import Args

DT_DIR = Path('./bin/dt-linux')

def download_helm_chart(args):
    if platform.system() == 'Windows':
        logging.error("CAUTION: Use of Windows' dt plugin doesn't upload properly on linux registry server. Please use Bash.")
        exit(1)
    assert_dt_present()

    input_fp = Path(args.input_filepath)
    input_list = []
    with open(input_fp, "r") as f:
        for line in f.readlines():
            parts = line.strip().split(',')
            chart = {'chart': parts[0].strip()}
            if len(parts) > 1:
                chart['version'] = parts[1].strip()
            input_list.append(chart)
    
    # Check if output dir exist
    output_dir = Path(args.output_dir if args.output_dir else './output/helm')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download helm chart
    for chart in input_list:
        command = ["./dt","wrap", chart['chart']]
        if 'version' in chart:
            command.extend(['--version', chart['version']])
        dl_chart = subprocess.run(command, cwd=DT_DIR, capture_output=True, text=True)
        print(dl_chart.stdout)
        if dl_chart.returncode:
            raise Exception(dl_chart.stderr)
        
        # Move file
        for file in glob.glob(f"{DT_DIR.as_posix()}/*.wrap.tgz", recursive=False):
            output_fp = output_dir/Path(file).name
            print(f'Moving {file} to {output_fp}')
            shutil.move(file, output_fp)


def upload_helm_chart(args: Args):
    REGISTRY = args.registry
    REPOSITORY = args.repository
    UPLOAD_DIR = Path(args.input)

    assert_dt_present()

    try:
        print("Logging in registry..")
        login_cmd = subprocess.run(["docker", "login", REGISTRY])
        if login_cmd.returncode:
            print("Exception occured during logging in.")
            print(f"{login_cmd=}")
            exit(1)

        files = []
        if args.input_type == InputType.FILE:
            files.append(args.input)
        else:
            # List tar files in directory
            files = list(UPLOAD_DIR.glob("**/*.wrap.tgz"))

        url = f"{REGISTRY}/{REPOSITORY}"
        for file in files:
            print(f"Uploading {file} to {url}..")
            unwrap_cmd = subprocess.run([DT_DIR/"dt", "unwrap", file, url, '--yes'],
                                        capture_output=True, text=True)
            print(unwrap_cmd.stdout)
            if unwrap_cmd.returncode:
                raise Exception(unwrap_cmd.stderr)
    finally:
        print("Logging out registry..")
        subprocess.run(["docker", "logout", REGISTRY])


def assert_dt_present():
    dt_fp = DT_DIR / 'dt'
    if dt_fp.exists() and dt_fp.is_file():
        return
    raise Exception(
        f"dt executable not found in {DT_DIR}. please download at github.com/vmware-labs/distribution-tooling-for-helm.")


