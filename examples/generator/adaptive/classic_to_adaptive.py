"""
Classic-to-Adaptive bridge (v0 prototype, AE-29).

Reads a Classic SWC from ARXML with autosar.xml.Reader and writes an Adaptive
ServiceInterface description plus ara::com-style proxy/skeleton C++ headers.
Without arguments it converts the WheelSpeedSensor SWC of the template example.

PROTOTYPE ONLY - not a certified toolchain. See README.md in this directory.
"""
import argparse
import os
import sys
from autosar.generator import adaptive_bridge

EXAMPLE_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSIC_DIR = os.path.join(EXAMPLE_DIR, "..", "..", "template", "generated")
DEFAULT_INPUTS = ("AUTOSAR_Platform.arxml", "DataTypes.arxml", "PortInterfaces.arxml", "WheelSpeedSensor.arxml")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Command line arguments
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="*", help="Classic ARXML files (default: template example output)")
    parser.add_argument("--swc", default="WheelSpeedSensor", help="Short name or reference of the SWC")
    parser.add_argument("--service-name", help="ServiceInterface short name (default: <SWC>Service)")
    parser.add_argument("--service-id", type=lambda text: int(text, 0), default=0x1000,
                        help="SOME/IP service interface ID (default: 0x1000)")
    parser.add_argument("--major-version", type=int, default=1)
    parser.add_argument("--minor-version", type=int, default=0)
    parser.add_argument("--ara-include-prefix", default="../../ara",
                        help="Path from the generated headers to the 'ara' source directory of Adaptive-AUTOSAR")
    parser.add_argument("--out-dir", help="Output directory (default: generated/<service> next to this script)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """
    Runs the generator
    """
    args = parse_args(argv)
    inputs = args.inputs or [os.path.join(CLASSIC_DIR, name) for name in DEFAULT_INPUTS]
    classic = adaptive_bridge.ClassicModel()
    try:
        classic.load_files(inputs)
        model = adaptive_bridge.build_service_model(classic, args.swc, args.service_name, args.service_id,
                                                    args.major_version, args.minor_version)
    except adaptive_bridge.BridgeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    out_dir = args.out_dir or os.path.join(EXAMPLE_DIR, "generated", model.file_stem)
    files = adaptive_bridge.render_all(model, args.ara_include_prefix)
    adaptive_bridge.write_files(files, out_dir)
    print(f"{model.classic_swc_ref} -> {model.name} (service ID 0x{model.service_id:04X})")
    for event in model.events:
        print(f"  event  0x{event.event_id:04X} {event.name}: {event.data_type.name} <- {event.classic_element_ref}")
    for method in model.methods:
        print(f"  method 0x{method.method_id:04X} {method.name} <- {method.classic_operation_ref}")
    for cpp_type in model.types:
        print(f"  type   {cpp_type.name} = {cpp_type.target} <- {cpp_type.classic_ref}")
    for item in model.not_mapped:
        print(f"  not mapped (v0): {item}")
    for file_name in files:
        print(f"  wrote {file_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
