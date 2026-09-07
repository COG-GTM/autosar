"""
Mode declaration groups
"""
# pylint: disable=C0103

from . import factory

NAMESPACE = "Default"

AccMode = factory.ModeDeclarationGroupTemplate("AccMode", NAMESPACE,
                                               ["OFF", "STANDBY", "ACTIVE", "OVERRIDE"],
                                               "OFF")
