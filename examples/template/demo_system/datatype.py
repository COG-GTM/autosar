"""
data types
"""
# flake8: noqa
# pylint: disable=C0103, C0301

from . import factory, platform

NAMESPACE = "Default"

InactiveActive_T = factory.ImplementationEnumDataTypeTemplate("InactiveActive_T", NAMESPACE, platform.BaseTypes.uint8, ["InactiveActive_Inactive", "InactiveActive_Active"])

# WheelSpeed_T: uint16, 0.01 km/h per bit (physical range 0 .. 655.35 km/h)
KmPerHour = factory.UnitTemplate("KmPerHour", NAMESPACE, "km/h")
WheelSpeed_T_DataConstr = factory.DataConstraintInternalTemplate("WheelSpeed_T_DataConstr", NAMESPACE, 0, 65535)
WheelSpeed_T_CompuMethod = factory.CompuMethodLinearTemplate("WheelSpeed_T_CompuMethod", NAMESPACE, 0.01, 0, 0, 65535, unit=KmPerHour)
WheelSpeed_T = factory.ImplementationValueTypeTemplate("WheelSpeed_T", NAMESPACE, platform.BaseTypes.uint16, WheelSpeed_T_DataConstr, WheelSpeed_T_CompuMethod)
