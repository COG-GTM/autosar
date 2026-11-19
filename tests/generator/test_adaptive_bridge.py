"""Unit tests for the Classic-to-Adaptive bridge (v0 prototype, AE-29)"""

# pylint: disable=missing-class-docstring, missing-function-docstring, wrong-import-position
import os
import sys
import tempfile
import unittest
from lxml import etree
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
import autosar.xml.element as ar_element  # noqa E402
from autosar.generator import adaptive_bridge as bridge  # noqa E402

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
CLASSIC_DIR = os.path.join(REPO_DIR, "examples", "template", "generated")
EXAMPLE_DIR = os.path.join(REPO_DIR, "examples", "generator", "adaptive")
NS = {"ar": "http://autosar.org/schema/r4.0"}

SYNTHETIC_ARXML = """<?xml version="1.0" encoding="utf-8"?>
<AUTOSAR xmlns="http://autosar.org/schema/r4.0">
  <AR-PACKAGES>
    <AR-PACKAGE>
      <SHORT-NAME>Types</SHORT-NAME>
      <ELEMENTS>
        <SW-BASE-TYPE>
          <SHORT-NAME>sint16</SHORT-NAME>
          <BASE-TYPE-SIZE>16</BASE-TYPE-SIZE>
          <BASE-TYPE-ENCODING>2C</BASE-TYPE-ENCODING>
        </SW-BASE-TYPE>
        <IMPLEMENTATION-DATA-TYPE>
          <SHORT-NAME>Torque_T</SHORT-NAME>
          <CATEGORY>VALUE</CATEGORY>
          <SW-DATA-DEF-PROPS>
            <SW-DATA-DEF-PROPS-VARIANTS>
              <SW-DATA-DEF-PROPS-CONDITIONAL>
                <BASE-TYPE-REF DEST="SW-BASE-TYPE">/Types/sint16</BASE-TYPE-REF>
              </SW-DATA-DEF-PROPS-CONDITIONAL>
            </SW-DATA-DEF-PROPS-VARIANTS>
          </SW-DATA-DEF-PROPS>
        </IMPLEMENTATION-DATA-TYPE>
        <IMPLEMENTATION-DATA-TYPE>
          <SHORT-NAME>TorqueLimit_T</SHORT-NAME>
          <CATEGORY>TYPE_REFERENCE</CATEGORY>
          <SW-DATA-DEF-PROPS>
            <SW-DATA-DEF-PROPS-VARIANTS>
              <SW-DATA-DEF-PROPS-CONDITIONAL>
                <IMPLEMENTATION-DATA-TYPE-REF DEST="IMPLEMENTATION-DATA-TYPE"
                >/Types/Torque_T</IMPLEMENTATION-DATA-TYPE-REF>
              </SW-DATA-DEF-PROPS-CONDITIONAL>
            </SW-DATA-DEF-PROPS-VARIANTS>
          </SW-DATA-DEF-PROPS>
        </IMPLEMENTATION-DATA-TYPE>
        <IMPLEMENTATION-DATA-TYPE>
          <SHORT-NAME>Samples_T</SHORT-NAME>
          <CATEGORY>ARRAY</CATEGORY>
        </IMPLEMENTATION-DATA-TYPE>
      </ELEMENTS>
    </AR-PACKAGE>
    <AR-PACKAGE>
      <SHORT-NAME>Interfaces</SHORT-NAME>
      <ELEMENTS>
        <SENDER-RECEIVER-INTERFACE>
          <SHORT-NAME>Torque_I</SHORT-NAME>
          <DATA-ELEMENTS>
            <VARIABLE-DATA-PROTOTYPE>
              <SHORT-NAME>Value</SHORT-NAME>
              <TYPE-TREF DEST="IMPLEMENTATION-DATA-TYPE">/Types/Torque_T</TYPE-TREF>
            </VARIABLE-DATA-PROTOTYPE>
            <VARIABLE-DATA-PROTOTYPE>
              <SHORT-NAME>Limit</SHORT-NAME>
              <TYPE-TREF DEST="IMPLEMENTATION-DATA-TYPE">/Types/TorqueLimit_T</TYPE-TREF>
            </VARIABLE-DATA-PROTOTYPE>
          </DATA-ELEMENTS>
        </SENDER-RECEIVER-INTERFACE>
        <SENDER-RECEIVER-INTERFACE>
          <SHORT-NAME>Samples_I</SHORT-NAME>
          <DATA-ELEMENTS>
            <VARIABLE-DATA-PROTOTYPE>
              <SHORT-NAME>Samples</SHORT-NAME>
              <TYPE-TREF DEST="IMPLEMENTATION-DATA-TYPE">/Types/Samples_T</TYPE-TREF>
            </VARIABLE-DATA-PROTOTYPE>
          </DATA-ELEMENTS>
        </SENDER-RECEIVER-INTERFACE>
        <CLIENT-SERVER-INTERFACE>
          <SHORT-NAME>Calibration_I</SHORT-NAME>
          <OPERATIONS>
            <CLIENT-SERVER-OPERATION>
              <SHORT-NAME>Adjust</SHORT-NAME>
              <ARGUMENTS>
                <ARGUMENT-DATA-PROTOTYPE>
                  <SHORT-NAME>offset</SHORT-NAME>
                  <TYPE-TREF DEST="IMPLEMENTATION-DATA-TYPE">/Types/Torque_T</TYPE-TREF>
                  <DIRECTION>INOUT</DIRECTION>
                </ARGUMENT-DATA-PROTOTYPE>
              </ARGUMENTS>
            </CLIENT-SERVER-OPERATION>
            <CLIENT-SERVER-OPERATION>
              <SHORT-NAME>Reset</SHORT-NAME>
            </CLIENT-SERVER-OPERATION>
          </OPERATIONS>
        </CLIENT-SERVER-INTERFACE>
      </ELEMENTS>
    </AR-PACKAGE>
    <AR-PACKAGE>
      <SHORT-NAME>Components</SHORT-NAME>
      <ELEMENTS>
        <APPLICATION-SW-COMPONENT-TYPE>
          <SHORT-NAME>TorqueSensor</SHORT-NAME>
          <PORTS>
            <P-PORT-PROTOTYPE>
              <SHORT-NAME>Front</SHORT-NAME>
              <PROVIDED-INTERFACE-TREF DEST="SENDER-RECEIVER-INTERFACE">/Interfaces/Torque_I</PROVIDED-INTERFACE-TREF>
            </P-PORT-PROTOTYPE>
            <P-PORT-PROTOTYPE>
              <SHORT-NAME>Rear</SHORT-NAME>
              <PROVIDED-INTERFACE-TREF DEST="SENDER-RECEIVER-INTERFACE">/Interfaces/Torque_I</PROVIDED-INTERFACE-TREF>
            </P-PORT-PROTOTYPE>
            <P-PORT-PROTOTYPE>
              <SHORT-NAME>Calibration</SHORT-NAME>
              <PROVIDED-INTERFACE-TREF DEST="CLIENT-SERVER-INTERFACE"
              >/Interfaces/Calibration_I</PROVIDED-INTERFACE-TREF>
            </P-PORT-PROTOTYPE>
            <R-PORT-PROTOTYPE>
              <SHORT-NAME>Reference</SHORT-NAME>
              <REQUIRED-INTERFACE-TREF DEST="SENDER-RECEIVER-INTERFACE">/Interfaces/Torque_I</REQUIRED-INTERFACE-TREF>
            </R-PORT-PROTOTYPE>
          </PORTS>
        </APPLICATION-SW-COMPONENT-TYPE>
        <APPLICATION-SW-COMPONENT-TYPE>
          <SHORT-NAME>ArraySender</SHORT-NAME>
          <PORTS>
            <P-PORT-PROTOTYPE>
              <SHORT-NAME>Samples</SHORT-NAME>
              <PROVIDED-INTERFACE-TREF DEST="SENDER-RECEIVER-INTERFACE">/Interfaces/Samples_I</PROVIDED-INTERFACE-TREF>
            </P-PORT-PROTOTYPE>
          </PORTS>
        </APPLICATION-SW-COMPONENT-TYPE>
        <APPLICATION-SW-COMPONENT-TYPE>
          <SHORT-NAME>Consumer</SHORT-NAME>
          <PORTS>
            <R-PORT-PROTOTYPE>
              <SHORT-NAME>Torque</SHORT-NAME>
              <REQUIRED-INTERFACE-TREF DEST="SENDER-RECEIVER-INTERFACE">/Interfaces/Torque_I</REQUIRED-INTERFACE-TREF>
            </R-PORT-PROTOTYPE>
            <P-PORT-PROTOTYPE>
              <SHORT-NAME>Dangling</SHORT-NAME>
              <PROVIDED-INTERFACE-TREF DEST="SENDER-RECEIVER-INTERFACE">/Interfaces/Missing_I</PROVIDED-INTERFACE-TREF>
            </P-PORT-PROTOTYPE>
          </PORTS>
        </APPLICATION-SW-COMPONENT-TYPE>
      </ELEMENTS>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>
"""


def load_demo(*file_names: str) -> bridge.ClassicModel:
    classic = bridge.ClassicModel()
    classic.load_files(os.path.join(CLASSIC_DIR, file_name) for file_name in file_names)
    return classic


def wheel_speed_model() -> bridge.ServiceModel:
    classic = load_demo("AUTOSAR_Platform.arxml", "DataTypes.arxml", "PortInterfaces.arxml", "WheelSpeedSensor.arxml")
    return bridge.build_service_model(classic, "WheelSpeedSensor")


def timer_model() -> bridge.ServiceModel:
    classic = load_demo("AUTOSAR_Platform.arxml", "PortInterfaces.arxml", "TimerComponent.arxml")
    return bridge.build_service_model(classic, "TimerComponent", service_id=0x1001)


def synthetic_model(swc_name: str = "TorqueSensor") -> bridge.ServiceModel:
    classic = bridge.ClassicModel()
    classic.load_str(SYNTHETIC_ARXML)
    return bridge.build_service_model(classic, swc_name)


class SenderReceiverToEventTests(unittest.TestCase):
    """Rule: sender-receiver port / data element -> Adaptive Event (on the Demo 1 WheelSpeedSensor SWC)"""

    def setUp(self):
        self.model = wheel_speed_model()

    def test_service(self):
        self.assertEqual(self.model.name, "WheelSpeedSensorService")
        self.assertEqual(self.model.classic_swc_ref, "/ComponentTypes/WheelSpeedSensor")
        self.assertEqual(self.model.service_id, 0x1000)
        self.assertEqual(self.model.namespace, ("generated", "wheelspeedsensorservice"))
        self.assertEqual(self.model.file_stem, "wheel_speed_sensor_service")

    def test_event(self):
        self.assertEqual(len(self.model.events), 1)
        self.assertEqual(self.model.methods, [])
        event = self.model.events[0]
        self.assertEqual(event.name, "WheelSpeed")
        self.assertEqual(event.event_id, 0x8001)
        self.assertEqual(event.classic_port_ref, "/ComponentTypes/WheelSpeedSensor/WheelSpeed")
        self.assertEqual(event.classic_element_ref, "/PortInterfaces/WheelSpeed_I/WheelSpeed")
        self.assertEqual(event.data_type.name, "WheelSpeed_T")

    def test_compu_method_is_reported_as_not_mapped(self):
        self.assertEqual(len(self.model.not_mapped), 1)
        self.assertIn("/DataTypes/CompuMethods/WheelSpeed_T_CompuMethod", self.model.not_mapped[0])

    def test_name_collision_uses_port_prefix(self):
        model = synthetic_model()
        self.assertEqual([event.name for event in model.events],
                         ["Front_Value", "Front_Limit", "Rear_Value", "Rear_Limit"])
        self.assertEqual([event.event_id for event in model.events], [0x8001, 0x8002, 0x8003, 0x8004])

    def test_require_port_is_not_mapped(self):
        model = synthetic_model()
        self.assertTrue(any("/Components/TorqueSensor/Reference: RequirePortPrototype" in item
                            for item in model.not_mapped))

    def test_unresolved_reference_is_rejected(self):
        with self.assertRaisesRegex(bridge.BridgeError, "cannot be resolved"):
            synthetic_model("Consumer")

    def test_unknown_swc_is_rejected(self):
        with self.assertRaisesRegex(bridge.BridgeError, "exactly one SWC"):
            synthetic_model("NoSuchComponent")


class ClientServerToMethodTests(unittest.TestCase):
    """Rule: client-server port / operation -> Adaptive Method (on the TimerComponent SWC of the same example)"""

    def setUp(self):
        self.model = timer_model()

    def test_methods(self):
        self.assertEqual(self.model.events, [])
        self.assertEqual([(method.name, method.method_id) for method in self.model.methods],
                         [("GetTime", 1), ("IsTimerElapsed", 2)])
        self.assertEqual(self.model.methods[0].classic_operation_ref, "/PortInterfaces/FreeRunningTimer_I/GetTime")

    def test_arguments(self):
        get_time, is_timer_elapsed = self.model.methods
        self.assertEqual([(arg.name, arg.direction, arg.data_type.name) for arg in get_time.arguments],
                         [("value", "OUT", "uint32")])
        self.assertEqual([(arg.name, arg.direction, arg.data_type.name) for arg in is_timer_elapsed.arguments],
                         [("startTime", "IN", "uint32"), ("duration", "IN", "uint32"), ("result", "OUT", "boolean")])
        self.assertEqual([arg.name for arg in is_timer_elapsed.in_arguments], ["startTime", "duration"])
        self.assertEqual([arg.name for arg in is_timer_elapsed.out_arguments], ["result"])

    def test_inout_and_no_arguments(self):
        model = synthetic_model()
        adjust, reset = model.methods
        self.assertEqual(adjust.in_arguments, adjust.out_arguments)
        self.assertEqual(adjust.arguments[0].direction, "INOUT")
        self.assertEqual(reset.arguments, ())
        skeleton = bridge.render_skeleton_header(model, "../../ara")
        self.assertIn("virtual bool Adjust(Torque_T &offset) = 0;", skeleton)
        self.assertIn("virtual bool Reset() = 0;", skeleton)
        proxy = bridge.render_proxy_header(model, "../../ara")
        self.assertIn("void Adjust(Torque_T offset, AdjustHandler responseHandler)", proxy)
        self.assertIn("using ResetHandler = std::function<void(bool)>;", proxy)


class ImplementationDataTypeToCppTests(unittest.TestCase):
    """Rule: ImplementationDataType -> C++ type"""

    def test_base_type_mapping(self):
        cases = [
            (ar_element.SwBaseType("uint8", size=8, encoding="uint8"), "std::uint8_t"),
            (ar_element.SwBaseType("uint16", size=16, encoding="uint16"), "std::uint16_t"),
            (ar_element.SwBaseType("uint32", size=32), "std::uint32_t"),
            (ar_element.SwBaseType("uint64", size=64, encoding="NONE"), "std::uint64_t"),
            (ar_element.SwBaseType("sint8", size=8, encoding="2C"), "std::int8_t"),
            (ar_element.SwBaseType("sint32", size=32), "std::int32_t"),
            (ar_element.SwBaseType("MyInt", size=64, encoding="2C"), "std::int64_t"),
            (ar_element.SwBaseType("boolean", size=8, encoding="BOOLEAN"), "bool"),
            (ar_element.SwBaseType("float32", size=32, encoding="IEEE754"), "float"),
            (ar_element.SwBaseType("float64", size=64, encoding="IEEE754"), "double"),
        ]
        for base_type, expected in cases:
            with self.subTest(base_type=base_type.name):
                self.assertEqual(bridge.base_type_to_cpp(base_type), expected)

    def test_unsupported_base_type_size(self):
        with self.assertRaises(bridge.BridgeError):
            bridge.base_type_to_cpp(ar_element.SwBaseType("uint24", size=24))

    def test_wheel_speed_type(self):
        cpp_type = wheel_speed_model().types[0]
        self.assertEqual(cpp_type.name, "WheelSpeed_T")
        self.assertEqual(cpp_type.target, "std::uint16_t")
        self.assertEqual(cpp_type.classic_ref, "/DataTypes/ImplementationDataTypes/WheelSpeed_T")
        self.assertEqual(cpp_type.base_type_ref, "/AUTOSAR_Platform/BaseTypes/uint16")

    def test_platform_types(self):
        self.assertEqual([(cpp_type.name, cpp_type.target) for cpp_type in timer_model().types],
                         [("uint32", "std::uint32_t"), ("boolean", "bool")])

    def test_type_reference_is_ordered_after_its_target(self):
        model = synthetic_model()
        self.assertEqual([(cpp_type.name, cpp_type.target) for cpp_type in model.types],
                         [("Torque_T", "std::int16_t"), ("TorqueLimit_T", "Torque_T")])
        header = bridge.render_types_header(model)
        self.assertLess(header.index("using Torque_T = std::int16_t;"),
                        header.index("using TorqueLimit_T = Torque_T;"))

    def test_array_type_is_rejected(self):
        with self.assertRaisesRegex(bridge.BridgeError, "category ARRAY"):
            synthetic_model("ArraySender")

    def test_types_header(self):
        header = bridge.render_types_header(wheel_speed_model())
        self.assertIn("using WheelSpeed_T = std::uint16_t;", header)
        self.assertIn("#ifndef WHEEL_SPEED_SENSOR_SERVICE_TYPES_H", header)
        self.assertIn("not a certified toolchain", header)


class OutputTests(unittest.TestCase):

    def test_arxml_content(self):
        root = etree.fromstring(bridge.render_arxml(wheel_speed_model()).encode("utf-8"))
        deployment = "ar:AR-PACKAGES/ar:AR-PACKAGE/ar:ELEMENTS/ar:SOMEIP-SERVICE-INTERFACE-DEPLOYMENT"
        self.assertEqual(root.findtext(deployment + "/ar:SERVICE-INTERFACE-ID", namespaces=NS), str(0x1000))
        self.assertEqual(root.findtext(deployment + "//ar:EVENT-ID", namespaces=NS), str(0x8001))
        events = root.findall(".//ar:SERVICE-INTERFACE/ar:EVENTS/ar:VARIABLE-DATA-PROTOTYPE", namespaces=NS)
        self.assertEqual([event.findtext("ar:SHORT-NAME", namespaces=NS) for event in events], ["WheelSpeed"])
        self.assertEqual(events[0].findtext("ar:TYPE-TREF", namespaces=NS),
                         "/WheelSpeedSensorServiceManifest/WheelSpeed_T")

    def test_arxml_references_resolve(self):
        for model in (wheel_speed_model(), timer_model(), synthetic_model()):
            root = etree.fromstring(bridge.render_arxml(model).encode("utf-8"))
            package = root.find("ar:AR-PACKAGES/ar:AR-PACKAGE", namespaces=NS)
            known = set()
            for element in package.iterfind(".//ar:SHORT-NAME", namespaces=NS):
                path = []
                node = element.getparent()
                while node is not None:
                    name = node.findtext("ar:SHORT-NAME", namespaces=NS)
                    if name is not None:
                        path.insert(0, name)
                    node = node.getparent()
                known.add("/" + "/".join(path))
            refs = [node.text for node in root.iter() if node.get("DEST") is not None]
            self.assertGreater(len(refs), 0)
            for ref in refs:
                with self.subTest(service=model.name, ref=ref):
                    self.assertIn(ref, known)

    def test_method_arxml(self):
        root = etree.fromstring(bridge.render_arxml(timer_model()).encode("utf-8"))
        ids = [node.text for node in root.iterfind(".//ar:METHOD-ID", namespaces=NS)]
        self.assertEqual(ids, ["1", "2"])
        directions = [node.text for node in root.iterfind(".//ar:DIRECTION", namespaces=NS)]
        self.assertEqual(directions, ["OUT", "IN", "IN", "OUT"])
        self.assertIsNone(root.find(".//ar:EVENT-GROUPS", namespaces=NS))

    def test_output_is_deterministic(self):
        first = bridge.render_all(wheel_speed_model())
        second = bridge.render_all(wheel_speed_model())
        self.assertEqual(list(first), list(second))
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            for directory, files in ((first_dir, first), (second_dir, second)):
                bridge.write_files(files, directory)
            for file_name in first:
                with open(os.path.join(first_dir, file_name), "rb") as first_file, \
                        open(os.path.join(second_dir, file_name), "rb") as second_file:
                    content = first_file.read()
                    self.assertEqual(content, second_file.read())
                    self.assertNotIn(b"\r", content)

    def test_committed_example_output_is_up_to_date(self):
        for model in (wheel_speed_model(), timer_model()):
            for file_name, content in bridge.render_all(model).items():
                with self.subTest(file_name=file_name):
                    path = os.path.join(EXAMPLE_DIR, "generated", model.file_stem, file_name)
                    with open(path, "r", encoding="utf-8", newline="") as file:
                        self.assertEqual(file.read(), content)

    def test_file_set(self):
        self.assertEqual(list(bridge.render_all(wheel_speed_model())),
                         ["wheel_speed_sensor_service.arxml", "wheel_speed_sensor_service_types.h",
                          "wheel_speed_sensor_service_common.h", "wheel_speed_sensor_service_skeleton.h",
                          "wheel_speed_sensor_service_proxy.h"])

    def test_event_only_service_has_no_rpc_dependency(self):
        files = bridge.render_all(wheel_speed_model())
        for file_name, content in files.items():
            self.assertNotIn("rpc_server.h", content, file_name)
            self.assertNotIn("rpc_client.h", content, file_name)
        self.assertIn("events::WheelSpeed WheelSpeed;", files["wheel_speed_sensor_service_skeleton.h"])
        self.assertIn("const std::uint16_t cWheelSpeedEventId{0x8001};", files["wheel_speed_sensor_service_common.h"])

    def test_include_prefix(self):
        header = bridge.render_skeleton_header(wheel_speed_model(), "ara")
        self.assertIn('#include "ara/com/helper/network_layer.h"', header)

    def test_snake_case(self):
        self.assertEqual(bridge.to_snake_case("WheelSpeedSensorService"), "wheel_speed_sensor_service")
        self.assertEqual(bridge.to_snake_case("ABSControl"), "abs_control")
        self.assertEqual(bridge.to_snake_case("Timer_Component"), "timer_component")

    def test_invalid_identifiers_are_rejected(self):
        classic = bridge.ClassicModel()
        classic.load_str(SYNTHETIC_ARXML)
        with self.assertRaises(bridge.BridgeError):
            bridge.build_service_model(classic, "TorqueSensor", service_name="class")
        with self.assertRaises(bridge.BridgeError):
            bridge.build_service_model(classic, "TorqueSensor", service_id=0x10000)


if __name__ == '__main__':
    unittest.main()
