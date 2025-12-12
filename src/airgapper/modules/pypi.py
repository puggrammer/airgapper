from pathlib import Path

from airgapper.dataclasses import Args
from airgapper.enum import InputType
from airgapper.repositories import NexusHelper
from airgapper.utils import pretty_print_response, run_command, pretty_print_summary


class PypiHelper:

    def download_pypi_packages(self, args: Args):
        print(f"Args: {args}")

        # Check if output dir exist
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        input_list = []
        if args.input_type == InputType.PACKAGE:
            input_list.append(args.input)

            # Download pypi packages
            proc = run_command(["pip", "download", "--no-cache-dir", "-d", output_dir, args.input], text=True)
            pretty_print_summary(f"Completed pip download with status code {proc.returncode}")
            # pretty_print_completedprocess(proc)

        elif args.input_type == InputType.FILE:
            # Download pypi packages
            proc = run_command(["pip", "download", "--no-cache-dir", "-d", output_dir, "-r", args.input],
                               text=True)
            pretty_print_summary(f"Completed pip download with status code {proc.returncode}")
            # pretty_print_completedprocess(proc)
        else:
            raise Exception("No implementation for provided InputType.")

    def upload_pypi_packages_nexus(self, args: Args):
        nexus = NexusHelper(url=args.registry, repository=args.repository)

        upload_files = []
        if args.input_type == InputType.PACKAGE:
            upload_files.append(Path(args.input))
        elif args.input_type == InputType.FOLDER:
            upload_files = list(Path(args.input).iterdir())
        else:
            raise ValueError(f"Unknown InputType: {args.input_type}")
        print(f"Files found for upload: {upload_files}")

        for file in upload_files:
            print(f"Uploading python package {file.name}..")
            resp = nexus.api_upload_pypi_component(file)
            pretty_print_response(resp)
        pretty_print_summary("Upload pypi packages to nexus completed!")
