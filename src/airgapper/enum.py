from enum import Enum


class Module(str, Enum):
    BITNAMI_HELM = "bitnami_helm"
    HELM = "helm"
    DOCKER = "docker"
    PYPI = "pypi"


class Action(str, Enum):
    DOWNLOAD = "download"
    UPLOAD = "upload"

class InputType(str, Enum):
    PACKAGE = "package"
    TXT_FILE = "txt_file"
    FOLDER = "folder"

class DockerRepository(str, Enum):
    DOCKER_REGISTRY = "docker_registry"
    HARBOR = "harbor"
    NEXUS = "nexus"

class PypiRepository(str, Enum):
    NEXUS = "nexus"

class HelmRepository(str, Enum):
    HARBOR = "harbor"
    NEXUs = "nexus"