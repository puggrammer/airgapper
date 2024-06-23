from enum import Enum


class Module(str, Enum):
    HELM = "helm"
    DOCKER = "docker"
    PYPI = "pypi"


class Action(str, Enum):
    DOWNLOAD = "download"
    UPLOAD = "upload"

class InputType(str, Enum):
    FILE = "file"
    TXT_FILE = "txt_file"
    FOLDER = "folder"

class DockerRegistry(str, Enum):
    DOCKER_REGISTRY = "docker_registry"
    HARBOR = "harbor"
    NEXUS = "nexus"

class PypiRegistry(str, Enum):
    NEXUS = "nexus"