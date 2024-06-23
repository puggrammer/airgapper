
import os
from pathlib import Path
import getpass
import subprocess
import getpass
import requests

from airgapper.enum import InputType
from airgapper.modules.dataclasses import Args
from airgapper.utils import pretty_print_completedprocess, pretty_print_response

class PypiHelper:

    def download_pypi_packages(self, args: Args):
        print(f"Args: {args}")

        # Check if output dir exist
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        input_list = []
        if args.input_type == InputType.FILE:
            input_list.append(args.input)

            # Download pypi packages
            proc = subprocess.run(["pip", "download", "--no-cache-dir","-d", output_dir, args.input], capture_output=True, text=True)
            pretty_print_completedprocess(proc)

        elif args.input_type == InputType.TXT_FILE:
            # Download pypi packages
            proc = subprocess.run(["pip", "download", "--no-cache-dir","-d", output_dir, "-r", args.input], capture_output=True, text=True)
            pretty_print_completedprocess(proc)


    def upload_pypi_packages_nexus(self, args: Args):
        user, pwd = self._get_login_details()

        input_files = []
        if args.input_type == InputType.FILE:
            input_files.append(Path(args.input))
        elif args.input_type == InputType.FOLDER:
            input_files = list(Path(args.input).iterdir())
        print(f"Input files detected: {input_files}")

        
        for file in input_files:
            print(f"Uploading python package {file.name}..")
            resp = requests.post(
                f"http://{args.registry}/service/rest/v1/components",
                params={"repository": args.repository},
                headers={"accept": "application/json"}, # "Content-Type": "multipart/form-data"
                files={"pypi.asset": (file.name, open(file, 'rb'))},
                auth=(user, pwd)
                )
            pretty_print_response(resp)
        print("Uploading completed.")
        

    def _get_login_details(self):
        print("Logging in..")
        user = os.getenv("AIRGAPPER_PYPI_USER")
        if not user:
            user = input("Username:")
        pwd = os.getenv("AIRGAPPER_PYPI_PASS")
        if not pwd:
            pwd = getpass.getpass(f"Password for {user}:")
        return (user,pwd)
