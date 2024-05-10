from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

from airgapper.enum import Action, InputType, Module

@dataclass
class Args:
    module: Module
    action: Action
    input: str
    input_type: InputType
    output_dir: Path
    registry: str
    repository: str
    def __init__(self, args: Namespace):
        self.module = args.module
        self.action = args.action
        self.input = args.input
        self.input_type = self.determine_input_type(self.input)
        self.output_dir = args.output_dir
        self.registry = args.registry
        self.repository = args.repository

    def determine_input_type(self, input):
        # Check if file exist
        input_fp = Path(input)
        if self.action == Action.DOWNLOAD:
            if input_fp.exists() and input_fp.is_file():
                return InputType.TXT_FILE  
            return InputType.FILE
        
        elif self.action == Action.UPLOAD:
            if not input_fp.exists():
                raise Exception(f"Unable to locate file to upload: {input_fp}")
            if input_fp.is_dir():
                return InputType.FOLDER
            return InputType.FILE
        
        raise Exception(f"Unknown Action provided: {self.action}")

