"""
Template factory for the Adaptive Cruise Control (ACC) example.

The factory layer describes how ARXML elements are created without deciding
where they end up. Package placement is decided by the namespaces of the
workspace (see config.toml).
"""
from typing import Any, Callable
import autosar.xml.element as ar_element
import autosar.xml.enumeration as ar_enum
import autosar.xml.template as ar_template
import autosar.xml.workspace as ar_workspace
from autosar.xml.template import TemplateBase

CreateFuncType = Callable[[ar_element.Package, ar_workspace.Workspace, dict[str, ar_element.ARElement] | None],
                          ar_element.ARElement]

DATA_TYPE_MAPPING_ROLE = "DataTypeMappingSet"


class SwBaseTypeTemplate(ar_template.ElementTemplate):
    """
    SwBaseType template
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 bit_size: int = None,
                 encoding: str = None,
                 native_declaration: str = None) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.BASE_TYPE)
        self.category = "FIXED_LENGTH"
        self.bit_size = bit_size
        self.encoding = encoding
        self.native_declaration = native_declaration

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.SwBaseType:
        """
        Factory method for SwBaseType
        """
        return ar_element.SwBaseType(name=self.element_name,
                                     category=self.category,
                                     size=self.bit_size,
                                     encoding=self.encoding,
                                     native_declaration=self.native_declaration)


class UnitTemplate(ar_template.ElementTemplate):
    """
    Physical unit template
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 display_name: str) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.UNIT)
        self.display_name = display_name

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.Unit:
        """
        Factory method
        """
        return ar_element.Unit(self.element_name, self.display_name)


class DataConstraintInternalTemplate(ar_template.ElementTemplate):
    """
    Template for internal (implementation-side) data constraints
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 lower_limit: int | float,
                 upper_limit: int | float) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.DATA_CONSTRAINT)
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.DataConstraint:
        """
        Factory method
        """
        return ar_element.DataConstraint.make_internal(self.element_name, self.lower_limit, self.upper_limit)


class DataConstraintPhysicalTemplate(ar_template.ElementTemplate):
    """
    Template for physical data constraints (used by application data types)
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 lower_limit: int | float,
                 upper_limit: int | float,
                 unit: UnitTemplate | None = None) -> None:
        dependencies = None if unit is None else [unit]
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.DATA_CONSTRAINT, dependencies)
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.unit = unit

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.DataConstraint:
        """
        Factory method
        """
        unit_ref = None
        if self.unit is not None:
            unit_ref = dependencies[self.unit.ref(workspace)].ref()
        return ar_element.DataConstraint.make_physical(self.element_name,
                                                       self.lower_limit,
                                                       self.upper_limit,
                                                       unit_ref=unit_ref)


class CompuMethodLinearTemplate(ar_template.ElementTemplate):
    """
    Template for linear compu-methods (internal value to physical value)

    physical_value = offset + factor * internal_value
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 factor: int | float,
                 offset: int | float,
                 lower_limit: int | float,
                 upper_limit: int | float,
                 unit: UnitTemplate | None = None,
                 desc: str | None = None) -> None:
        dependencies = None if unit is None else [unit]
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.COMPU_METHOD, dependencies)
        self.category = "LINEAR"
        self.factor = factor
        self.offset = offset
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.unit = unit
        self.desc = desc

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.CompuMethod:
        """
        Factory method
        """
        unit_ref = None
        if self.unit is not None:
            unit_ref = dependencies[self.unit.ref(workspace)].ref()
        computation = ar_element.Computation.make_rational(scaling_factor=self.factor,
                                                           offset=self.offset,
                                                           lower_limit=self.lower_limit,
                                                           upper_limit=self.upper_limit)
        return ar_element.CompuMethod(name=self.element_name,
                                      desc=self.desc,
                                      category=self.category,
                                      unit_ref=unit_ref,
                                      int_to_phys=computation)


class CompuMethodEnumTemplate(ar_template.ElementTemplate):
    """
    Template for text-table compu-methods
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 value_table: list[str] | list[tuple],
                 auto_label: bool = True,
                 desc: str | None = None) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.COMPU_METHOD)
        self.category = "TEXTTABLE"
        self.value_table = value_table
        self.auto_label = auto_label
        self.desc = desc

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.CompuMethod:
        """
        Factory method
        """
        computation = ar_element.Computation.make_value_table(self.value_table, auto_label=self.auto_label)
        return ar_element.CompuMethod(name=self.element_name,
                                      desc=self.desc,
                                      category=self.category,
                                      int_to_phys=computation)


class ApplicationValueTypeTemplate(ar_template.ElementTemplate):
    """
    Template for primitive application data types.

    An application data type carries the physical semantics of a signal
    (unit, resolution and physical range) while the implementation data type
    carries its in-memory representation.
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 compu_method: ar_template.ElementTemplate,
                 data_constraint: ar_template.ElementTemplate,
                 unit: UnitTemplate | None = None,
                 desc: str | None = None,
                 calibration_access: ar_enum.SwCalibrationAccess | None = None) -> None:
        dependencies = [compu_method, data_constraint]
        if unit is not None:
            dependencies.append(unit)
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.APPLICATION_DATA_TYPE, dependencies)
        self.category = "VALUE"
        self.compu_method = compu_method
        self.data_constraint = data_constraint
        self.unit = unit
        self.desc = desc
        self.calibration_access = calibration_access

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.ApplicationPrimitiveDataType:
        """
        Factory method
        """
        unit_ref = None if self.unit is None else dependencies[self.unit.ref(workspace)].ref()
        sw_data_def_props = ar_element.SwDataDefPropsConditional(
            compu_method_ref=self.compu_method.ref(workspace),
            data_constraint_ref=self.data_constraint.ref(workspace),
            unit_ref=unit_ref,
            calibration_access=self.calibration_access)
        return ar_element.ApplicationPrimitiveDataType(name=self.element_name,
                                                       desc=self.desc,
                                                       category=self.category,
                                                       sw_data_def_props=sw_data_def_props)


class ImplementationValueTypeTemplate(ar_template.ElementTemplate):
    """
    Template for value-based implementation data types
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 base_type: ar_template.ElementTemplate,
                 data_constraint: ar_template.ElementTemplate = None,
                 compu_method: ar_template.ElementTemplate = None,
                 desc: str | None = None,
                 calibration_access: ar_enum.SwCalibrationAccess | None = None,
                 type_emitter: str | None = None) -> None:
        dependencies = [base_type]
        if data_constraint is not None:
            dependencies.append(data_constraint)
        if compu_method is not None:
            dependencies.append(compu_method)
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.IMPLEMENTATION_DATA_TYPE, dependencies)
        self.category = "VALUE"
        self.desc = desc
        self.base_type = base_type
        self.data_constraint = data_constraint
        self.compu_method = compu_method
        self.calibration_access = calibration_access
        self.type_emitter = type_emitter

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.ImplementationDataType:
        """
        Factory method
        """
        compu_method_ref = None if self.compu_method is None else self.compu_method.ref(workspace)
        data_constraint_ref = None if self.data_constraint is None else self.data_constraint.ref(workspace)
        sw_data_def_props = ar_element.SwDataDefPropsConditional(base_type_ref=self.base_type.ref(workspace),
                                                                 compu_method_ref=compu_method_ref,
                                                                 data_constraint_ref=data_constraint_ref,
                                                                 calibration_access=self.calibration_access)
        return ar_element.ImplementationDataType(name=self.element_name,
                                                 desc=self.desc,
                                                 category=self.category,
                                                 sw_data_def_props=sw_data_def_props,
                                                 type_emitter=self.type_emitter)


class DataTypeMappingSetTemplate(ar_template.ElementTemplate):
    """
    Template for a data type mapping set.

    Each mapping pairs an application data type with the implementation data
    type used by the RTE to store it.
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 type_pairs: list[tuple[ar_template.ElementTemplate, ar_template.ElementTemplate]]) -> None:
        dependencies: list[TemplateBase] = []
        for application_type, implementation_type in type_pairs:
            dependencies.append(application_type)
            dependencies.append(implementation_type)
        super().__init__(element_name, namespace_name, DATA_TYPE_MAPPING_ROLE, dependencies)
        self.type_pairs = type_pairs

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.DataTypeMappingSet:
        """
        Factory method
        """
        elem = ar_element.DataTypeMappingSet(self.element_name)
        for application_type, implementation_type in self.type_pairs:
            application_element = dependencies[application_type.ref(workspace)]
            implementation_element = dependencies[implementation_type.ref(workspace)]
            elem.append(ar_element.DataTypeMap(application_element.ref(), implementation_element.ref()))
        return elem


class ModeDeclarationGroupTemplate(ar_template.ElementTemplate):
    """
    ModeDeclarationGroup template
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 mode_declarations: list[str],
                 initial_mode_name: str | None = None) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.MODE_DECLARATION)
        self.mode_declarations = list(mode_declarations)
        self.initial_mode_name = initial_mode_name

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.ModeDeclarationGroup:
        """
        Factory method
        """
        initial_mode_ref = None
        if self.initial_mode_name is not None:
            initial_mode_ref = '/'.join([str(package.ref()), self.element_name, self.initial_mode_name])
        return ar_element.ModeDeclarationGroup(name=self.element_name,
                                               mode_declarations=self.mode_declarations,
                                               initial_mode_ref=initial_mode_ref)


class ModeSwitchInterfaceTemplate(ar_template.ElementTemplate):
    """
    ModeSwitchInterface template
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 mode_declaration_group: ModeDeclarationGroupTemplate,
                 mode_group_name: str,
                 is_service: bool = False) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.PORT_INTERFACE, [mode_declaration_group])
        self.mode_group_name = mode_group_name
        self.mode_declaration_group = mode_declaration_group
        self.is_service = is_service

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.ModeSwitchInterface:
        """
        Factory method
        """
        elem = ar_element.ModeSwitchInterface(self.element_name, is_service=self.is_service)
        elem.create_mode_group(self.mode_group_name, self.mode_declaration_group.ref(workspace))
        return elem


class SenderReceiverInterfaceTemplate(ar_template.ElementTemplate):
    """
    Sender-receiver port interface template.

    data_elements is a list of tuples where each tuple is
    (data element name, data type template).
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 data_elements: list[tuple[str, ar_template.ElementTemplate]]) -> None:
        dependencies = [data_type for _, data_type in data_elements]
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.PORT_INTERFACE, dependencies)
        self.data_elements = data_elements

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.SenderReceiverInterface:
        """
        Factory method
        """
        port_interface = ar_element.SenderReceiverInterface(self.element_name)
        for element_name, data_type in self.data_elements:
            data_type_element = dependencies[data_type.ref(workspace)]
            port_interface.create_data_element(element_name, type_ref=data_type_element.ref())
        return port_interface


class GenericPortInterfaceTemplate(ar_template.ElementTemplate):
    """
    Generic port interface element template
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 create_func: CreateFuncType,
                 depends: list[TemplateBase] | None = None) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.PORT_INTERFACE, depends)
        self.create_func = create_func

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.PortInterface:
        """
        Factory method
        """
        return self.create_func(package, workspace, dependencies, **kwargs)


class GenericComponentTypeTemplate(ar_template.ElementTemplate):
    """
    Generic component type element template
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 create_func: CreateFuncType,
                 depends: list[TemplateBase] | None = None,
                 append_to_package: bool = False) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.COMPONENT_TYPE, depends, append_to_package)
        self.create_func = create_func

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.SwComponentType:
        """
        Factory method
        """
        return self.create_func(package, workspace, dependencies, **kwargs)


class SwcImplementationTemplate(ar_template.ElementTemplate):
    """
    SwcImplementation template
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 component_type: ar_template.ElementTemplate) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.COMPONENT_TYPE, [component_type])
        self.component_type = component_type

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.SwcImplementation:
        """
        Factory method
        """
        swc_type = dependencies[self.component_type.ref(workspace)]
        return ar_element.SwcImplementation(self.element_name, behavior_ref=swc_type.internal_behavior.ref())


class ConstantTemplate(ar_template.ElementTemplate):
    """
    Constant template based on raw (internal) values
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 value: Any) -> None:
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.CONSTANT)
        self.value = value

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.ConstantSpecification:
        """
        Factory method
        """
        return ar_element.ConstantSpecification.make_constant(self.element_name, self.value)


class PhysicalConstantTemplate(ar_template.ElementTemplate):
    """
    Constant template based on physical values.

    Init values of ports typed by application data types shall be expressed as
    physical values (AR:APPLICATION-VALUE-SPECIFICATION) and not as raw
    integers, which is what this template creates.
    """

    def __init__(self,
                 element_name: str,
                 namespace_name: str,
                 value: int | float | str,
                 unit: UnitTemplate | None = None,
                 category: str = "VALUE") -> None:
        dependencies = None if unit is None else [unit]
        super().__init__(element_name, namespace_name, ar_enum.PackageRole.CONSTANT, dependencies)
        self.value = value
        self.unit = unit
        self.category = category

    def create(self,
               package: ar_element.Package,
               workspace: ar_workspace.Workspace,
               dependencies: dict[str, ar_element.ARElement] | None,
               **kwargs) -> ar_element.ConstantSpecification:
        """
        Factory method
        """
        unit_ref = None
        unit_display_name = None
        if self.unit is not None:
            unit_element = dependencies[self.unit.ref(workspace)]
            unit_ref = unit_element.ref()
            unit_display_name = unit_element.display_name
        value_cont = ar_element.SwValueCont(unit_ref=unit_ref,
                                            unit_display_name=unit_display_name,
                                            sw_values_phys=ar_element.SwValues([self.value]))
        value_spec = ar_element.ApplicationValueSpecification(category=self.category, sw_value_cont=value_cont)
        return ar_element.ConstantSpecification(self.element_name, value_spec)
