"""Unit tests for the WheelSpeed elements of the template example (examples/template/demo_system)"""

# pylint: disable=missing-class-docstring, missing-function-docstring, wrong-import-position, wrong-import-order
import os
import sys
import tempfile
import unittest
from lxml import etree
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
EXAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../examples/template'))
sys.path.insert(0, EXAMPLE_DIR)
import autosar.xml.element as ar_element  # noqa E402
import autosar.xml.enumeration as ar_enum  # noqa E402
import autosar.xml.reader as ar_reader  # noqa E402
import autosar.xml.workspace as ar_workspace  # noqa E402
from demo_system import component, datatype, platform, portinterface  # noqa E402

CONFIG_FILE = os.path.join(EXAMPLE_DIR, "config.toml")
SCHEMA_VERSIONS = (48, 49, 50, 51)
# Directory containing AUTOSAR_000xx.xsd files. The schemas are not part of this repository.
XSD_DIR = os.environ.get("AUTOSAR_XSD_DIR")


def create_workspace(document_root: str | None = None) -> ar_workspace.Workspace:
    workspace = ar_workspace.Workspace(CONFIG_FILE, document_root=document_root)
    for template in (platform.ImplementationTypes.boolean,
                     platform.ImplementationTypes.uint8,
                     platform.ImplementationTypes.uint16,
                     platform.ImplementationTypes.uint32,
                     platform.ImplementationTypes.uint64):
        workspace.apply(template)
    return workspace


class WheelSpeedDataTypeTests(unittest.TestCase):

    def setUp(self):
        self.workspace = create_workspace()
        self.workspace.apply(datatype.WheelSpeed_T)

    def test_implementation_data_type(self):
        elem = self.workspace.find("/DataTypes/ImplementationDataTypes/WheelSpeed_T")
        self.assertIsInstance(elem, ar_element.ImplementationDataType)
        self.assertEqual(elem.category, "VALUE")
        props = elem.sw_data_def_props[0]
        self.assertEqual(str(props.base_type_ref), "/AUTOSAR_Platform/BaseTypes/uint16")
        self.assertEqual(str(props.compu_method_ref), "/DataTypes/CompuMethods/WheelSpeed_T_CompuMethod")
        self.assertEqual(str(props.data_constraint_ref), "/DataTypes/DataConstrs/WheelSpeed_T_DataConstr")

    def test_base_type_is_16_bit(self):
        elem = self.workspace.find("/AUTOSAR_Platform/BaseTypes/uint16")
        self.assertIsInstance(elem, ar_element.SwBaseType)
        self.assertEqual(elem.size, 16)

    def test_compu_method_resolution(self):
        elem = self.workspace.find("/DataTypes/CompuMethods/WheelSpeed_T_CompuMethod")
        self.assertIsInstance(elem, ar_element.CompuMethod)
        self.assertEqual(elem.category, "LINEAR")
        self.assertEqual(str(elem.unit_ref), "/DataTypes/Units/KmPerHour")
        self.assertIsNone(elem.phys_to_int)
        scales = elem.int_to_phys.compu_scales
        self.assertEqual(len(scales), 1)
        self.assertEqual(scales[0].lower_limit, 0)
        self.assertEqual(scales[0].upper_limit, 65535)
        self.assertEqual(list(scales[0].content.numerator), [0, 0.01])
        self.assertEqual(list(scales[0].content.denominator), [1])

    def test_unit(self):
        elem = self.workspace.find("/DataTypes/Units/KmPerHour")
        self.assertIsInstance(elem, ar_element.Unit)
        self.assertEqual(str(elem.display_name), "km/h")

    def test_data_constraint(self):
        elem = self.workspace.find("/DataTypes/DataConstrs/WheelSpeed_T_DataConstr")
        self.assertIsInstance(elem, ar_element.DataConstraint)
        self.assertEqual(len(elem.rules), 1)
        self.assertIsNone(elem.rules[0].physical)
        self.assertEqual(elem.rules[0].internal.lower_limit, 0)
        self.assertEqual(elem.rules[0].internal.upper_limit, 65535)


class WheelSpeedPortInterfaceTests(unittest.TestCase):

    def test_sender_receiver_interface(self):
        workspace = create_workspace()
        workspace.apply(portinterface.WheelSpeed_I)
        elem = workspace.find("/PortInterfaces/WheelSpeed_I")
        self.assertIsInstance(elem, ar_element.SenderReceiverInterface)
        self.assertEqual(len(elem.data_elements), 1)
        data_element = elem.data_elements[0]
        self.assertEqual(data_element.name, "WheelSpeed")
        self.assertEqual(str(data_element.type_ref), "/DataTypes/ImplementationDataTypes/WheelSpeed_T")
        self.assertEqual(data_element.type_ref.dest, ar_enum.IdentifiableSubTypes.IMPLEMENTATION_DATA_TYPE)
        # The data type is created as a dependency of the port interface
        self.assertIsInstance(workspace.find("/DataTypes/ImplementationDataTypes/WheelSpeed_T"),
                              ar_element.ImplementationDataType)


class WheelSpeedSensorComponentTests(unittest.TestCase):

    def setUp(self):
        self.workspace = create_workspace()
        self.workspace.apply(component.WheelSpeedSensor_Implementation)
        self.swc = self.workspace.find("/ComponentTypes/WheelSpeedSensor")

    def test_component_type(self):
        self.assertIsInstance(self.swc, ar_element.ApplicationSoftwareComponentType)

    def test_provide_port(self):
        self.assertEqual(len(self.swc.ports), 1)
        port = self.swc.ports[0]
        self.assertIsInstance(port, ar_element.ProvidePortPrototype)
        self.assertEqual(port.name, "WheelSpeed")
        self.assertEqual(str(port.port_interface_ref), "/PortInterfaces/WheelSpeed_I")
        self.assertEqual(len(port.com_spec), 1)
        com_spec = port.com_spec[0]
        self.assertIsInstance(com_spec, ar_element.NonqueuedSenderComSpec)
        self.assertEqual(str(com_spec.data_element_ref), "/PortInterfaces/WheelSpeed_I/WheelSpeed")
        self.assertEqual(str(com_spec.init_value.constant_ref), "/Constants/WheelSpeed_IV")
        constant = self.workspace.find("/Constants/WheelSpeed_IV")
        self.assertIsInstance(constant, ar_element.ConstantSpecification)
        self.assertEqual(constant.value.value, 0)

    def test_runnable(self):
        behavior = self.swc.internal_behavior
        self.assertEqual(len(behavior.runnables), 1)
        runnable = behavior.runnables[0]
        self.assertEqual(runnable.name, "WheelSpeedSensor_Run")
        self.assertEqual(runnable.symbol, "WheelSpeedSensor_Run")
        self.assertFalse(runnable.can_be_invoked_concurrently)
        self.assertEqual(len(runnable.data_send_point), 1)
        send_point = runnable.data_send_point[0]
        self.assertEqual(send_point.name, "SEND_WheelSpeed_WheelSpeed")
        iref = send_point.accessed_variable.ar_variable_iref
        self.assertEqual(str(iref.port_prototype_ref), "/ComponentTypes/WheelSpeedSensor/WheelSpeed")
        self.assertEqual(str(iref.target_data_prototype_ref), "/PortInterfaces/WheelSpeed_I/WheelSpeed")

    def test_timing_event_10ms(self):
        behavior = self.swc.internal_behavior
        self.assertEqual(len(behavior.events), 1)
        event = behavior.events[0]
        self.assertIsInstance(event, ar_element.TimingEvent)
        self.assertEqual(event.name, "TMT_WheelSpeedSensor_Run")
        self.assertAlmostEqual(event.period, 0.010)
        self.assertEqual(str(event.start_on_event),
                         "/ComponentTypes/WheelSpeedSensor/WheelSpeedSensor_InternalBehavior/WheelSpeedSensor_Run")

    def test_swc_implementation(self):
        elem = self.workspace.find("/ComponentTypes/WheelSpeedSensor_Implementation")
        self.assertIsInstance(elem, ar_element.SwcImplementation)
        self.assertEqual(str(elem.behavior_ref), "/ComponentTypes/WheelSpeedSensor/WheelSpeedSensor_InternalBehavior")


class CompositionTests(unittest.TestCase):

    def setUp(self):
        self.workspace = create_workspace()
        self.workspace.apply(component.CompositionComponent)
        self.swc = self.workspace.find("/ComponentTypes/CompositionComponent")

    def test_wheel_speed_sensor_prototype(self):
        prototypes = {elem.name: str(elem.type_ref) for elem in self.swc.components}
        self.assertEqual(prototypes, {"ReceiverComponent": "/ComponentTypes/ReceiverComponent",
                                      "TimerComponent": "/ComponentTypes/TimerComponent",
                                      "WheelSpeedSensor": "/ComponentTypes/WheelSpeedSensor"})

    def test_wheel_speed_delegation(self):
        ports = {port.name: port for port in self.swc.ports}
        self.assertIsInstance(ports["WheelSpeed"], ar_element.ProvidePortPrototype)
        self.assertEqual(str(ports["WheelSpeed"].port_interface_ref), "/PortInterfaces/WheelSpeed_I")
        connectors = {elem.name: elem for elem in self.swc.connectors}
        connector = connectors["WheelSpeedSensor_WheelSpeed_WheelSpeed"]
        self.assertIsInstance(connector, ar_element.DelegationSwConnector)
        self.assertEqual(str(connector.inner_port.component_ref),
                         "/ComponentTypes/CompositionComponent/WheelSpeedSensor")
        self.assertEqual(str(connector.inner_port.port_ref),
                         "/ComponentTypes/WheelSpeedSensor/WheelSpeed")
        self.assertEqual(str(connector.outer_port), "/ComponentTypes/CompositionComponent/WheelSpeed")


class GeneratedDocumentTests(unittest.TestCase):

    def _write_documents(self, document_root: str, schema_version: int) -> list[str]:
        workspace = create_workspace(document_root)
        workspace.apply(component.CompositionComponent)
        workspace.write_documents(schema_version)
        return sorted(os.path.join(document_root, name) for name in os.listdir(document_root))

    def test_checked_in_documents_are_up_to_date(self):
        generated_dir = os.path.join(EXAMPLE_DIR, "generated")
        with tempfile.TemporaryDirectory() as document_root:
            file_paths = self._write_documents(document_root, 51)
            self.assertIn("WheelSpeedSensor.arxml", [os.path.basename(path) for path in file_paths])
            self.assertEqual(sorted(os.listdir(generated_dir)), [os.path.basename(path) for path in file_paths])
            for file_path in file_paths:
                with open(file_path, encoding="utf-8") as actual:
                    with open(os.path.join(generated_dir, os.path.basename(file_path)), encoding="utf-8") as expected:
                        self.assertEqual(actual.read(), expected.read(), os.path.basename(file_path))

    def test_read_back_wheel_speed_sensor(self):
        for schema_version in SCHEMA_VERSIONS:
            with self.subTest(schema_version=schema_version):
                with tempfile.TemporaryDirectory() as document_root:
                    self._write_documents(document_root, schema_version)
                    reader = ar_reader.Reader()
                    document = reader.read_file(os.path.join(document_root, "WheelSpeedSensor.arxml"))
                    self.assertEqual(document.schema_version, schema_version)
                    swc = document.find("/ComponentTypes/WheelSpeedSensor")
                    self.assertIsInstance(swc, ar_element.ApplicationSoftwareComponentType)
                    self.assertEqual(swc.ports[0].name, "WheelSpeed")
                    self.assertAlmostEqual(swc.internal_behavior.events[0].period, 0.010)

    @unittest.skipIf(XSD_DIR is None, "AUTOSAR_XSD_DIR not set (AUTOSAR XSD files are not part of this repository)")
    def test_xsd_validation(self):
        for schema_version in SCHEMA_VERSIONS:
            with self.subTest(schema_version=schema_version):
                schema = etree.XMLSchema(etree.parse(os.path.join(XSD_DIR, f"AUTOSAR_{schema_version:05d}.xsd")))
                with tempfile.TemporaryDirectory() as document_root:
                    for file_path in self._write_documents(document_root, schema_version):
                        valid = schema.validate(etree.parse(file_path))
                        self.assertTrue(valid, f"{os.path.basename(file_path)}: {schema.error_log}")


if __name__ == '__main__':
    unittest.main()
