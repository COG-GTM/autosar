"""
Component type templates of the ACC subsystem.

Decomposition:

    RadarRawTarget ->| RadarPreProcessing |-> RadarTarget ->| AccController |
                                                                    |
                                          AccelRequest + AccMode ---+
                                                                    v
                                                          | ActuatorArbitration | -> EngineTorqueRequest
                                                                                  -> BrakeDecelRequest
"""
# pylint: disable=C0103

import autosar.xml.element as ar_element
import autosar.xml.enumeration as ar_enum
import autosar.xml.workspace as ar_workspace
from . import constants, datatype, factory, portinterface

NAMESPACE = "Default"

RADAR_CYCLE_TIME = 40.0 / 1000
CONTROL_CYCLE_TIME = 20.0 / 1000
ACTUATOR_CYCLE_TIME = 10.0 / 1000


def create_RadarPreProcessing(package: ar_element.Package,
                              workspace: ar_workspace.Workspace,
                              deps: dict[str, ar_element.ARElement] | None,
                              **_1) -> ar_element.ApplicationSoftwareComponentType:
    """
    Radar pre-processing SWC.

    Filters and plausibility-checks the raw radar detections and publishes a
    single tracked target to the ACC controller.
    """
    raw_target_interface = deps[portinterface.RadarRawTarget_I.ref(workspace)]
    target_interface = deps[portinterface.RadarTarget_I.ref(workspace)]
    vehicle_speed_interface = deps[portinterface.VehicleSpeed_I.ref(workspace)]
    mapping_set = deps[datatype.AccTypeMappingSet.ref(workspace)]
    distance_init = deps[constants.TargetDistance_IV.ref(workspace)]
    relative_speed_init = deps[constants.RelativeSpeed_IV.ref(workspace)]
    target_valid_init = deps[constants.RadarTargetValid_IV.ref(workspace)]
    vehicle_speed_init = deps[constants.VehicleSpeed_IV.ref(workspace)]
    swc = ar_element.ApplicationSoftwareComponentType("RadarPreProcessing")
    package.append(swc)
    swc.create_require_port("RadarRawTarget", raw_target_interface,
                            com_spec={"RawDistance": {"init_value": distance_init.ref(),
                                                      "alive_timeout": 3 * RADAR_CYCLE_TIME,
                                                      "handle_never_received": True},
                                      "RawRelativeSpeed": {"init_value": relative_speed_init.ref(),
                                                           "alive_timeout": 3 * RADAR_CYCLE_TIME,
                                                           "handle_never_received": True},
                                      "RawTargetValid": {"init_value": target_valid_init.ref(),
                                                         "alive_timeout": 3 * RADAR_CYCLE_TIME,
                                                         "handle_never_received": True}})
    swc.create_require_port("VehicleSpeed", vehicle_speed_interface,
                            com_spec={"init_value": vehicle_speed_init.ref(),
                                      "alive_timeout": 0,
                                      "handle_never_received": False})
    swc.create_provide_port("RadarTarget", target_interface,
                            com_spec={"TargetDistance": {"init_value": distance_init.ref()},
                                      "TargetRelativeSpeed": {"init_value": relative_speed_init.ref()},
                                      "TargetValid": {"init_value": target_valid_init.ref()}})
    behavior = swc.create_internal_behavior(data_type_mappings=mapping_set.ref())
    behavior.create_port_api_options("*", enable_take_address=False, indirect_api=False)
    init_runnable_name = swc.name + "_Init"
    periodic_runnable_name = swc.name + "_Run"
    behavior.create_runnable(init_runnable_name, can_be_invoked_concurrently=False, minimum_start_interval=0)
    runnable = behavior.create_runnable(periodic_runnable_name,
                                        can_be_invoked_concurrently=False, minimum_start_interval=0)
    runnable.create_port_access(["RadarRawTarget/RawDistance",
                                 "RadarRawTarget/RawRelativeSpeed",
                                 "RadarRawTarget/RawTargetValid",
                                 "VehicleSpeed/VehicleSpeed",
                                 "RadarTarget/TargetDistance",
                                 "RadarTarget/TargetRelativeSpeed",
                                 "RadarTarget/TargetValid"])
    behavior.create_init_event(init_runnable_name)
    behavior.create_timing_event(periodic_runnable_name, RADAR_CYCLE_TIME)
    return swc


def create_AccController(package: ar_element.Package,
                         workspace: ar_workspace.Workspace,
                         deps: dict[str, ar_element.ARElement] | None,
                         **_1) -> ar_element.ApplicationSoftwareComponentType:
    """
    ACC controller SWC.

    Runs the speed and distance control laws, owns the ACC state machine and
    offers a calibration service to the tester.
    """
    target_interface = deps[portinterface.RadarTarget_I.ref(workspace)]
    vehicle_speed_interface = deps[portinterface.VehicleSpeed_I.ref(workspace)]
    driver_request_interface = deps[portinterface.AccDriverRequest_I.ref(workspace)]
    accel_request_interface = deps[portinterface.AccAccelRequest_I.ref(workspace)]
    mode_interface = deps[portinterface.AccMode_I.ref(workspace)]
    calibration_interface = deps[portinterface.AccCalibration_I.ref(workspace)]
    mapping_set = deps[datatype.AccTypeMappingSet.ref(workspace)]
    distance_init = deps[constants.TargetDistance_IV.ref(workspace)]
    relative_speed_init = deps[constants.RelativeSpeed_IV.ref(workspace)]
    target_valid_init = deps[constants.RadarTargetValid_IV.ref(workspace)]
    vehicle_speed_init = deps[constants.VehicleSpeed_IV.ref(workspace)]
    set_speed_init = deps[constants.SetSpeed_IV.ref(workspace)]
    time_gap_init = deps[constants.TimeGap_IV.ref(workspace)]
    accel_init = deps[constants.LongitudinalAccel_IV.ref(workspace)]
    swc = ar_element.ApplicationSoftwareComponentType("AccController")
    package.append(swc)
    swc.create_require_port("RadarTarget", target_interface,
                            com_spec={"TargetDistance": {"init_value": distance_init.ref(),
                                                         "alive_timeout": 3 * RADAR_CYCLE_TIME,
                                                         "handle_never_received": True},
                                      "TargetRelativeSpeed": {"init_value": relative_speed_init.ref(),
                                                              "alive_timeout": 3 * RADAR_CYCLE_TIME,
                                                              "handle_never_received": True},
                                      "TargetValid": {"init_value": target_valid_init.ref(),
                                                      "alive_timeout": 3 * RADAR_CYCLE_TIME,
                                                      "handle_never_received": True}})
    swc.create_require_port("VehicleSpeed", vehicle_speed_interface,
                            com_spec={"init_value": vehicle_speed_init.ref(),
                                      "alive_timeout": 0,
                                      "handle_never_received": False})
    swc.create_require_port("DriverRequest", driver_request_interface,
                            com_spec={"SetSpeed": {"init_value": set_speed_init.ref()},
                                      "TimeGap": {"init_value": time_gap_init.ref()}})
    swc.create_provide_port("AccelRequest", accel_request_interface,
                            com_spec={"init_value": accel_init.ref()})
    swc.create_provide_port("AccMode", mode_interface, com_spec={"enhanced_mode_api": False,
                                                                 "queue_length": 1})
    swc.create_provide_port("AccCalibration", calibration_interface,
                            com_spec={"ReadParameter": {"queue_length": 1},
                                      "WriteParameter": {"queue_length": 1}})
    behavior = swc.create_internal_behavior(data_type_mappings=mapping_set.ref())
    behavior.create_port_api_options("*", enable_take_address=False, indirect_api=False)
    init_runnable_name = swc.name + "_Init"
    control_runnable_name = swc.name + "_Run"
    target_runnable_name = swc.name + "_OnTargetUpdate"
    read_runnable_name = swc.name + "_ReadParameter"
    write_runnable_name = swc.name + "_WriteParameter"
    behavior.create_runnable(init_runnable_name, can_be_invoked_concurrently=False, minimum_start_interval=0)
    runnable = behavior.create_runnable(control_runnable_name,
                                        can_be_invoked_concurrently=False, minimum_start_interval=0)
    runnable.create_port_access(["RadarTarget/TargetDistance",
                                 "RadarTarget/TargetRelativeSpeed",
                                 "RadarTarget/TargetValid",
                                 "VehicleSpeed/VehicleSpeed",
                                 "DriverRequest/SetSpeed",
                                 "DriverRequest/TimeGap",
                                 "AccelRequest/AccelRequest"])
    runnable = behavior.create_runnable(target_runnable_name,
                                        can_be_invoked_concurrently=False, minimum_start_interval=0)
    runnable.create_port_access(["RadarTarget/TargetDistance",
                                 "RadarTarget/TargetValid"])
    behavior.create_runnable(read_runnable_name, can_be_invoked_concurrently=False, minimum_start_interval=0)
    behavior.create_runnable(write_runnable_name, can_be_invoked_concurrently=False, minimum_start_interval=0)
    behavior.create_init_event(init_runnable_name)
    behavior.create_timing_event(control_runnable_name, CONTROL_CYCLE_TIME)
    behavior.create_data_received_event(target_runnable_name, "RadarTarget/TargetDistance")
    behavior.create_operation_invoked_event(read_runnable_name, "AccCalibration/ReadParameter")
    behavior.create_operation_invoked_event(write_runnable_name, "AccCalibration/WriteParameter")
    return swc


def create_ActuatorArbitration(package: ar_element.Package,
                               workspace: ar_workspace.Workspace,
                               deps: dict[str, ar_element.ARElement] | None,
                               **_1) -> ar_element.ApplicationSoftwareComponentType:
    """
    Actuator arbitration SWC.

    Splits the requested longitudinal acceleration into a positive torque
    request for the engine and a deceleration request for the brake system.
    """
    accel_request_interface = deps[portinterface.AccAccelRequest_I.ref(workspace)]
    vehicle_speed_interface = deps[portinterface.VehicleSpeed_I.ref(workspace)]
    mode_interface = deps[portinterface.AccMode_I.ref(workspace)]
    torque_interface = deps[portinterface.EngineTorqueRequest_I.ref(workspace)]
    brake_interface = deps[portinterface.BrakeDecelRequest_I.ref(workspace)]
    mapping_set = deps[datatype.AccTypeMappingSet.ref(workspace)]
    accel_init = deps[constants.LongitudinalAccel_IV.ref(workspace)]
    torque_init = deps[constants.TorqueRequest_IV.ref(workspace)]
    vehicle_speed_init = deps[constants.VehicleSpeed_IV.ref(workspace)]
    swc = ar_element.ApplicationSoftwareComponentType("ActuatorArbitration")
    package.append(swc)
    swc.create_require_port("AccelRequest", accel_request_interface,
                            com_spec={"init_value": accel_init.ref(),
                                      "alive_timeout": 3 * CONTROL_CYCLE_TIME,
                                      "handle_never_received": True})
    swc.create_require_port("VehicleSpeed", vehicle_speed_interface,
                            com_spec={"init_value": vehicle_speed_init.ref(),
                                      "alive_timeout": 0,
                                      "handle_never_received": False})
    swc.create_require_port("AccMode", mode_interface, com_spec={"enhanced_mode_api": False,
                                                                 "supports_async": False})
    swc.create_provide_port("EngineTorqueRequest", torque_interface,
                            com_spec={"init_value": torque_init.ref()})
    swc.create_provide_port("BrakeDecelRequest", brake_interface,
                            com_spec={"init_value": accel_init.ref()})
    behavior = swc.create_internal_behavior(data_type_mappings=mapping_set.ref())
    behavior.create_port_api_options("*", enable_take_address=False, indirect_api=False)
    init_runnable_name = swc.name + "_Init"
    periodic_runnable_name = swc.name + "_Run"
    accel_runnable_name = swc.name + "_OnAccelRequest"
    mode_runnable_name = swc.name + "_OnAccActivated"
    behavior.create_runnable(init_runnable_name, can_be_invoked_concurrently=False, minimum_start_interval=0)
    runnable = behavior.create_runnable(periodic_runnable_name,
                                        can_be_invoked_concurrently=False, minimum_start_interval=0)
    runnable.create_port_access(["AccelRequest/AccelRequest",
                                 "VehicleSpeed/VehicleSpeed",
                                 "EngineTorqueRequest/TorqueRequest",
                                 "BrakeDecelRequest/DecelRequest"])
    runnable = behavior.create_runnable(accel_runnable_name,
                                        can_be_invoked_concurrently=False, minimum_start_interval=0)
    runnable.create_port_access(["AccelRequest/AccelRequest"])
    behavior.create_runnable(mode_runnable_name, can_be_invoked_concurrently=False, minimum_start_interval=0)
    behavior.create_init_event(init_runnable_name)
    behavior.create_timing_event(periodic_runnable_name, ACTUATOR_CYCLE_TIME)
    behavior.create_data_received_event(accel_runnable_name, "AccelRequest/AccelRequest")
    behavior.create_swc_mode_mode_switch_event(mode_runnable_name,
                                               "AccMode/ACTIVE",
                                               ar_enum.ModeActivationKind.ON_ENTRY)
    return swc


def create_AccComposition(package: ar_element.Package,
                          workspace: ar_workspace.Workspace,
                          deps: dict[str, ar_element.ARElement] | None,
                          **_1) -> ar_element.CompositionSwComponentType:
    """
    Composition of the ACC subsystem.

    The composition owns the outer (ECU-level) ports and wires the three
    atomic components using assembly and delegation connectors.
    """
    raw_target_interface = deps[portinterface.RadarRawTarget_I.ref(workspace)]
    vehicle_speed_interface = deps[portinterface.VehicleSpeed_I.ref(workspace)]
    driver_request_interface = deps[portinterface.AccDriverRequest_I.ref(workspace)]
    torque_interface = deps[portinterface.EngineTorqueRequest_I.ref(workspace)]
    brake_interface = deps[portinterface.BrakeDecelRequest_I.ref(workspace)]
    calibration_interface = deps[portinterface.AccCalibration_I.ref(workspace)]
    mode_interface = deps[portinterface.AccMode_I.ref(workspace)]
    distance_init = deps[constants.TargetDistance_IV.ref(workspace)]
    relative_speed_init = deps[constants.RelativeSpeed_IV.ref(workspace)]
    target_valid_init = deps[constants.RadarTargetValid_IV.ref(workspace)]
    vehicle_speed_init = deps[constants.VehicleSpeed_IV.ref(workspace)]
    set_speed_init = deps[constants.SetSpeed_IV.ref(workspace)]
    time_gap_init = deps[constants.TimeGap_IV.ref(workspace)]
    accel_init = deps[constants.LongitudinalAccel_IV.ref(workspace)]
    torque_init = deps[constants.TorqueRequest_IV.ref(workspace)]
    radar_component = workspace.find(RadarPreProcessing.ref(workspace))
    controller_component = workspace.find(AccController.ref(workspace))
    actuator_component = workspace.find(ActuatorArbitration.ref(workspace))
    swc = ar_element.CompositionSwComponentType("AccComposition")
    package.append(swc)
    swc.create_require_port("RadarRawTarget", raw_target_interface,
                            com_spec={"RawDistance": {"init_value": distance_init.ref()},
                                      "RawRelativeSpeed": {"init_value": relative_speed_init.ref()},
                                      "RawTargetValid": {"init_value": target_valid_init.ref()}})
    swc.create_require_port("VehicleSpeed", vehicle_speed_interface,
                            com_spec={"init_value": vehicle_speed_init.ref()})
    swc.create_require_port("DriverRequest", driver_request_interface,
                            com_spec={"SetSpeed": {"init_value": set_speed_init.ref()},
                                      "TimeGap": {"init_value": time_gap_init.ref()}})
    swc.create_provide_port("EngineTorqueRequest", torque_interface,
                            com_spec={"init_value": torque_init.ref()})
    swc.create_provide_port("BrakeDecelRequest", brake_interface,
                            com_spec={"init_value": accel_init.ref()})
    swc.create_provide_port("AccMode", mode_interface, com_spec={"enhanced_mode_api": False,
                                                                 "queue_length": 1})
    swc.create_provide_port("AccCalibration", calibration_interface,
                            com_spec={"ReadParameter": {"queue_length": 1},
                                      "WriteParameter": {"queue_length": 1}})
    swc.create_component_prototype(radar_component)
    swc.create_component_prototype(controller_component)
    swc.create_component_prototype(actuator_component)
    # Assembly connectors
    swc.create_connector("RadarPreProcessing/RadarTarget", "AccController/RadarTarget", workspace)
    swc.create_connector("AccController/AccelRequest", "ActuatorArbitration/AccelRequest", workspace)
    swc.create_connector("AccController/AccMode", "ActuatorArbitration/AccMode", workspace)
    # Delegation connectors
    swc.create_connector("RadarRawTarget", "RadarPreProcessing/RadarRawTarget", workspace)
    swc.create_connector("VehicleSpeed", "RadarPreProcessing/VehicleSpeed", workspace)
    swc.create_connector("VehicleSpeed", "AccController/VehicleSpeed", workspace)
    swc.create_connector("VehicleSpeed", "ActuatorArbitration/VehicleSpeed", workspace)
    swc.create_connector("DriverRequest", "AccController/DriverRequest", workspace)
    swc.create_connector("AccCalibration", "AccController/AccCalibration", workspace)
    swc.create_connector("AccMode", "AccController/AccMode", workspace)
    swc.create_connector("EngineTorqueRequest", "ActuatorArbitration/EngineTorqueRequest", workspace)
    swc.create_connector("BrakeDecelRequest", "ActuatorArbitration/BrakeDecelRequest", workspace)
    return swc


RadarPreProcessing = factory.GenericComponentTypeTemplate("RadarPreProcessing",
                                                          NAMESPACE,
                                                          create_RadarPreProcessing,
                                                          depends=[portinterface.RadarRawTarget_I,
                                                                   portinterface.RadarTarget_I,
                                                                   portinterface.VehicleSpeed_I,
                                                                   datatype.AccTypeMappingSet,
                                                                   constants.TargetDistance_IV,
                                                                   constants.RelativeSpeed_IV,
                                                                   constants.RadarTargetValid_IV,
                                                                   constants.VehicleSpeed_IV])
RadarPreProcessing_Implementation = factory.SwcImplementationTemplate("RadarPreProcessing_Implementation",
                                                                      NAMESPACE,
                                                                      component_type=RadarPreProcessing)
AccController = factory.GenericComponentTypeTemplate("AccController",
                                                     NAMESPACE,
                                                     create_AccController,
                                                     depends=[portinterface.RadarTarget_I,
                                                              portinterface.VehicleSpeed_I,
                                                              portinterface.AccDriverRequest_I,
                                                              portinterface.AccAccelRequest_I,
                                                              portinterface.AccMode_I,
                                                              portinterface.AccCalibration_I,
                                                              datatype.AccTypeMappingSet,
                                                              constants.TargetDistance_IV,
                                                              constants.RelativeSpeed_IV,
                                                              constants.RadarTargetValid_IV,
                                                              constants.VehicleSpeed_IV,
                                                              constants.SetSpeed_IV,
                                                              constants.TimeGap_IV,
                                                              constants.LongitudinalAccel_IV])
AccController_Implementation = factory.SwcImplementationTemplate("AccController_Implementation",
                                                                 NAMESPACE,
                                                                 component_type=AccController)
ActuatorArbitration = factory.GenericComponentTypeTemplate("ActuatorArbitration",
                                                           NAMESPACE,
                                                           create_ActuatorArbitration,
                                                           depends=[portinterface.AccAccelRequest_I,
                                                                    portinterface.VehicleSpeed_I,
                                                                    portinterface.AccMode_I,
                                                                    portinterface.EngineTorqueRequest_I,
                                                                    portinterface.BrakeDecelRequest_I,
                                                                    datatype.AccTypeMappingSet,
                                                                    constants.LongitudinalAccel_IV,
                                                                    constants.TorqueRequest_IV,
                                                                    constants.VehicleSpeed_IV])
ActuatorArbitration_Implementation = factory.SwcImplementationTemplate("ActuatorArbitration_Implementation",
                                                                       NAMESPACE,
                                                                       component_type=ActuatorArbitration)
AccComposition = factory.GenericComponentTypeTemplate("AccComposition",
                                                      NAMESPACE,
                                                      create_AccComposition,
                                                      depends=[portinterface.RadarRawTarget_I,
                                                               portinterface.VehicleSpeed_I,
                                                               portinterface.AccDriverRequest_I,
                                                               portinterface.EngineTorqueRequest_I,
                                                               portinterface.BrakeDecelRequest_I,
                                                               portinterface.AccCalibration_I,
                                                               portinterface.AccMode_I,
                                                               constants.TargetDistance_IV,
                                                               constants.RelativeSpeed_IV,
                                                               constants.RadarTargetValid_IV,
                                                               constants.VehicleSpeed_IV,
                                                               constants.SetSpeed_IV,
                                                               constants.TimeGap_IV,
                                                               constants.LongitudinalAccel_IV,
                                                               constants.TorqueRequest_IV,
                                                               RadarPreProcessing_Implementation,
                                                               AccController_Implementation,
                                                               ActuatorArbitration_Implementation])
