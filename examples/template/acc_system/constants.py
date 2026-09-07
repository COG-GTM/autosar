"""
Init-value constants.

Ports typed by application data types use physical init values.
"""
# pylint: disable=C0103

from . import datatype, factory

NAMESPACE = "Default"

VehicleSpeed_IV = factory.PhysicalConstantTemplate("VehicleSpeed_IV", NAMESPACE, 0, datatype.Units.KmPerHour)
SetSpeed_IV = factory.PhysicalConstantTemplate("SetSpeed_IV", NAMESPACE, 0, datatype.Units.KmPerHour)
TargetDistance_IV = factory.PhysicalConstantTemplate("TargetDistance_IV", NAMESPACE, 250, datatype.Units.Meter)
RelativeSpeed_IV = factory.PhysicalConstantTemplate("RelativeSpeed_IV", NAMESPACE, 0, datatype.Units.MeterPerSecond)
LongitudinalAccel_IV = factory.PhysicalConstantTemplate("LongitudinalAccel_IV", NAMESPACE, 0,
                                                        datatype.Units.MeterPerSecondSquared)
TorqueRequest_IV = factory.PhysicalConstantTemplate("TorqueRequest_IV", NAMESPACE, 0, datatype.Units.NewtonMeter)
TimeGap_IV = factory.PhysicalConstantTemplate("TimeGap_IV", NAMESPACE, 1.5, datatype.Units.Second)
RadarTargetValid_IV = factory.PhysicalConstantTemplate("RadarTargetValid_IV", NAMESPACE, "RadarTargetValid_NotValid")
