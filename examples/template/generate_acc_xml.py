"""
Generates the Adaptive Cruise Control (ACC) example project.

The entire project is created by applying a single template (the composition
component), then written once per supported schema version.
"""

import os
from acc_system import generator


def main():
    """Main"""
    for schema_version in generator.SCHEMA_VERSIONS:
        document_root = generator.schema_dir(schema_version)
        os.makedirs(document_root, exist_ok=True)
        workspace = generator.create_workspace(document_root)
        workspace.write_documents(schema_version=schema_version)
        print(f"Generated ARXML for schema version {schema_version} in {document_root}")


if __name__ == "__main__":
    main()
