"""
Body Control Module (BCM) example.

Models a simplified BCM with two Software Components:
  - WindowController SWC with a provide port (sends window position)
  - DoorSensor SWC with a require port (receives window position)

The two SWCs are connected via a SenderReceiver interface.
Generates a valid ARXML file and validates it parses back correctly.
"""
import os
import sys
import autosar.xml
import autosar.xml.element as ar_element


def create_package_map(workspace: autosar.xml.Workspace):
    """
    Creates package map in workspace
    """
    workspace.create_package_map({
        "PlatformBaseTypes": "AUTOSAR_Platform/BaseTypes",
        "PlatformImplementationDataTypes": "AUTOSAR_Platform/ImplementationDataTypes",
        "PlatformDataConstraints": "AUTOSAR_Platform/DataConstraints",
        "PlatformCompuMethods": "AUTOSAR_Platform/CompuMethods",
        "Constants": "Constants",
        "PortInterfaces": "PortInterfaces",
        "ComponentTypes": "ComponentTypes",
    })


def create_platform_types(workspace: autosar.xml.Workspace):
    """
    Creates necessary platform types for the BCM
    """
    # Base types
    uint8_base_type = ar_element.SwBaseType('uint8', size=8)
    workspace.add_element("PlatformBaseTypes", uint8_base_type)

    uint16_base_type = ar_element.SwBaseType('uint16', size=16)
    workspace.add_element("PlatformBaseTypes", uint16_base_type)

    # Data constraint for window position (0-100 percent)
    window_pos_constr = ar_element.DataConstraint.make_internal(
        "WindowPosition_DataConstr", 0, 100
    )
    workspace.add_element("PlatformDataConstraints", window_pos_constr)

    # Compu method for window position (percent)
    computation = ar_element.Computation.make_rational(
        scaling_factor=1, offset=0, lower_limit=0, upper_limit=100
    )
    window_pos_compu = ar_element.CompuMethod(
        name="WindowPosition_CompuMethod",
        category="LINEAR",
        int_to_phys=computation,
        unit_ref=None,
    )
    workspace.add_element("PlatformCompuMethods", window_pos_compu)

    # Implementation data types
    sw_data_def_props = ar_element.SwDataDefPropsConditional(
        base_type_ref=uint8_base_type.ref(),
        data_constraint_ref=window_pos_constr.ref(),
        compu_method_ref=window_pos_compu.ref(),
    )
    uint8_impl_type = ar_element.ImplementationDataType(
        "uint8", category="VALUE", sw_data_def_props=sw_data_def_props
    )
    workspace.add_element("PlatformImplementationDataTypes", uint8_impl_type)

    sw_data_def_props = ar_element.SwDataDefPropsConditional(
        base_type_ref=uint16_base_type.ref()
    )
    uint16_impl_type = ar_element.ImplementationDataType(
        "uint16", category="VALUE", sw_data_def_props=sw_data_def_props
    )
    workspace.add_element("PlatformImplementationDataTypes", uint16_impl_type)


def create_sender_receiver_interface(workspace: autosar.xml.Workspace):
    """
    Creates the WindowPosition SenderReceiver interface
    """
    uint8_impl_t = workspace.find_element("PlatformImplementationDataTypes", "uint8")
    port_interface = ar_element.SenderReceiverInterface("WindowPosition_I")
    port_interface.create_data_element("WindowPosition", type_ref=uint8_impl_t.ref())
    workspace.add_element("PortInterfaces", port_interface)


def create_constants(workspace: autosar.xml.Workspace):
    """
    Creates init value constants
    """
    constant = ar_element.ConstantSpecification.make_constant("WindowPosition_IV", 0)
    workspace.add_element("Constants", constant)


def create_window_controller_swc(workspace: autosar.xml.Workspace):
    """
    Creates the WindowController SWC with a provide port.
    This component sends window position data.
    """
    window_pos_interface = workspace.find_element("PortInterfaces", "WindowPosition_I")
    window_pos_init = workspace.find_element("Constants", "WindowPosition_IV")

    swc = ar_element.ApplicationSoftwareComponentType("WindowController")
    workspace.add_element("ComponentTypes", swc)

    # Create provide port for sending window position
    swc.create_provide_port(
        "WindowPositionPort",
        window_pos_interface,
        com_spec={
            "init_value": window_pos_init.ref(),
            "uses_end_to_end_protection": False,
        },
    )

    # Create internal behavior
    behavior = swc.create_internal_behavior()

    init_runnable_name = swc.name + "_Init"
    periodic_runnable_name = swc.name + "_Run"

    behavior.create_runnable(
        init_runnable_name,
        can_be_invoked_concurrently=False,
        minimum_start_interval=0,
    )
    runnable = behavior.create_runnable(
        periodic_runnable_name,
        can_be_invoked_concurrently=False,
        minimum_start_interval=0,
    )
    runnable.create_port_access(["WindowPositionPort"])

    behavior.create_init_event(init_runnable_name)
    behavior.create_timing_event(periodic_runnable_name, period=0.02)

    # Create SWC Implementation
    impl = ar_element.SwcImplementation(
        "WindowController_Implementation",
        behavior_ref=swc.internal_behavior.ref(),
    )
    workspace.add_element("ComponentTypes", impl)


def create_door_sensor_swc(workspace: autosar.xml.Workspace):
    """
    Creates the DoorSensor SWC with a require port.
    This component receives window position data.
    """
    window_pos_interface = workspace.find_element("PortInterfaces", "WindowPosition_I")
    window_pos_init = workspace.find_element("Constants", "WindowPosition_IV")

    swc = ar_element.ApplicationSoftwareComponentType("DoorSensor")
    workspace.add_element("ComponentTypes", swc)

    # Create require port for receiving window position
    swc.create_require_port(
        "WindowPositionPort",
        window_pos_interface,
        com_spec={
            "init_value": window_pos_init.ref(),
            "alive_timeout": 0,
            "enable_update": False,
            "uses_end_to_end_protection": False,
            "handle_never_received": False,
        },
    )

    # Create internal behavior
    behavior = swc.create_internal_behavior()

    init_runnable_name = swc.name + "_Init"
    periodic_runnable_name = swc.name + "_Run"

    behavior.create_runnable(
        init_runnable_name,
        can_be_invoked_concurrently=False,
        minimum_start_interval=0,
    )
    runnable = behavior.create_runnable(
        periodic_runnable_name,
        can_be_invoked_concurrently=False,
        minimum_start_interval=0,
    )
    runnable.create_port_access(["WindowPositionPort"])

    behavior.create_init_event(init_runnable_name)
    behavior.create_timing_event(periodic_runnable_name, period=0.02)

    # Create SWC Implementation
    impl = ar_element.SwcImplementation(
        "DoorSensor_Implementation",
        behavior_ref=swc.internal_behavior.ref(),
    )
    workspace.add_element("ComponentTypes", impl)


def create_composition(workspace: autosar.xml.Workspace):
    """
    Creates the BCM composition connecting WindowController and DoorSensor
    """
    swc = ar_element.CompositionSwComponentType("BodyControlModule")
    swc.create_component_prototype(
        workspace.find_element("ComponentTypes", "WindowController")
    )
    swc.create_component_prototype(
        workspace.find_element("ComponentTypes", "DoorSensor")
    )
    # Element must be added to workspace before connectors can be created
    workspace.add_element("ComponentTypes", swc)
    swc.create_connector(
        "WindowController/WindowPositionPort",
        "DoorSensor/WindowPositionPort",
        workspace,
    )


def save_xml_files(workspace: autosar.xml.Workspace, output_dir: str) -> str:
    """
    Saves workspace as ARXML documents.
    Returns the path to the main BCM arxml file.
    """
    workspace.set_document_root(output_dir)
    workspace.create_document(
        "bcm_platform.arxml", packages="/AUTOSAR_Platform"
    )
    workspace.create_document("bcm_constants.arxml", packages="/Constants")
    workspace.create_document(
        "bcm_portinterfaces.arxml", packages="/PortInterfaces"
    )
    workspace.create_document_mapping(
        package_ref="/ComponentTypes",
        element_types=ar_element.SwComponentType,
        suffix_filters=["_Implementation"],
    )
    workspace.write_documents()
    return output_dir


def validate_arxml(output_dir: str):
    """
    Validates generated ARXML files by parsing them back with the reader
    and checking that all expected elements are present.
    """
    reader = autosar.xml.Reader()
    # Only validate files generated by this script
    bcm_files = [
        "bcm_platform.arxml",
        "bcm_constants.arxml",
        "bcm_portinterfaces.arxml",
        "WindowController.arxml",
        "WindowController_Implementation.arxml",
        "DoorSensor.arxml",
        "DoorSensor_Implementation.arxml",
        "BodyControlModule.arxml",
    ]
    arxml_files = [f for f in bcm_files if os.path.isfile(os.path.join(output_dir, f))]
    assert len(arxml_files) > 0, "No ARXML files found"

    print(f"Found {len(arxml_files)} ARXML file(s) to validate:")
    for fname in arxml_files:
        print(f"  - {fname}")

    # Read all generated files into a fresh workspace
    workspace = autosar.xml.Workspace()
    for fname in arxml_files:
        filepath = os.path.join(output_dir, fname)
        document = reader.read_file(filepath)
        if document is not None:
            for pkg in document.packages:
                existing = workspace.find(f"/{pkg.name}")
                if existing is None:
                    workspace.append(pkg)
                else:
                    # Merge elements from duplicate package
                    for elem in pkg.elements:
                        existing.append(elem)
            print(f"  Parsed {fname}: OK")
        else:
            print(f"  Parsed {fname}: FAILED - returned None")
            sys.exit(1)

    # Verify key elements exist after round-trip
    checks = {
        "SenderReceiverInterface": (
            "/PortInterfaces",
            "WindowPosition_I",
        ),
        "WindowController SWC": (
            "/ComponentTypes",
            "WindowController",
        ),
        "DoorSensor SWC": (
            "/ComponentTypes",
            "DoorSensor",
        ),
        "BCM Composition": (
            "/ComponentTypes",
            "BodyControlModule",
        ),
        "WindowController Implementation": (
            "/ComponentTypes",
            "WindowController_Implementation",
        ),
        "DoorSensor Implementation": (
            "/ComponentTypes",
            "DoorSensor_Implementation",
        ),
    }

    print("\nValidation checks:")
    all_passed = True
    for label, (pkg_path, elem_name) in checks.items():
        pkg = workspace.find(pkg_path)
        if pkg is None:
            print(f"  FAIL: Package {pkg_path} not found")
            all_passed = False
            continue
        elem = pkg.find(elem_name)
        if elem is None:
            print(f"  FAIL: {label} ({elem_name}) not found in {pkg_path}")
            all_passed = False
        else:
            print(f"  PASS: {label} ({elem_name})")

    if all_passed:
        print("\nAll validation checks passed!")
    else:
        print("\nSome validation checks failed!")
        sys.exit(1)


def main():
    """
    Main entry point.
    Creates a BCM model with WindowController and DoorSensor SWCs,
    generates ARXML, and validates the output.
    """
    output_dir = os.path.join(os.path.dirname(__file__), "data")

    # Create workspace
    workspace = autosar.xml.Workspace()
    workspace.behavior_settings.update({
        "init_event_prefix": "IT",
        "timing_event_prefix": "TMT",
        "data_send_point_prefix": "SEND",
        "data_receive_point_prefix": "REC",
    })

    create_package_map(workspace)
    create_platform_types(workspace)
    create_sender_receiver_interface(workspace)
    create_constants(workspace)
    create_window_controller_swc(workspace)
    create_door_sensor_swc(workspace)
    create_composition(workspace)

    print("=== Body Control Module (BCM) ARXML Generator ===\n")
    print("Components:")
    print("  - WindowController SWC (provide port: WindowPositionPort)")
    print("  - DoorSensor SWC (require port: WindowPositionPort)")
    print("  - BodyControlModule composition (assembly connector)")
    print(f"\nGenerating ARXML files to: {output_dir}\n")

    save_xml_files(workspace, output_dir)
    print("ARXML files generated successfully.\n")

    print("--- Validating generated ARXML (round-trip parse) ---\n")
    validate_arxml(output_dir)


if __name__ == "__main__":
    main()
