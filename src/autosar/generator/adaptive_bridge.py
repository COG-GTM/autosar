"""
Classic-to-Adaptive bridge (v0 prototype, AE-29).

Reads a Classic AUTOSAR SWC description with autosar.xml.Reader and derives:

* an Adaptive ServiceInterface description (ARXML) with a SOME/IP deployment
* C++14 ara::com-style proxy/skeleton headers targeting the SOME/IP classes
  of the COG-GTM/Adaptive-AUTOSAR simulator

Mapping rules (v0):

* provided sender-receiver port / data element -> Adaptive Event
* provided client-server port / operation      -> Adaptive Method
* ImplementationDataType                       -> C++ type alias

PROTOTYPE ONLY. This is not a certified toolchain. The ARXML output is not
validated against the AUTOSAR Adaptive XSD and the C++ output is not a
complete ara::com binding. See examples/generator/adaptive/README.md.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Iterable
import autosar.xml.element as ar_element
import autosar.xml.enumeration as ar_enum
import autosar.xml.reader as ar_reader

GENERATOR_NAME = "autosar classic-to-adaptive bridge v0 (AE-29 prototype)"
DISCLAIMER = "PROTOTYPE OUTPUT - not a certified toolchain, not for production or safety use."
FIRST_EVENT_ID = 0x8001
FIRST_METHOD_ID = 0x0001
EVENT_GROUP_ID = 1
SOMEIP_PROTOCOL_VERSION = 1

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_CPP_KEYWORDS = frozenset("""
alignas alignof and and_eq asm auto bitand bitor bool break case catch char char16_t char32_t class compl const
constexpr const_cast continue decltype default delete do double dynamic_cast else enum explicit export extern false
float for friend goto if inline int long mutable namespace new noexcept not not_eq nullptr operator or or_eq private
protected public register reinterpret_cast return short signed sizeof static static_assert static_cast struct switch
template this thread_local throw true try typedef typeid typename union unsigned using virtual void volatile wchar_t
while xor xor_eq
""".split())
# Member names of the generated proxy/skeleton classes that an event or method must not shadow.
_RESERVED_MEMBERS = frozenset(["OfferService", "StopOfferService", "IsOffered"])


# Short names used for the primitive types in the generated ARXML package
_PRIMITIVE_NAMES = frozenset(["bool", "float", "double"]).union(
    f"{prefix}int{size}_t" for prefix in ("", "u") for size in (8, 16, 32, 64))


class BridgeError(Exception):
    """
    Raised when the Classic input cannot be mapped by the v0 rules
    """


@dataclass(frozen=True)
class CppType:
    """
    C++ type derived from a Classic ImplementationDataType
    """

    name: str  # Alias name, same as the short name of the ImplementationDataType
    target: str  # What the alias points to: a <cstdint> type, bool, float, double or another alias
    classic_ref: str
    base_type_ref: str | None = None  # Set for category VALUE
    referenced_type: str | None = None  # Set for category TYPE_REFERENCE
    compu_method_ref: str | None = None
    data_constraint_ref: str | None = None


@dataclass(frozen=True)
class Event:
    """
    Adaptive event derived from a data element of a provided sender-receiver port
    """

    name: str
    event_id: int
    data_type: CppType
    classic_port_ref: str
    classic_element_ref: str


@dataclass(frozen=True)
class Argument:
    """
    Method argument derived from an ArgumentDataPrototype
    """

    name: str
    direction: str  # IN, OUT or INOUT
    data_type: CppType


@dataclass(frozen=True)
class Method:
    """
    Adaptive method derived from an operation of a provided client-server port
    """

    name: str
    method_id: int
    arguments: tuple[Argument, ...]
    classic_port_ref: str
    classic_operation_ref: str

    @property
    def in_arguments(self) -> tuple[Argument, ...]:
        """Arguments sent in the request"""
        return tuple(arg for arg in self.arguments if arg.direction in ("IN", "INOUT"))

    @property
    def out_arguments(self) -> tuple[Argument, ...]:
        """Arguments sent in the response"""
        return tuple(arg for arg in self.arguments if arg.direction in ("OUT", "INOUT"))


@dataclass
class ServiceModel:
    """
    Adaptive service derived from one Classic SWC
    """

    name: str
    classic_swc_ref: str
    service_id: int
    major_version: int
    minor_version: int
    namespace: tuple[str, ...]
    events: list[Event] = field(default_factory=list)
    methods: list[Method] = field(default_factory=list)
    types: list[CppType] = field(default_factory=list)  # In dependency order
    not_mapped: list[str] = field(default_factory=list)

    @property
    def file_stem(self) -> str:
        """Base name of all generated files"""
        return to_snake_case(self.name)

    @property
    def package_name(self) -> str:
        """Short name of the generated AR-PACKAGE"""
        return self.name + "Manifest"


def to_snake_case(name: str) -> str:
    """
    Converts PascalCase to snake_case (file naming convention of Adaptive-AUTOSAR)
    """
    result = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    return re.sub(r"_+", "_", result).lower()


def _check_identifier(name: str, what: str) -> str:
    if not _IDENTIFIER.match(name) or name in _CPP_KEYWORDS or "__" in name:
        raise BridgeError(f"{what} '{name}' is not usable as a C++ identifier")
    return name


def base_type_to_cpp(base_type: ar_element.SwBaseType) -> str:
    """
    Maps a SwBaseType to a C++ type using its size and encoding.
    Falls back to the short name and the native declaration when the encoding is not conclusive.
    """
    size = base_type.size
    encoding = (base_type.encoding or "").upper()
    hints = tuple(text.lower() for text in (base_type.name, base_type.native_declaration) if text)
    if encoding == "BOOLEAN" or (not encoding and any(hint in ("boolean", "bool") for hint in hints)):
        return "bool"
    if encoding == "IEEE754" or any(hint.startswith("float") or hint == "double" for hint in hints):
        if size == 32:
            return "float"
        if size == 64:
            return "double"
        raise BridgeError(f"Base type '{base_type.name}': unsupported floating point size {size}")
    if size not in (8, 16, 32, 64):
        raise BridgeError(f"Base type '{base_type.name}': unsupported size {size}")
    signed = encoding in ("2C", "1C", "SM") or encoding.startswith("SINT") or \
        (not encoding.startswith("UINT") and any(hint.startswith(("sint", "int")) for hint in hints))
    return f"std::{'' if signed else 'u'}int{size}_t"


class ClassicModel:
    """
    Index of all elements of the loaded Classic ARXML documents, by reference
    """

    def __init__(self) -> None:
        self.elements: dict[str, ar_element.ARElement] = {}

    def load_files(self, file_paths: Iterable[str]) -> None:
        """
        Reads ARXML files with autosar.xml.Reader
        """
        for file_path in file_paths:
            reader = ar_reader.Reader()
            self.add_document(reader.read_file(file_path))

    def load_str(self, xml: str) -> None:
        """
        Reads one ARXML document from string
        """
        self.add_document(ar_reader.Reader().read_str(xml))

    def add_document(self, document: ar_element.PackageCollection) -> None:
        """
        Indexes the packages of a document (or workspace)
        """
        for package in document.packages:
            self._add_package(package, "/" + package.name)

    def _add_package(self, package: ar_element.Package, path: str) -> None:
        for element in package.elements:
            self.elements.setdefault(f"{path}/{element.name}", element)
        for sub_package in package.packages:
            self._add_package(sub_package, f"{path}/{sub_package.name}")

    def find(self, ref: object, expected_type: type | None = None) -> ar_element.ARElement:
        """
        Returns the element behind a reference, raises BridgeError if it is not loaded
        """
        path = str(ref)
        element = self.elements.get(path)
        if element is None:
            raise BridgeError(f"Reference '{path}' cannot be resolved in the loaded ARXML files")
        if expected_type is not None and not isinstance(element, expected_type):
            raise BridgeError(f"'{path}' is {type(element).__name__}, expected {expected_type.__name__}")
        return element

    def find_swc(self, name: str) -> tuple[str, ar_element.SwComponentType]:
        """
        Finds a SWC by short name or by full reference
        """
        matches = [(ref, element) for ref, element in self.elements.items()
                   if isinstance(element, ar_element.SwComponentType) and name in (ref, element.name)]
        if len(matches) != 1:
            raise BridgeError(f"Expected exactly one SWC named '{name}', found {len(matches)}")
        return matches[0]


class _TypeMapper:
    """
    Maps ImplementationDataTypes to C++ aliases, keeping dependency order
    """

    def __init__(self, classic: ClassicModel) -> None:
        self.classic = classic
        self.types: dict[str, CppType] = {}
        self._names: dict[str, str] = {}

    def map(self, ref: object) -> CppType:
        """
        Returns the C++ type for a data type reference
        """
        path = str(ref)
        if path in self.types:
            return self.types[path]
        data_type = self.classic.find(path)
        if not isinstance(data_type, ar_element.ImplementationDataType):
            raise BridgeError(f"'{path}' is {type(data_type).__name__}: "
                              "v0 only maps ImplementationDataType")
        name = _check_identifier(data_type.name, "Data type")
        if name in _PRIMITIVE_NAMES:
            raise BridgeError(f"Data type '{path}' has the name of a C++ primitive, "
                              "which would be ambiguous in the generated ARXML package")
        if self._names.setdefault(name, path) != path:
            raise BridgeError(f"Data types '{self._names[name]}' and '{path}' have the same short name")
        props = data_type.sw_data_def_props[0] if data_type.sw_data_def_props else None
        optional = {
            "compu_method_ref": str(props.compu_method_ref) if props and props.compu_method_ref else None,
            "data_constraint_ref": str(props.data_constraint_ref) if props and props.data_constraint_ref else None,
        }
        if data_type.category == "VALUE" and props is not None and props.base_type_ref is not None:
            base_type = self.classic.find(props.base_type_ref, ar_element.SwBaseType)
            cpp_type = CppType(name, base_type_to_cpp(base_type), path,
                               base_type_ref=str(props.base_type_ref), **optional)
        elif data_type.category == "TYPE_REFERENCE" and props is not None and props.impl_data_type_ref is not None:
            target = self.map(props.impl_data_type_ref)
            cpp_type = CppType(name, target.name, path, referenced_type=target.name, **optional)
        else:
            raise BridgeError(f"Data type '{path}' has category {data_type.category}: "
                              "v0 only maps VALUE and TYPE_REFERENCE")
        self.types[path] = cpp_type
        return cpp_type


def build_service_model(classic: ClassicModel,
                        swc_name: str,
                        service_name: str | None = None,
                        service_id: int = 0x1000,
                        major_version: int = 1,
                        minor_version: int = 0,
                        namespace: Iterable[str] | None = None) -> ServiceModel:
    """
    Applies the v0 mapping rules to one SWC
    """
    swc_ref, swc = classic.find_swc(swc_name)
    name = _check_identifier(service_name or swc.name + "Service", "Service name")
    if not 0 < service_id < 0xFFFF:
        raise BridgeError(f"Service ID 0x{service_id:04X} is outside 0x0001..0xFFFE")
    if not 0 <= major_version <= 0xFF:
        raise BridgeError(f"Major version {major_version} does not fit the 8-bit SOME/IP interface version")
    if namespace is None:
        namespace = ("generated", name.lower())
    model = ServiceModel(name, swc_ref, service_id, major_version, minor_version,
                         tuple(_check_identifier(part, "Namespace") for part in namespace))
    type_mapper = _TypeMapper(classic)
    events: list[tuple[str, str, CppType, str, str]] = []
    methods: list[tuple[str, str, tuple[Argument, ...], str, str]] = []
    for port in swc.ports:
        port_ref = f"{swc_ref}/{port.name}"
        if not isinstance(port, ar_element.ProvidePortPrototype):
            model.not_mapped.append(f"{port_ref}: {type(port).__name__} (v0 maps provided ports only)")
            continue
        interface_ref = str(port.port_interface_ref)
        interface = classic.find(interface_ref)
        if isinstance(interface, ar_element.SenderReceiverInterface):
            for data_element in interface.data_elements:
                events.append((port.name, data_element.name, type_mapper.map(data_element.type_ref),
                               port_ref, f"{interface_ref}/{data_element.name}"))
        elif isinstance(interface, ar_element.ClientServerInterface):
            for operation in interface.operations:
                operation_ref = f"{interface_ref}/{operation.name}"
                arguments = tuple(Argument(_check_identifier(argument.name, "Argument"),
                                           ar_enum.enum_to_xml(argument.direction),
                                           type_mapper.map(argument.type_ref))
                                  for argument in operation.arguments)
                if len({argument.name for argument in arguments}) != len(arguments):
                    raise BridgeError(f"Operation '{operation_ref}' has duplicate argument names")
                if operation.possible_error_refs:
                    model.not_mapped.append(f"{operation_ref}: possible errors (v0 has no ApApplicationError)")
                methods.append((port.name, operation.name, arguments, port_ref, operation_ref))
        else:
            model.not_mapped.append(f"{port_ref}: {type(interface).__name__} {interface_ref} "
                                    "(v0 maps sender-receiver and client-server only)")
    members = [(port, member) for port, member, *_ in events]
    members.extend((port, member) for port, member, *_ in methods)
    names = _unique_member_names(members)
    for index, (_, _, data_type, port_ref, element_ref) in enumerate(events):
        model.events.append(Event(names[index], FIRST_EVENT_ID + index, data_type, port_ref, element_ref))
    for index, (_, _, arguments, port_ref, operation_ref) in enumerate(methods):
        model.methods.append(Method(names[len(events) + index], FIRST_METHOD_ID + index,
                                    arguments, port_ref, operation_ref))
    if len(model.events) > 0x7FFF or len(model.methods) > 0x7FFF:
        raise BridgeError("Too many events or methods for the SOME/IP ID ranges")
    if not model.events and not model.methods:
        raise BridgeError(f"SWC '{swc_ref}' has no provided sender-receiver or client-server port to map")
    model.types = list(type_mapper.types.values())
    for cpp_type in model.types:
        if cpp_type.compu_method_ref is not None:
            model.not_mapped.append(f"{cpp_type.classic_ref}: CompuMethod {cpp_type.compu_method_ref} "
                                    "(events and methods carry the raw internal value)")
    return model


def _unique_member_names(members: list[tuple[str, str]]) -> list[str]:
    """
    Uses the element name where it is unique in the service, else <Port>_<Element>
    """
    count: dict[str, int] = {}
    for _, member in members:
        count[member] = count.get(member, 0) + 1
    result = []
    for port, member in members:
        name = member if count[member] == 1 else f"{port}_{member}"
        _check_identifier(name, "Event/method")
        if name in _RESERVED_MEMBERS:
            raise BridgeError(f"Event/method name '{name}' is reserved by the generated classes")
        result.append(name)
    if len(set(result)) != len(result):
        raise BridgeError("Event/method names are not unique within the service")
    return result


# ---------------------------------------------------------------------------------------------------------------------
# ARXML rendering
# ---------------------------------------------------------------------------------------------------------------------

_STD_TYPES = ("bool", "float", "double")


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _xml(tag: str, *children: object, attr: str = "") -> tuple:
    return (tag, attr, children)


def _render_xml(node: tuple, lines: list[str], level: int) -> None:
    tag, attr, children = node
    indent = "  " * level
    opening = f"{tag} {attr}" if attr else tag
    if len(children) == 1 and not isinstance(children[0], tuple):
        lines.append(f"{indent}<{opening}>{_xml_escape(str(children[0]))}</{tag}>")
        return
    lines.append(f"{indent}<{opening}>")
    for child in children:
        _render_xml(child, lines, level + 1)
    lines.append(f"{indent}</{tag}>")


def _desc(text: str) -> tuple:
    return _xml("DESC", _xml("L-2", text, attr='L="EN"'))


def _std_type_name(target: str) -> str:
    return target.split("::")[-1]


def render_arxml(model: ServiceModel) -> str:
    """
    Renders the Adaptive ServiceInterface description with its SOME/IP deployment
    """
    package_ref = "/" + model.package_name
    interface_ref = f"{package_ref}/{model.name}"
    deployment_name = model.name + "_SomeIp"
    deployment_ref = f"{package_ref}/{deployment_name}"
    type_dest = 'DEST="STD-CPP-IMPLEMENTATION-DATA-TYPE"'
    elements = []
    std_types = []
    for cpp_type in model.types:
        if cpp_type.referenced_type is None and cpp_type.target not in std_types:
            std_types.append(cpp_type.target)
    for target in std_types:
        children = [_xml("SHORT-NAME", _std_type_name(target)), _xml("CATEGORY", "VALUE")]
        if target.startswith("std::"):
            children.append(_xml("NAMESPACES", _xml("SYMBOL-PROPS", _xml("SHORT-NAME", "std"),
                                                    _xml("SYMBOL", "std"))))
        elements.append(_xml("STD-CPP-IMPLEMENTATION-DATA-TYPE", *children))
    namespaces = _xml("NAMESPACES", *[_xml("SYMBOL-PROPS", _xml("SHORT-NAME", part), _xml("SYMBOL", part))
                                      for part in model.namespace])
    for cpp_type in model.types:
        target = cpp_type.referenced_type or _std_type_name(cpp_type.target)
        elements.append(_xml("STD-CPP-IMPLEMENTATION-DATA-TYPE",
                             _xml("SHORT-NAME", cpp_type.name),
                             _desc(f"Generated from Classic ImplementationDataType {cpp_type.classic_ref}"),
                             _xml("CATEGORY", "TYPE_REFERENCE"),
                             namespaces,
                             _xml("TYPE-REFERENCE-REF", f"{package_ref}/{target}", attr=type_dest)))
    interface = [_xml("SHORT-NAME", model.name),
                 _desc(f"Generated from Classic SWC {model.classic_swc_ref} by {GENERATOR_NAME}. {DISCLAIMER}"),
                 namespaces]
    if model.events:
        interface.append(_xml("EVENTS", *[
            _xml("VARIABLE-DATA-PROTOTYPE",
                 _xml("SHORT-NAME", event.name),
                 _desc(f"Generated from port {event.classic_port_ref}, data element {event.classic_element_ref}"),
                 _xml("TYPE-TREF", f"{package_ref}/{event.data_type.name}", attr=type_dest))
            for event in model.events]))
    if model.methods:
        interface.append(_xml("METHODS", *[
            _xml("CLIENT-SERVER-OPERATION",
                 _xml("SHORT-NAME", method.name),
                 _desc(f"Generated from port {method.classic_port_ref}, operation {method.classic_operation_ref}"),
                 *([_xml("ARGUMENTS", *[
                     _xml("ARGUMENT-DATA-PROTOTYPE",
                          _xml("SHORT-NAME", argument.name),
                          _xml("TYPE-TREF", f"{package_ref}/{argument.data_type.name}", attr=type_dest),
                          _xml("DIRECTION", argument.direction))
                     for argument in method.arguments])] if method.arguments else []))
            for method in model.methods]))
    elements.append(_xml("SERVICE-INTERFACE", *interface))
    deployment = [_xml("SHORT-NAME", deployment_name)]
    if model.events:
        deployment.append(_xml("EVENT-DEPLOYMENTS", *[
            _xml("SOMEIP-EVENT-DEPLOYMENT",
                 _xml("SHORT-NAME", event.name),
                 _xml("EVENT-REF", f"{interface_ref}/{event.name}", attr='DEST="VARIABLE-DATA-PROTOTYPE"'),
                 _xml("EVENT-ID", event.event_id),
                 _xml("TRANSPORT-PROTOCOL", "UDP"))
            for event in model.events]))
    if model.methods:
        deployment.append(_xml("METHOD-DEPLOYMENTS", *[
            _xml("SOMEIP-METHOD-DEPLOYMENT",
                 _xml("SHORT-NAME", method.name),
                 _xml("METHOD-REF", f"{interface_ref}/{method.name}", attr='DEST="CLIENT-SERVER-OPERATION"'),
                 _xml("METHOD-ID", method.method_id),
                 _xml("TRANSPORT-PROTOCOL", "TCP"))
            for method in model.methods]))
    deployment.append(_xml("SERVICE-INTERFACE-REF", interface_ref, attr='DEST="SERVICE-INTERFACE"'))
    if model.events:
        deployment.append(_xml("EVENT-GROUPS", _xml(
            "SOMEIP-EVENT-GROUP",
            _xml("SHORT-NAME", "AllEvents"),
            _xml("EVENT-GROUP-ID", EVENT_GROUP_ID),
            _xml("EVENT-REFS", *[_xml("EVENT-REF", f"{deployment_ref}/{event.name}",
                                      attr='DEST="SOMEIP-EVENT-DEPLOYMENT"') for event in model.events]))))
    deployment.append(_xml("SERVICE-INTERFACE-ID", model.service_id))
    deployment.append(_xml("SERVICE-INTERFACE-VERSION",
                           _xml("MAJOR-VERSION", model.major_version),
                           _xml("MINOR-VERSION", model.minor_version)))
    elements.append(_xml("SOMEIP-SERVICE-INTERFACE-DEPLOYMENT", *deployment))
    root = _xml("AUTOSAR",
                _xml("AR-PACKAGES", _xml("AR-PACKAGE",
                                         _xml("SHORT-NAME", model.package_name),
                                         _xml("ELEMENTS", *elements))),
                attr='xmlns="http://autosar.org/schema/r4.0" '
                     'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                     'xsi:schemaLocation="http://autosar.org/schema/r4.0 AUTOSAR_00051.xsd"')
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f"<!-- GENERATED FILE - DO NOT EDIT. {GENERATOR_NAME}. -->",
             f"<!-- {DISCLAIMER} Not validated against the AUTOSAR XSD. -->"]
    _render_xml(root, lines, 0)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------------------------------------------
# C++ rendering
# ---------------------------------------------------------------------------------------------------------------------

_SERIALIZABLE = (("bool", None), ("std::uint8_t", None), ("std::uint16_t", None), ("std::uint32_t", None),
                 ("std::uint64_t", None), ("std::int8_t", "std::uint8_t"), ("std::int16_t", "std::uint16_t"),
                 ("std::int32_t", "std::uint32_t"), ("std::int64_t", "std::uint64_t"),
                 ("float", "std::uint32_t"), ("double", "std::uint64_t"))


class _Cpp:
    """
    Minimal C++ source writer (Allman braces, 4 space indentation)
    """

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.level = 0

    def line(self, text: str = "") -> None:
        """Appends one line at the current indentation"""
        self.lines.append(("    " * self.level + text) if text else "")

    def open(self, text: str | None = None) -> None:
        """Appends an optional statement and an opening brace"""
        if text is not None:
            self.line(text)
        self.line("{")
        self.level += 1

    def close(self, suffix: str = "") -> None:
        """Appends a closing brace"""
        self.level -= 1
        self.line("}" + suffix)

    def access(self, name: str) -> None:
        """Appends an access specifier"""
        self.level -= 1
        self.line(name + ":")
        self.level += 1

    def __str__(self) -> str:
        return "\n".join(self.lines) + "\n"


def _begin_header(model: ServiceModel, suffix: str, brief: str, includes: list[str]) -> tuple[_Cpp, str]:
    guard = f"{model.file_stem}_{suffix}_h".upper()
    cpp = _Cpp()
    cpp.line("// GENERATED FILE - DO NOT EDIT.")
    cpp.line(f"// Generator: {GENERATOR_NAME}")
    cpp.line(f"// Source:    Classic SWC {model.classic_swc_ref}")
    cpp.line(f"// {DISCLAIMER}")
    cpp.line("//")
    cpp.line(f"// {brief}")
    cpp.line()
    cpp.line(f"#ifndef {guard}")
    cpp.line(f"#define {guard}")
    cpp.line()
    for include in includes:
        cpp.line(f"#include {include}")
    cpp.line()
    for part in model.namespace:
        cpp.open(f"namespace {part}")
    return cpp, guard


def _end_header(model: ServiceModel, cpp: _Cpp) -> str:
    for _ in model.namespace:
        cpp.close()
    cpp.line()
    cpp.line("#endif")
    return str(cpp)


def render_types_header(model: ServiceModel) -> str:
    """
    Renders the C++ aliases of the mapped ImplementationDataTypes
    """
    cpp, _ = _begin_header(model, "types", "C++ types mapped from Classic ImplementationDataTypes.", ["<cstdint>"])
    for index, cpp_type in enumerate(model.types):
        if index > 0:
            cpp.line()
        cpp.line(f"/// @brief Classic ImplementationDataType {cpp_type.classic_ref}")
        if cpp_type.base_type_ref is not None:
            cpp.line(f"/// @note Base type: {cpp_type.base_type_ref}")
        if cpp_type.compu_method_ref is not None:
            cpp.line(f"/// @note CompuMethod {cpp_type.compu_method_ref} is NOT applied (raw internal value)")
        if cpp_type.data_constraint_ref is not None:
            cpp.line(f"/// @note DataConstr {cpp_type.data_constraint_ref} is NOT enforced")
        cpp.line(f"using {cpp_type.name} = {cpp_type.target};")
    return _end_header(model, cpp)


def _hex(value: int) -> str:
    return f"0x{value:04x}"


def render_common_header(model: ServiceModel, ara_include_prefix: str) -> str:
    """
    Renders the SOME/IP identifiers, the payload serialization and the event notification message
    """
    cpp, _ = _begin_header(
        model, "common", "SOME/IP deployment identifiers and payload serialization shared by proxy and skeleton.",
        ["<algorithm>", "<cstddef>", "<cstdint>", "<stdexcept>", "<utility>", "<vector>",
         f'"{ara_include_prefix}/com/someip/someip_message.h"', f'"./{model.file_stem}_types.h"'])
    cpp.line("/// @brief SOME/IP service interface ID")
    cpp.line(f"const std::uint16_t cServiceId{{{_hex(model.service_id)}}};")
    cpp.line("/// @brief Service interface major version (SOME/IP interface version)")
    cpp.line(f"const std::uint8_t cMajorVersion{{{model.major_version}}};")
    cpp.line("/// @brief Service interface minor version")
    cpp.line(f"const std::uint32_t cMinorVersion{{{model.minor_version}}};")
    cpp.line("/// @brief SOME/IP protocol version")
    cpp.line(f"const std::uint8_t cProtocolVersion{{{SOMEIP_PROTOCOL_VERSION}}};")
    if model.events:
        cpp.line("/// @brief Event group that contains all the events of the service")
        cpp.line(f"const std::uint16_t cEventgroupId{{{_hex(EVENT_GROUP_ID)}}};")
    for event in model.events:
        cpp.line(f"/// @brief Event ID of {event.name} ({event.classic_element_ref})")
        cpp.line(f"const std::uint16_t c{event.name}EventId{{{_hex(event.event_id)}}};")
    for method in model.methods:
        cpp.line(f"/// @brief Method ID of {method.name} ({method.classic_operation_ref})")
        cpp.line(f"const std::uint16_t c{method.name}MethodId{{{_hex(method.method_id)}}};")
    cpp.line()
    cpp.line("/// @brief Big-endian (network byte order) payload serialization of the basic types")
    cpp.open("namespace serialization")
    cpp.line("template <typename TUnsigned>")
    cpp.line("void AppendBigEndian(std::vector<std::uint8_t> &payload, TUnsigned value)")
    cpp.open()
    cpp.open("for (std::size_t _index = sizeof(TUnsigned); _index > 0; --_index)")
    cpp.line("payload.push_back(")
    cpp.line("    static_cast<std::uint8_t>(value >> (8 * (_index - 1))));")
    cpp.close()
    cpp.close()
    cpp.line()
    cpp.line("template <typename TUnsigned>")
    cpp.line("bool TryExtractBigEndian(")
    cpp.line("    const std::vector<std::uint8_t> &payload,")
    cpp.line("    std::size_t &offset,")
    cpp.line("    TUnsigned &value)")
    cpp.open()
    cpp.line("if (offset > payload.size() ||")
    cpp.line("    payload.size() - offset < sizeof(TUnsigned))")
    cpp.open()
    cpp.line("return false;")
    cpp.close()
    cpp.line()
    cpp.line("TUnsigned _result{0};")
    cpp.open("for (std::size_t _index = 0; _index < sizeof(TUnsigned); ++_index)")
    cpp.line("_result = static_cast<TUnsigned>(")
    cpp.line("    (_result << 8) | payload[offset + _index]);")
    cpp.close()
    cpp.line()
    cpp.line("offset += sizeof(TUnsigned);")
    cpp.line("value = _result;")
    cpp.line("return true;")
    cpp.close()
    for type_name, carrier in _SERIALIZABLE:
        cpp.line()
        cpp.line("inline void Serialize(")
        cpp.line(f"    std::vector<std::uint8_t> &payload, {type_name} value)")
        cpp.open()
        if type_name == "bool":
            cpp.line("payload.push_back(value ? 1 : 0);")
        elif carrier is None:
            cpp.line("AppendBigEndian(payload, value);")
        elif type_name in ("float", "double"):
            cpp.line(f"{carrier} _raw;")
            cpp.line("const std::uint8_t *cBytes{")
            cpp.line("    reinterpret_cast<const std::uint8_t *>(&value)};")
            cpp.line("std::copy(")
            cpp.line("    cBytes, cBytes + sizeof(_raw),")
            cpp.line("    reinterpret_cast<std::uint8_t *>(&_raw));")
            cpp.line("AppendBigEndian(payload, _raw);")
        else:
            cpp.line(f"AppendBigEndian(payload, static_cast<{carrier}>(value));")
        cpp.close()
        cpp.line()
        cpp.line("inline bool TryDeserialize(")
        cpp.line("    const std::vector<std::uint8_t> &payload,")
        cpp.line("    std::size_t &offset,")
        cpp.line(f"    {type_name} &value)")
        cpp.open()
        if carrier is None and type_name != "bool":
            cpp.line("return TryExtractBigEndian(payload, offset, value);")
        else:
            cpp.line(f"{carrier or 'std::uint8_t'} _raw;")
            cpp.open("if (!TryExtractBigEndian(payload, offset, _raw))")
            cpp.line("return false;")
            cpp.close()
            cpp.line()
            if type_name == "bool":
                cpp.line("value = (_raw != 0);")
            elif type_name in ("float", "double"):
                cpp.line("const std::uint8_t *cBytes{")
                cpp.line("    reinterpret_cast<const std::uint8_t *>(&_raw)};")
                cpp.line("std::copy(")
                cpp.line("    cBytes, cBytes + sizeof(value),")
                cpp.line("    reinterpret_cast<std::uint8_t *>(&value));")
            else:
                cpp.line(f"value = static_cast<{type_name}>(_raw);")
            cpp.line("return true;")
        cpp.close()
    cpp.close()
    if model.events:
        _render_event_message(cpp)
    return _end_header(model, cpp)


def _render_event_message(cpp: _Cpp) -> None:
    cpp.line()
    cpp.line("/// @brief SOME/IP notification message that carries one event sample")
    cpp.open("class EventMessage : public ara::com::someip::SomeIpMessage")
    cpp.access("private")
    cpp.line("static const std::size_t cHeaderSize{16};")
    cpp.line()
    cpp.line("std::vector<std::uint8_t> mEventPayload;")
    cpp.line()
    cpp.access("public")
    cpp.line("/// @brief Constructor")
    cpp.line("/// @param eventId SOME/IP event ID")
    cpp.line("/// @param sessionId Notification session ID")
    cpp.line("/// @param eventPayload Serialized event sample")
    cpp.line("EventMessage(")
    cpp.line("    std::uint16_t eventId,")
    cpp.line("    std::uint16_t sessionId,")
    cpp.line("    std::vector<std::uint8_t> eventPayload)")
    cpp.line("    : ara::com::someip::SomeIpMessage(")
    cpp.line("          (static_cast<std::uint32_t>(cServiceId) << 16) | eventId,")
    cpp.line("          0,")
    cpp.line("          cProtocolVersion,")
    cpp.line("          cMajorVersion,")
    cpp.line("          ara::com::someip::SomeIpMessageType::Notification,")
    cpp.line("          sessionId),")
    cpp.line("      mEventPayload{std::move(eventPayload)}")
    cpp.open()
    cpp.close()
    cpp.line()
    cpp.line("std::uint32_t Length() const noexcept override")
    cpp.open()
    cpp.line("const std::uint32_t cHeaderRemainder{8};")
    cpp.line("return cHeaderRemainder +")
    cpp.line("       static_cast<std::uint32_t>(mEventPayload.size());")
    cpp.close()
    cpp.line()
    cpp.line("std::vector<std::uint8_t> Payload() const override")
    cpp.open()
    cpp.line("std::vector<std::uint8_t> _result{")
    cpp.line("    ara::com::someip::SomeIpMessage::Payload()};")
    cpp.line("_result.insert(")
    cpp.line("    _result.end(), mEventPayload.cbegin(), mEventPayload.cend());")
    cpp.line()
    cpp.line("return _result;")
    cpp.close()
    cpp.line()
    cpp.line("/// @brief SOME/IP event ID (lower half of the message ID)")
    cpp.line("std::uint16_t EventId() const noexcept")
    cpp.open()
    cpp.line("return static_cast<std::uint16_t>(MessageId() & 0xffff);")
    cpp.close()
    cpp.line()
    cpp.line("/// @brief SOME/IP service ID (upper half of the message ID)")
    cpp.line("std::uint16_t ServiceId() const noexcept")
    cpp.open()
    cpp.line("return static_cast<std::uint16_t>(MessageId() >> 16);")
    cpp.close()
    cpp.line()
    cpp.line("/// @brief Serialized event sample")
    cpp.line("const std::vector<std::uint8_t> &EventPayload() const noexcept")
    cpp.open()
    cpp.line("return mEventPayload;")
    cpp.close()
    cpp.line()
    cpp.line("/// @brief Deserialize a message from a byte vector")
    cpp.line("/// @throws std::out_of_range Throws when the SOME/IP header is truncated")
    cpp.line("static EventMessage Deserialize(")
    cpp.line("    const std::vector<std::uint8_t> &payload)")
    cpp.open()
    cpp.open("if (payload.size() < cHeaderSize)")
    cpp.line('throw std::out_of_range("Truncated SOME/IP header.");')
    cpp.close()
    cpp.line()
    cpp.line("EventMessage _result(0, 1, std::vector<std::uint8_t>());")
    cpp.line("ara::com::someip::SomeIpMessage::Deserialize(&_result, payload);")
    cpp.line("_result.mEventPayload.assign(")
    cpp.line("    payload.cbegin() + cHeaderSize, payload.cend());")
    cpp.line()
    cpp.line("return _result;")
    cpp.close()
    cpp.close(";")


def _method_signature(method: Method) -> str:
    parameters = [f"{argument.data_type.name} {'' if argument.direction == 'IN' else '&'}{argument.name}"
                  for argument in method.arguments]
    return f"{method.name}({', '.join(parameters)})"


def _not_mapped_comment(model: ServiceModel, cpp: _Cpp) -> None:
    for item in model.not_mapped:
        cpp.line(f"/// @note Not mapped (v0): {item}")


def render_skeleton_header(model: ServiceModel, ara_include_prefix: str) -> str:
    """
    Renders the provider side (skeleton) of the service
    """
    includes = ["<cstdint>", "<vector>"]
    if model.events:
        includes.append(f'"{ara_include_prefix}/com/helper/network_layer.h"')
    if model.methods:
        includes.append(f'"{ara_include_prefix}/com/someip/rpc/rpc_server.h"')
    includes.append(f'"./{model.file_stem}_common.h"')
    cpp, _ = _begin_header(model, "skeleton", f"Provider side (skeleton) of {model.name}.", includes)
    class_name = model.name + "Skeleton"
    cpp.open("namespace skeleton")
    if model.events:
        cpp.line("/// @brief Provider side of an event")
        cpp.line("/// @tparam TSample Event sample type")
        cpp.line("template <typename TSample>")
        cpp.open("class Event")
        cpp.access("private")
        cpp.line("ara::com::helper::NetworkLayer<EventMessage> *const mNetworkLayer;")
        cpp.line("const std::uint16_t mEventId;")
        cpp.line("const bool *const mOffered;")
        cpp.line("std::uint16_t mSessionId;")
        cpp.line()
        cpp.access("public")
        cpp.line("using SampleType = TSample;")
        cpp.line()
        cpp.line("Event(")
        cpp.line("    ara::com::helper::NetworkLayer<EventMessage> *networkLayer,")
        cpp.line("    std::uint16_t eventId,")
        cpp.line("    const bool *offered) : mNetworkLayer{networkLayer},")
        cpp.line("                           mEventId{eventId},")
        cpp.line("                           mOffered{offered},")
        cpp.line("                           mSessionId{1}")
        cpp.open()
        cpp.close()
        cpp.line()
        cpp.line("/// @brief Send a sample as a SOME/IP notification")
        cpp.line("/// @returns False if the service is not offered, otherwise true")
        cpp.line("bool Send(const SampleType &sample)")
        cpp.open()
        cpp.open("if (!*mOffered)")
        cpp.line("return false;")
        cpp.close()
        cpp.line()
        cpp.line("std::vector<std::uint8_t> _eventPayload;")
        cpp.line("serialization::Serialize(_eventPayload, sample);")
        cpp.line("EventMessage _message(mEventId, mSessionId, std::move(_eventPayload));")
        cpp.line("mNetworkLayer->Send(_message);")
        cpp.line("_message.IncrementSessionId();")
        cpp.line("mSessionId = _message.SessionId();")
        cpp.line()
        cpp.line("return true;")
        cpp.close()
        cpp.close(";")
        cpp.line()
        cpp.open("namespace events")
        for event in model.events:
            cpp.line(f"/// @brief Classic data element {event.classic_element_ref}")
            cpp.line(f"using {event.name} = Event<{event.data_type.name}>;")
        cpp.close()
        cpp.line()
    cpp.line(f"/// @brief Skeleton of {model.name}")
    cpp.line(f"/// @note Generated from Classic SWC {model.classic_swc_ref}")
    cpp.line("/// @note OfferService only gates the events and methods of this object.")
    cpp.line("///       SOME/IP service discovery is not driven by the generated code.")
    _not_mapped_comment(model, cpp)
    cpp.open(f"class {class_name}")
    cpp.access("private")
    cpp.line("bool mOffered;")
    if model.methods:
        cpp.line("ara::com::someip::rpc::RpcServer *const mRpcServer;")
    for method in model.methods:
        cpp.line()
        cpp.line(f"bool handle{method.name}(")
        cpp.line("    const std::vector<std::uint8_t> &request,")
        cpp.line("    std::vector<std::uint8_t> &response)")
        cpp.open()
        cpp.open("if (!mOffered)")
        cpp.line("return false;")
        cpp.close()
        cpp.line()
        if method.in_arguments:
            cpp.line("std::size_t _offset{0};")
        else:
            cpp.line("static_cast<void>(request);")
        for argument in method.arguments:
            cpp.line(f"{argument.data_type.name} _{argument.name}{{}};")
        for argument in method.in_arguments:
            cpp.open(f"if (!serialization::TryDeserialize(request, _offset, _{argument.name}))")
            cpp.line("return false;")
            cpp.close()
        cpp.line()
        call_arguments = ", ".join(f"_{argument.name}" for argument in method.arguments)
        cpp.line(f"const bool cSuccessful{{{method.name}({call_arguments})}};")
        if method.out_arguments:
            cpp.open("if (cSuccessful)")
            for argument in method.out_arguments:
                cpp.line(f"serialization::Serialize(response, _{argument.name});")
            cpp.close()
        else:
            cpp.line("static_cast<void>(response);")
        cpp.line()
        cpp.line("return cSuccessful;")
        cpp.close()
    cpp.line()
    cpp.access("public")
    for event in model.events:
        cpp.line(f"/// @brief Event of Classic port {event.classic_port_ref}")
        cpp.line(f"events::{event.name} {event.name};")
    if model.events:
        cpp.line()
    parameters = []
    if model.events:
        cpp.line("/// @param eventNetworkLayer Transport of the event notifications")
        parameters.append("ara::com::helper::NetworkLayer<EventMessage> *eventNetworkLayer")
    if model.methods:
        cpp.line("/// @param rpcServer RPC server that dispatches the method requests")
        parameters.append("ara::com::someip::rpc::RpcServer *rpcServer")
    initializers = ["mOffered{false}"]
    if model.methods:
        initializers.append("mRpcServer{rpcServer}")
    initializers += [f"{event.name}(eventNetworkLayer, c{event.name}EventId, &mOffered)" for event in model.events]
    cpp.line(f"{'explicit ' if len(parameters) == 1 else ''}{class_name}(")
    for index, parameter in enumerate(parameters):
        cpp.line(f"    {parameter}{',' if index + 1 < len(parameters) else ')'}")
    for index, initializer in enumerate(initializers):
        cpp.line(f"    {':' if index == 0 else ' '} {initializer}{',' if index + 1 < len(initializers) else ''}")
    cpp.open()
    for method in model.methods:
        cpp.line("mRpcServer->SetHandler(")
        cpp.line(f"    cServiceId, c{method.name}MethodId,")
        cpp.line("    [this](const std::vector<std::uint8_t> &request,")
        cpp.line("           std::vector<std::uint8_t> &response)")
        cpp.line("    {")
        cpp.line(f"        return handle{method.name}(request, response);")
        cpp.line("    });")
    cpp.close()
    cpp.line()
    cpp.line(f"{class_name}(const {class_name} &) = delete;")
    cpp.line(f"{class_name} &operator=(const {class_name} &) = delete;")
    if model.methods:
        cpp.line()
        cpp.line(f"virtual ~{class_name}()")
        cpp.open()
        cpp.line("// The RPC server has no handler removal; replace them with rejections.")
        for method in model.methods:
            cpp.line("mRpcServer->SetHandler(")
            cpp.line(f"    cServiceId, c{method.name}MethodId,")
            cpp.line("    [](const std::vector<std::uint8_t> &,")
            cpp.line("       std::vector<std::uint8_t> &)")
            cpp.line("    {")
            cpp.line("        return false;")
            cpp.line("    });")
        cpp.close()
    else:
        cpp.line(f"virtual ~{class_name}() noexcept = default;")
    cpp.line()
    cpp.line("/// @brief Enable the events and the methods of the service")
    cpp.line("void OfferService() noexcept")
    cpp.open()
    cpp.line("mOffered = true;")
    cpp.close()
    cpp.line()
    cpp.line("/// @brief Disable the events and the methods of the service")
    cpp.line("void StopOfferService() noexcept")
    cpp.open()
    cpp.line("mOffered = false;")
    cpp.close()
    cpp.line()
    cpp.line("/// @brief Indicate whether the service is offered")
    cpp.line("bool IsOffered() const noexcept")
    cpp.open()
    cpp.line("return mOffered;")
    cpp.close()
    for method in model.methods:
        cpp.line()
        cpp.line(f"/// @brief Classic operation {method.classic_operation_ref}")
        cpp.line("/// @returns True if the call is handled; false is reported as E_NOT_OK")
        cpp.line(f"virtual bool {_method_signature(method)} = 0;")
    cpp.close(";")
    cpp.close()
    return _end_header(model, cpp)


def render_proxy_header(model: ServiceModel, ara_include_prefix: str) -> str:
    """
    Renders the consumer side (proxy) of the service
    """
    includes = ["<cstdint>", "<functional>", "<vector>"]
    if model.events:
        includes.append(f'"{ara_include_prefix}/com/helper/network_layer.h"')
    if model.methods:
        includes.append(f'"{ara_include_prefix}/com/someip/rpc/rpc_client.h"')
    includes.append(f'"./{model.file_stem}_common.h"')
    cpp, _ = _begin_header(model, "proxy", f"Consumer side (proxy) of {model.name}.", includes)
    class_name = model.name + "Proxy"
    cpp.open("namespace proxy")
    if model.events:
        cpp.line("/// @brief Consumer side of an event")
        cpp.line("/// @tparam TSample Event sample type")
        cpp.line("template <typename TSample>")
        cpp.open("class Event")
        cpp.access("private")
        cpp.line("const std::uint16_t mEventId;")
        cpp.line("bool mSubscribed;")
        cpp.line("bool mHasSample;")
        cpp.line("TSample mLastSample;")
        cpp.line("std::function<void(const TSample &)> mReceiveHandler;")
        cpp.line()
        cpp.access("public")
        cpp.line("using SampleType = TSample;")
        cpp.line()
        cpp.line("explicit Event(std::uint16_t eventId) : mEventId{eventId},")
        cpp.line("                                        mSubscribed{false},")
        cpp.line("                                        mHasSample{false},")
        cpp.line("                                        mLastSample{}")
        cpp.open()
        cpp.close()
        cpp.line()
        cpp.line("/// @brief Start accepting the event notifications")
        cpp.line("/// @note Local filter only; no SOME/IP-SD eventgroup subscription")
        cpp.line("void Subscribe() noexcept")
        cpp.open()
        cpp.line("mSubscribed = true;")
        cpp.close()
        cpp.line()
        cpp.line("/// @brief Stop accepting the event notifications")
        cpp.line("void Unsubscribe() noexcept")
        cpp.open()
        cpp.line("mSubscribed = false;")
        cpp.line("mHasSample = false;")
        cpp.close()
        cpp.line()
        cpp.line("bool IsSubscribed() const noexcept")
        cpp.open()
        cpp.line("return mSubscribed;")
        cpp.close()
        cpp.line()
        cpp.line("/// @brief Set a callback to be invoked on each received sample")
        cpp.line("void SetReceiveHandler(std::function<void(const SampleType &)> handler)")
        cpp.open()
        cpp.line("mReceiveHandler = std::move(handler);")
        cpp.close()
        cpp.line()
        cpp.line("void UnsetReceiveHandler()")
        cpp.open()
        cpp.line("mReceiveHandler = nullptr;")
        cpp.close()
        cpp.line()
        cpp.line("/// @brief Try to get the last received sample")
        cpp.line("/// @returns False if no sample is received since the subscription")
        cpp.line("bool TryGetLastSample(SampleType &sample) const")
        cpp.open()
        cpp.open("if (mHasSample)")
        cpp.line("sample = mLastSample;")
        cpp.close()
        cpp.line()
        cpp.line("return mHasSample;")
        cpp.close()
        cpp.line()
        cpp.line("/// @brief Process a notification received by the proxy")
        cpp.line("/// @returns True if the notification is consumed by this event")
        cpp.line("bool Process(const EventMessage &message)")
        cpp.open()
        cpp.line("if (!mSubscribed ||")
        cpp.line("    message.ServiceId() != cServiceId ||")
        cpp.line("    message.EventId() != mEventId ||")
        cpp.line("    message.ProtocolVersion() != cProtocolVersion ||")
        cpp.line("    message.InterfaceVersion() != cMajorVersion ||")
        cpp.line("    message.MessageType() !=")
        cpp.line("        ara::com::someip::SomeIpMessageType::Notification)")
        cpp.open()
        cpp.line("return false;")
        cpp.close()
        cpp.line()
        cpp.line("std::size_t _offset{0};")
        cpp.line("SampleType _sample{};")
        cpp.line("if (!serialization::TryDeserialize(")
        cpp.line("        message.EventPayload(), _offset, _sample))")
        cpp.open()
        cpp.line("return false;")
        cpp.close()
        cpp.line()
        cpp.line("mLastSample = _sample;")
        cpp.line("mHasSample = true;")
        cpp.open("if (mReceiveHandler)")
        cpp.line("mReceiveHandler(mLastSample);")
        cpp.close()
        cpp.line()
        cpp.line("return true;")
        cpp.close()
        cpp.close(";")
        cpp.line()
        cpp.open("namespace events")
        for event in model.events:
            cpp.line(f"/// @brief Classic data element {event.classic_element_ref}")
            cpp.line(f"using {event.name} = Event<{event.data_type.name}>;")
        cpp.close()
        cpp.line()
    cpp.line(f"/// @brief Proxy of {model.name}")
    cpp.line(f"/// @note Generated from Classic SWC {model.classic_swc_ref}")
    cpp.line("/// @note No service discovery: the proxy is bound to the given transports.")
    if model.methods:
        cpp.line("/// @note Methods report their result via a callback (no ara::core::Future).")
    cpp.open(f"class {class_name}")
    cpp.access("private")
    if model.events:
        cpp.line("ara::com::helper::NetworkLayer<EventMessage> *const mEventNetworkLayer;")
    if model.methods:
        cpp.line("ara::com::someip::rpc::RpcClient *const mRpcClient;")
        cpp.line("const std::uint16_t mClientId;")
    cpp.line()
    cpp.access("public")
    for event in model.events:
        cpp.line(f"/// @brief Event of Classic port {event.classic_port_ref}")
        cpp.line(f"events::{event.name} {event.name};")
    for method in model.methods:
        handler_arguments = ", ".join(["bool"] + [argument.data_type.name for argument in method.out_arguments])
        cpp.line(f"/// @brief Response callback of {method.name}: success flag, then the OUT arguments")
        cpp.line(f"using {method.name}Handler = std::function<void({handler_arguments})>;")
    cpp.line()
    parameters = []
    initializers = []
    if model.events:
        cpp.line("/// @param eventNetworkLayer Transport of the event notifications")
        parameters.append("ara::com::helper::NetworkLayer<EventMessage> *eventNetworkLayer")
        initializers.append("mEventNetworkLayer{eventNetworkLayer}")
    if model.methods:
        cpp.line("/// @param rpcClient RPC client that sends the method requests")
        cpp.line("/// @param clientId SOME/IP client ID of this proxy")
        parameters.append("ara::com::someip::rpc::RpcClient *rpcClient")
        parameters.append("std::uint16_t clientId")
        initializers.append("mRpcClient{rpcClient}")
        initializers.append("mClientId{clientId}")
    initializers += [f"{event.name}(c{event.name}EventId)" for event in model.events]
    cpp.line(f"{'explicit ' if len(parameters) == 1 else ''}{class_name}(")
    for index, parameter in enumerate(parameters):
        cpp.line(f"    {parameter}{',' if index + 1 < len(parameters) else ')'}")
    for index, initializer in enumerate(initializers):
        cpp.line(f"    {':' if index == 0 else ' '} {initializer}{',' if index + 1 < len(initializers) else ''}")
    cpp.open()
    if model.events:
        cpp.line("mEventNetworkLayer->SetReceiver(")
        cpp.line("    this,")
        cpp.line("    [this](EventMessage message)")
        cpp.line("    {")
        for event in model.events:
            cpp.line(f"        {event.name}.Process(message);")
        cpp.line("    });")
    cpp.close()
    cpp.line()
    cpp.line(f"{class_name}(const {class_name} &) = delete;")
    cpp.line(f"{class_name} &operator=(const {class_name} &) = delete;")
    cpp.line()
    if model.events:
        cpp.line(f"~{class_name}()")
        cpp.open()
        cpp.line("// The network layer has no receiver removal; replace it with a no-op.")
        cpp.line("mEventNetworkLayer->SetReceiver(this, [](EventMessage) {});")
        cpp.close()
    else:
        cpp.line(f"~{class_name}() noexcept = default;")
    for method in model.methods:
        cpp.line()
        cpp.line(f"/// @brief Classic operation {method.classic_operation_ref}")
        parameters = [f"{argument.data_type.name} {argument.name}" for argument in method.in_arguments]
        parameters.append(f"{method.name}Handler responseHandler")
        cpp.line(f"void {method.name}({', '.join(parameters)})")
        cpp.open()
        cpp.line("std::vector<std::uint8_t> _request;")
        for argument in method.in_arguments:
            cpp.line(f"serialization::Serialize(_request, {argument.name});")
        cpp.line()
        cpp.line("mRpcClient->SetHandler(")
        cpp.line(f"    cServiceId, c{method.name}MethodId,")
        cpp.line("    [responseHandler](")
        cpp.line("        const ara::com::someip::rpc::SomeIpRpcMessage &message)")
        cpp.line("    {")
        cpp.level += 2
        cpp.line("bool _successful{")
        cpp.line("    message.MessageType() ==")
        cpp.line("        ara::com::someip::SomeIpMessageType::Response &&")
        cpp.line("    message.ReturnCode() ==")
        cpp.line("        ara::com::someip::SomeIpReturnCode::eOK};")
        if method.out_arguments:
            cpp.line("std::size_t _offset{0};")
        for argument in method.out_arguments:
            cpp.line(f"{argument.data_type.name} _{argument.name}{{}};")
            cpp.line("_successful =")
            cpp.line("    _successful &&")
            cpp.line("    serialization::TryDeserialize(")
            cpp.line(f"        message.RpcPayload(), _offset, _{argument.name});")
        call_arguments = ", ".join(["_successful"] + [f"_{argument.name}" for argument in method.out_arguments])
        cpp.line(f"responseHandler({call_arguments});")
        cpp.level -= 2
        cpp.line("    });")
        cpp.line("mRpcClient->Send(")
        cpp.line(f"    cServiceId, c{method.name}MethodId, mClientId, _request);")
        cpp.close()
    cpp.close(";")
    cpp.close()
    return _end_header(model, cpp)


def render_all(model: ServiceModel, ara_include_prefix: str = "../../ara") -> dict[str, str]:
    """
    Renders all output files. Returns file name -> content, in a stable order.
    """
    stem = model.file_stem
    return {
        f"{stem}.arxml": render_arxml(model),
        f"{stem}_types.h": render_types_header(model),
        f"{stem}_common.h": render_common_header(model, ara_include_prefix),
        f"{stem}_skeleton.h": render_skeleton_header(model, ara_include_prefix),
        f"{stem}_proxy.h": render_proxy_header(model, ara_include_prefix),
    }


def write_files(files: dict[str, str], out_dir: str) -> list[str]:
    """
    Writes the rendered files as UTF-8 with LF line endings. Returns the written paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for file_name, content in files.items():
        path = os.path.join(out_dir, file_name)
        with open(path, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
        paths.append(path)
    return paths
