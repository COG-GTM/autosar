"""
Generates the ACC architecture diagram directly from the workspace model.
"""

import os
from acc_system import component, diagram, generator


def main():
    """Main"""
    workspace = generator.create_workspace()
    composition_ref = component.AccComposition.ref(workspace)
    output_base_path = os.path.join(os.path.dirname(__file__), "acc_system", "diagram", "acc_architecture")
    for file_path in diagram.create_diagram(workspace, composition_ref, output_base_path):
        print(f"Generated {file_path}")


if __name__ == "__main__":
    main()
