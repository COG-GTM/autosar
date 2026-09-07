"""
Workspace creation for the ACC example.

Everything below the composition is created transitively, applying the
composition template is enough to generate the entire project.
"""

import os
import autosar.xml.workspace as ar_workspace
from . import component, platform

SCHEMA_VERSIONS = [48, 49, 50, 51]

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "acc_config.toml")
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")


def schema_dir(schema_version: int, base_dir: str | None = None) -> str:
    """
    Returns the output directory used for the given schema version
    """
    base_dir = GENERATED_DIR if base_dir is None else base_dir
    return os.path.join(base_dir, f"schema_{schema_version}")


def create_workspace(document_root: str | None = None) -> ar_workspace.Workspace:
    """
    Creates a workspace containing the entire ACC project
    """
    workspace = ar_workspace.Workspace(CONFIG_FILE_PATH, document_root=document_root)
    workspace.apply(platform.ImplementationTypes.boolean)
    workspace.apply(platform.ImplementationTypes.uint8)
    workspace.apply(platform.ImplementationTypes.uint16)
    workspace.apply(platform.ImplementationTypes.uint32)
    workspace.apply(component.AccComposition)
    return workspace
