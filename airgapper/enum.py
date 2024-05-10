from enum import Enum


class Module(str, Enum):
    HELM = "helm"
    DOCKER = "docker"


class Action(str, Enum):
    DOWNLOAD = "download"
    UPLOAD = "upload"

class InputType(str, Enum):
    FILE = "file"
    TXT_FILE = "txt_file"
    FOLDER = "folder"