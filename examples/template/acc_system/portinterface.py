"""
Port interfaces of the ACC subsystem
"""
# pylint: disable=C0103

import autosar.xml.element as ar_element
import autosar.xml.workspace as ar_workspace
from . import datatype, factory, mode, platform

NAMESPACE = "Default"


def create_acc_calibration_interface(package: ar_element.Package,
                                     workspace: ar_workspace.Workspace,
                                     deps: dict[str, ar_element.ARElement] | None,
                                     **_1) -> ar_element.ClientServerInterface:
    """
    Creates the calibration service interface AccCalibration_I.

    The tester (or a diagnostic component) reads and writes calibration
    parameters of the ACC controller, e.g. controller gains and the minimum
    allowed headway.
    """
    uint8_impl_type = deps[platform.ImplementationTypes.uint8.ref(workspace)]
    uint16_impl_type = deps[platform.ImplementationTypes.uint16.ref(workspace)]
    port_interface = ar_element.ClientServerInterface("AccCalibration_I", is_service=True)
    element_ref = str(package.ref()) + "/" + port_interface.name
    e_not_ok = port_interface.create_possible_error("E_NOT_OK", 1)
    e_out_of_range = port_interface.create_possible_error("E_OUT_OF_RANGE", 2)
    error_refs = [ar_element.ApplicationErrorRef(element_ref + "/" + error.name)
                  for error in (e_not_ok, e_out_of_range)]
    operation = port_interface.create_operation("ReadParameter", possible_error_refs=error_refs)
    operation.create_in_argument("parameterId", type_ref=uint8_impl_type.ref())
    operation.create_out_argument("parameterValue", type_ref=uint16_impl_type.ref())
    operation = port_interface.create_operation("WriteParameter", possible_error_refs=error_refs)
    operation.create_in_argument("parameterId", type_ref=uint8_impl_type.ref())
    operation.create_in_argument("parameterValue", type_ref=uint16_impl_type.ref())
    return port_interface


VehicleSpeed_I = factory.SenderReceiverInterfaceTemplate(
    "VehicleSpeed_I", NAMESPACE,
    [("VehicleSpeed", datatype.VehicleSpeed_T)])

RadarRawTarget_I = factory.SenderReceiverInterfaceTemplate(
    "RadarRawTarget_I", NAMESPACE,
    [("RawDistance", datatype.TargetDistance_T),
     ("RawRelativeSpeed", datatype.RelativeSpeed_T),
     ("RawTargetValid", datatype.RadarTargetValid_T)])

RadarTarget_I = factory.SenderReceiverInterfaceTemplate(
    "RadarTarget_I", NAMESPACE,
    [("TargetDistance", datatype.TargetDistance_T),
     ("TargetRelativeSpeed", datatype.RelativeSpeed_T),
     ("TargetValid", datatype.RadarTargetValid_T)])

AccDriverRequest_I = factory.SenderReceiverInterfaceTemplate(
    "AccDriverRequest_I", NAMESPACE,
    [("SetSpeed", datatype.SetSpeed_T),
     ("TimeGap", datatype.TimeGap_T)])

AccAccelRequest_I = factory.SenderReceiverInterfaceTemplate(
    "AccAccelRequest_I", NAMESPACE,
    [("AccelRequest", datatype.LongitudinalAccel_T)])

EngineTorqueRequest_I = factory.SenderReceiverInterfaceTemplate(
    "EngineTorqueRequest_I", NAMESPACE,
    [("TorqueRequest", datatype.TorqueRequest_T)])

BrakeDecelRequest_I = factory.SenderReceiverInterfaceTemplate(
    "BrakeDecelRequest_I", NAMESPACE,
    [("DecelRequest", datatype.LongitudinalAccel_T)])

AccMode_I = factory.ModeSwitchInterfaceTemplate("AccMode_I", NAMESPACE, mode.AccMode, "accMode")

AccCalibration_I = factory.GenericPortInterfaceTemplate("AccCalibration_I",
                                                        NAMESPACE,
                                                        create_acc_calibration_interface,
                                                        depends=[platform.ImplementationTypes.uint8,
                                                                 platform.ImplementationTypes.uint16])
