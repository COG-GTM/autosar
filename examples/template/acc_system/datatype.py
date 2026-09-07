"""
Data types for the ACC subsystem.

Each signal is defined twice:

* An application data type carrying the physical semantics
  (unit, resolution, physical range).
* An implementation data type carrying the in-memory representation
  (base type, internal range).

The two are paired in a data type mapping set which every SWC references from
its internal behavior. Physical value and internal value are related by:

    physical_value = offset + factor * internal_value
"""
# pylint: disable=C0103

from . import factory, platform

NAMESPACE = "Default"


class Units:
    """
    Physical units used by the ACC subsystem
    """

    KmPerHour = factory.UnitTemplate("KmPerHour", NAMESPACE, "km/h")
    Meter = factory.UnitTemplate("Meter", NAMESPACE, "m")
    MeterPerSecond = factory.UnitTemplate("MeterPerSecond", NAMESPACE, "m/s")
    MeterPerSecondSquared = factory.UnitTemplate("MeterPerSecondSquared", NAMESPACE, "m/s^2")
    NewtonMeter = factory.UnitTemplate("NewtonMeter", NAMESPACE, "Nm")
    Second = factory.UnitTemplate("Second", NAMESPACE, "s")


# Vehicle speed: uint16, resolution 1/64 km/h, 0 .. 1023.984375 km/h

VehicleSpeed_CompuMethod = factory.CompuMethodLinearTemplate("VehicleSpeed_T_CompuMethod", NAMESPACE,
                                                             factor=1 / 64,
                                                             offset=0,
                                                             lower_limit=0,
                                                             upper_limit=65535,
                                                             unit=Units.KmPerHour,
                                                             desc="Vehicle speed, resolution 1/64 km/h")
VehicleSpeed_DataConstr = factory.DataConstraintInternalTemplate("VehicleSpeed_T_DataConstr", NAMESPACE, 0, 65535)
VehicleSpeed_PhysConstr = factory.DataConstraintPhysicalTemplate("VehicleSpeed_T_PhysConstr", NAMESPACE,
                                                                 0, 1023.984375, Units.KmPerHour)
VehicleSpeed_T = factory.ApplicationValueTypeTemplate("VehicleSpeed_T", NAMESPACE,
                                                      VehicleSpeed_CompuMethod,
                                                      VehicleSpeed_PhysConstr,
                                                      Units.KmPerHour,
                                                      desc="Vehicle longitudinal speed")
VehicleSpeed_ImplType = factory.ImplementationValueTypeTemplate("VehicleSpeed_T", NAMESPACE,
                                                                platform.BaseTypes.uint16,
                                                                VehicleSpeed_DataConstr,
                                                                VehicleSpeed_CompuMethod)

# Driver set speed: uint8, resolution 1 km/h, 0 .. 255 km/h

SetSpeed_CompuMethod = factory.CompuMethodLinearTemplate("SetSpeed_T_CompuMethod", NAMESPACE,
                                                         factor=1,
                                                         offset=0,
                                                         lower_limit=0,
                                                         upper_limit=255,
                                                         unit=Units.KmPerHour,
                                                         desc="Driver selected speed, resolution 1 km/h")
SetSpeed_DataConstr = factory.DataConstraintInternalTemplate("SetSpeed_T_DataConstr", NAMESPACE, 0, 255)
SetSpeed_PhysConstr = factory.DataConstraintPhysicalTemplate("SetSpeed_T_PhysConstr", NAMESPACE,
                                                             0, 255, Units.KmPerHour)
SetSpeed_T = factory.ApplicationValueTypeTemplate("SetSpeed_T", NAMESPACE,
                                                  SetSpeed_CompuMethod,
                                                  SetSpeed_PhysConstr,
                                                  Units.KmPerHour,
                                                  desc="Driver selected cruise speed")
SetSpeed_ImplType = factory.ImplementationValueTypeTemplate("SetSpeed_T", NAMESPACE,
                                                            platform.BaseTypes.uint8,
                                                            SetSpeed_DataConstr,
                                                            SetSpeed_CompuMethod)

# Target distance: uint16, resolution 0.05 m, 0 .. 250 m

TargetDistance_CompuMethod = factory.CompuMethodLinearTemplate("TargetDistance_T_CompuMethod", NAMESPACE,
                                                               factor=0.05,
                                                               offset=0,
                                                               lower_limit=0,
                                                               upper_limit=5000,
                                                               unit=Units.Meter,
                                                               desc="Distance to target, resolution 0.05 m")
TargetDistance_DataConstr = factory.DataConstraintInternalTemplate("TargetDistance_T_DataConstr", NAMESPACE, 0, 5000)
TargetDistance_PhysConstr = factory.DataConstraintPhysicalTemplate("TargetDistance_T_PhysConstr", NAMESPACE,
                                                                   0, 250, Units.Meter)
TargetDistance_T = factory.ApplicationValueTypeTemplate("TargetDistance_T", NAMESPACE,
                                                        TargetDistance_CompuMethod,
                                                        TargetDistance_PhysConstr,
                                                        Units.Meter,
                                                        desc="Longitudinal distance to the tracked target")
TargetDistance_ImplType = factory.ImplementationValueTypeTemplate("TargetDistance_T", NAMESPACE,
                                                                  platform.BaseTypes.uint16,
                                                                  TargetDistance_DataConstr,
                                                                  TargetDistance_CompuMethod)

# Relative speed: sint16, resolution 0.01 m/s, -128 .. +128 m/s (closing speed is negative)

RelativeSpeed_CompuMethod = factory.CompuMethodLinearTemplate("RelativeSpeed_T_CompuMethod", NAMESPACE,
                                                              factor=0.01,
                                                              offset=0,
                                                              lower_limit=-12800,
                                                              upper_limit=12800,
                                                              unit=Units.MeterPerSecond,
                                                              desc="Relative speed, resolution 0.01 m/s")
RelativeSpeed_DataConstr = factory.DataConstraintInternalTemplate("RelativeSpeed_T_DataConstr", NAMESPACE,
                                                                  -12800, 12800)
RelativeSpeed_PhysConstr = factory.DataConstraintPhysicalTemplate("RelativeSpeed_T_PhysConstr", NAMESPACE,
                                                                  -128, 128, Units.MeterPerSecond)
RelativeSpeed_T = factory.ApplicationValueTypeTemplate("RelativeSpeed_T", NAMESPACE,
                                                       RelativeSpeed_CompuMethod,
                                                       RelativeSpeed_PhysConstr,
                                                       Units.MeterPerSecond,
                                                       desc="Target speed relative to ego vehicle")
RelativeSpeed_ImplType = factory.ImplementationValueTypeTemplate("RelativeSpeed_T", NAMESPACE,
                                                                 platform.BaseTypes.sint16,
                                                                 RelativeSpeed_DataConstr,
                                                                 RelativeSpeed_CompuMethod)

# Longitudinal acceleration: sint16, resolution 0.001 m/s2, -10 .. +5 m/s2

LongitudinalAccel_CompuMethod = factory.CompuMethodLinearTemplate("LongitudinalAccel_T_CompuMethod", NAMESPACE,
                                                                  factor=0.001,
                                                                  offset=0,
                                                                  lower_limit=-10000,
                                                                  upper_limit=5000,
                                                                  unit=Units.MeterPerSecondSquared,
                                                                  desc="Acceleration, resolution 0.001 m/s^2")
LongitudinalAccel_DataConstr = factory.DataConstraintInternalTemplate("LongitudinalAccel_T_DataConstr", NAMESPACE,
                                                                      -10000, 5000)
LongitudinalAccel_PhysConstr = factory.DataConstraintPhysicalTemplate("LongitudinalAccel_T_PhysConstr", NAMESPACE,
                                                                      -10, 5, Units.MeterPerSecondSquared)
LongitudinalAccel_T = factory.ApplicationValueTypeTemplate("LongitudinalAccel_T", NAMESPACE,
                                                           LongitudinalAccel_CompuMethod,
                                                           LongitudinalAccel_PhysConstr,
                                                           Units.MeterPerSecondSquared,
                                                           desc="Longitudinal acceleration request or measurement")
LongitudinalAccel_ImplType = factory.ImplementationValueTypeTemplate("LongitudinalAccel_T", NAMESPACE,
                                                                     platform.BaseTypes.sint16,
                                                                     LongitudinalAccel_DataConstr,
                                                                     LongitudinalAccel_CompuMethod)

# Torque request: sint16, resolution 0.5 Nm, -1000 .. +1000 Nm

TorqueRequest_CompuMethod = factory.CompuMethodLinearTemplate("TorqueRequest_T_CompuMethod", NAMESPACE,
                                                              factor=0.5,
                                                              offset=0,
                                                              lower_limit=-2000,
                                                              upper_limit=2000,
                                                              unit=Units.NewtonMeter,
                                                              desc="Torque request, resolution 0.5 Nm")
TorqueRequest_DataConstr = factory.DataConstraintInternalTemplate("TorqueRequest_T_DataConstr", NAMESPACE, -2000, 2000)
TorqueRequest_PhysConstr = factory.DataConstraintPhysicalTemplate("TorqueRequest_T_PhysConstr", NAMESPACE,
                                                                  -1000, 1000, Units.NewtonMeter)
TorqueRequest_T = factory.ApplicationValueTypeTemplate("TorqueRequest_T", NAMESPACE,
                                                       TorqueRequest_CompuMethod,
                                                       TorqueRequest_PhysConstr,
                                                       Units.NewtonMeter,
                                                       desc="Requested engine torque at the crankshaft")
TorqueRequest_ImplType = factory.ImplementationValueTypeTemplate("TorqueRequest_T", NAMESPACE,
                                                                 platform.BaseTypes.sint16,
                                                                 TorqueRequest_DataConstr,
                                                                 TorqueRequest_CompuMethod)

# Time gap: uint8, resolution 0.1 s, 0.8 .. 2.5 s

TimeGap_CompuMethod = factory.CompuMethodLinearTemplate("TimeGap_T_CompuMethod", NAMESPACE,
                                                        factor=0.1,
                                                        offset=0,
                                                        lower_limit=8,
                                                        upper_limit=25,
                                                        unit=Units.Second,
                                                        desc="Headway time gap, resolution 0.1 s")
TimeGap_DataConstr = factory.DataConstraintInternalTemplate("TimeGap_T_DataConstr", NAMESPACE, 8, 25)
TimeGap_PhysConstr = factory.DataConstraintPhysicalTemplate("TimeGap_T_PhysConstr", NAMESPACE,
                                                            0.8, 2.5, Units.Second)
TimeGap_T = factory.ApplicationValueTypeTemplate("TimeGap_T", NAMESPACE,
                                                 TimeGap_CompuMethod,
                                                 TimeGap_PhysConstr,
                                                 Units.Second,
                                                 desc="Driver selected headway time gap")
TimeGap_ImplType = factory.ImplementationValueTypeTemplate("TimeGap_T", NAMESPACE,
                                                           platform.BaseTypes.uint8,
                                                           TimeGap_DataConstr,
                                                           TimeGap_CompuMethod)

# Radar target validity: uint8 text-table

RadarTargetValid_CompuMethod = factory.CompuMethodEnumTemplate("RadarTargetValid_T_CompuMethod", NAMESPACE,
                                                               ["RadarTargetValid_NotValid",
                                                                "RadarTargetValid_Valid"],
                                                               auto_label=False)
RadarTargetValid_DataConstr = factory.DataConstraintInternalTemplate("RadarTargetValid_T_DataConstr", NAMESPACE, 0, 1)
RadarTargetValid_T = factory.ApplicationValueTypeTemplate("RadarTargetValid_T", NAMESPACE,
                                                          RadarTargetValid_CompuMethod,
                                                          RadarTargetValid_DataConstr,
                                                          desc="Plausibility status of the radar target")
RadarTargetValid_ImplType = factory.ImplementationValueTypeTemplate("RadarTargetValid_T", NAMESPACE,
                                                                    platform.BaseTypes.uint8,
                                                                    RadarTargetValid_DataConstr,
                                                                    RadarTargetValid_CompuMethod)

# ACC mode: uint8 text-table

AccMode_CompuMethod = factory.CompuMethodEnumTemplate("AccMode_T_CompuMethod", NAMESPACE,
                                                      ["AccMode_Off",
                                                       "AccMode_Standby",
                                                       "AccMode_Active",
                                                       "AccMode_Override"],
                                                      auto_label=False)
AccMode_DataConstr = factory.DataConstraintInternalTemplate("AccMode_T_DataConstr", NAMESPACE, 0, 3)
AccMode_T = factory.ApplicationValueTypeTemplate("AccMode_T", NAMESPACE,
                                                 AccMode_CompuMethod,
                                                 AccMode_DataConstr,
                                                 desc="Operating mode of the ACC function")
AccMode_ImplType = factory.ImplementationValueTypeTemplate("AccMode_T", NAMESPACE,
                                                           platform.BaseTypes.uint8,
                                                           AccMode_DataConstr,
                                                           AccMode_CompuMethod)

AccTypeMappingSet = factory.DataTypeMappingSetTemplate("AccTypeMappingSet", NAMESPACE,
                                                       [(VehicleSpeed_T, VehicleSpeed_ImplType),
                                                        (SetSpeed_T, SetSpeed_ImplType),
                                                        (TargetDistance_T, TargetDistance_ImplType),
                                                        (RelativeSpeed_T, RelativeSpeed_ImplType),
                                                        (LongitudinalAccel_T, LongitudinalAccel_ImplType),
                                                        (TorqueRequest_T, TorqueRequest_ImplType),
                                                        (TimeGap_T, TimeGap_ImplType),
                                                        (RadarTargetValid_T, RadarTargetValid_ImplType),
                                                        (AccMode_T, AccMode_ImplType)])
