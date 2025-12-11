import os
from argparse import Namespace
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from airgapper.enum import Action, DockerRepository, InputType, Module, PypiRepository, HelmRepository, MavenRepository


@dataclass
class Args:
    """Main dataclass for parsing cli args"""
    module: Module
    action: Action
    input: str
    input_type: InputType
    output_dir: Path
    registry: str
    repository: Optional[str]
    application: Union[Enum, None]
    def __init__(self, args: Namespace):
        self.module = args.module
        self.action = args.action
        self.input = args.input
        self.input_type = self.determine_input_type(self.input)
        self.output_dir = args.output_dir
        self.repository = args.repository
        self.application = self.determine_application(args.application)
        self.registry = self.determine_registry(args.registry)

    def determine_input_type(self, input_type):
        # Check if file exist
        input_fp = Path(input_type)
        if self.action == Action.DOWNLOAD:
            if input_fp.exists() and input_fp.is_file():
                return InputType.FILE
            return InputType.PACKAGE
        elif self.action == Action.UPLOAD:
            if not input_fp.exists():
                raise ValueError(f"Unable to locate file/folder to upload: {input_fp}")
            if input_fp.is_dir():
                return InputType.FOLDER
            return InputType.PACKAGE

        raise ValueError(f"Unknown Action provided: {self.action}")

    def determine_application(self, application):
        if not application:
            return None
        module_map = {
            Module.DOCKER: DockerRepository,
            Module.PYPI: PypiRepository,
            Module.BITNAMI_HELM: HelmRepository,
            Module.MAVEN: MavenRepository
        }
        for module, cls in module_map.items():
            if self.module == module:
                return cls(application)
        # Raise if no match
        raise NotImplementedError

    def determine_registry(self, registry):
        # Required for Upload Action
        # Order of priority (desc):
        # 1. CLI args
        # 2. env var

        if self.action == Action.DOWNLOAD:
            return ""
        if registry:
            return registry

        # Take registry URL from env
        if self.application == DockerRepository.NEXUS:
            if self.module == Module.DOCKER:
                registry = os.getenv("AIRGAPPER_NEXUS_DOCKER_URL")
            else:
                registry = os.getenv("AIRGAPPER_NEXUS_URL")
        elif self.application == DockerRepository.HARBOR:
            registry = os.getenv("AIRGAPPER_HARBOR_URL")

        if not registry:
            raise ValueError("Registry URL is required for Upload. Please provide a registry URL in args or set in .env file.")
        return registry
