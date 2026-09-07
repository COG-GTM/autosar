"""
Architecture diagram generation.

The diagram is derived from the workspace model (component prototypes, ports,
port interfaces and connectors), never hand-written, so it cannot drift away
from the generated ARXML.
"""

import os
import shutil
import subprocess
from itertools import zip_longest
import autosar.xml.element as ar_element
import autosar.xml.workspace as ar_workspace

INTERFACE_KIND = {ar_element.SenderReceiverInterface: ("SR", "#e8f0fb"),
                  ar_element.ClientServerInterface: ("CS", "#fdf0e0"),
                  ar_element.ModeSwitchInterface: ("MS", "#eaf6ea")}
DEFAULT_KIND = ("PI", "#f0f0f0")


def _short_name(ref) -> str:
    return str(ref).rpartition("/")[2]


def _port_info(workspace: ar_workspace.Workspace, port: ar_element.PortPrototype) -> tuple[str, str, str]:
    """
    Returns (interface name, interface kind, background color) of a port
    """
    interface_name = _short_name(port.port_interface_ref)
    port_interface = workspace.find(str(port.port_interface_ref))
    kind, color = INTERFACE_KIND.get(type(port_interface), DEFAULT_KIND)
    return interface_name, kind, color


def _port_cell(workspace: ar_workspace.Workspace,
               port: ar_element.PortPrototype | None,
               is_provide_port: bool) -> str:
    if port is None:
        return '<TD BORDER="0"></TD>'
    interface_name, kind, color = _port_info(workspace, port)
    marker = "&#9654;" if is_provide_port else "&#9655;"
    prefix = "p_" if is_provide_port else "r_"
    text = f"{port.name} : {interface_name} [{kind}]"
    if is_provide_port:
        content = f"{text} {marker}"
        align = "RIGHT"
    else:
        content = f"{marker} {text}"
        align = "LEFT"
    return (f'<TD PORT="{prefix}{port.name}" ALIGN="{align}" BGCOLOR="{color}" '
            f'BORDER="1" STYLE="ROUNDED"><FONT POINT-SIZE="11">{content}</FONT></TD>')


def _component_node(workspace: ar_workspace.Workspace,
                    node_id: str,
                    title: str,
                    subtitle: str,
                    component: ar_element.SwComponentType) -> str:
    require_ports = list(component.require_ports)
    provide_ports = list(component.provide_ports)
    rows = [f'<TR><TD COLSPAN="2" BORDER="0"><B><FONT POINT-SIZE="15">{title}</FONT></B>'
            f'<BR/><FONT POINT-SIZE="10" COLOR="#555555">{subtitle}</FONT></TD></TR>']
    for require_port, provide_port in zip_longest(require_ports, provide_ports):
        require_cell = _port_cell(workspace, require_port, False)
        provide_cell = _port_cell(workspace, provide_port, True)
        rows.append(f"<TR>{require_cell}{provide_cell}</TR>")
    label = ('<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="6" CELLPADDING="4" '
             'BGCOLOR="white" STYLE="ROUNDED">' + "".join(rows) + "</TABLE>>")
    return f'  "{node_id}" [label={label}];'


def _outer_port_node(workspace: ar_workspace.Workspace,
                     port: ar_element.PortPrototype,
                     is_provide_port: bool) -> str:
    interface_name, kind, color = _port_info(workspace, port)
    label = f"{port.name}\\n{interface_name} [{kind}]"
    shape = "cds" if is_provide_port else "rarrow"
    return (f'    "outer_{port.name}" [label="{label}", shape={shape}, style="filled", '
            f'fillcolor="{color}", fontsize=11, margin="0.16,0.08"];')


def create_dot(workspace: ar_workspace.Workspace,
               composition: ar_element.CompositionSwComponentType) -> str:
    """
    Creates a Graphviz DOT description of the given composition
    """
    lines = ["digraph AccArchitecture {",
             '  graph [rankdir=LR, splines=spline, nodesep=0.6, ranksep=1.4, '
             f'fontname="Helvetica", label="{composition.name}", labelloc=t, fontsize=22];',
             '  node [shape=plaintext, fontname="Helvetica"];',
             '  edge [fontname="Helvetica", fontsize=10, color="#444444"];']
    inner_components: dict[str, ar_element.SwComponentType] = {}
    for prototype in composition.components:
        component = workspace.find(str(prototype.type_ref))
        inner_components[prototype.name] = component
        lines.append(_component_node(workspace,
                                     prototype.name,
                                     prototype.name,
                                     type(component).__name__,
                                     component))
    lines.append('  subgraph cluster_inputs {\n    label=""; style=invis;')
    for port in composition.require_ports:
        lines.append(_outer_port_node(workspace, port, False))
    lines.append("  }")
    lines.append('  subgraph cluster_outputs {\n    label=""; style=invis;')
    for port in composition.provide_ports:
        lines.append(_outer_port_node(workspace, port, True))
    lines.append("  }")
    for connector in composition.connectors:
        if isinstance(connector, ar_element.AssemblySwConnector):
            source = f'"{_short_name(connector.provide_port.component_ref)}"' \
                     f':p_{_short_name(connector.provide_port.port_ref)}'
            target = f'"{_short_name(connector.require_port.component_ref)}"' \
                     f':r_{_short_name(connector.require_port.port_ref)}'
            interface_name = _short_name(
                inner_components[_short_name(connector.provide_port.component_ref)].find(
                    _short_name(connector.provide_port.port_ref)).port_interface_ref)
            lines.append(f'  {source} -> {target} [label="{interface_name}", penwidth=1.6];')
        elif isinstance(connector, ar_element.DelegationSwConnector):
            outer_name = _short_name(connector.outer_port)
            inner_component = _short_name(connector.inner_port.component_ref)
            inner_port = _short_name(connector.inner_port.port_ref)
            if connector.inner_port.port_ref.is_provide_port_ref:
                source = f'"{inner_component}":p_{inner_port}'
                target = f'"outer_{outer_name}"'
            else:
                source = f'"outer_{outer_name}"'
                target = f'"{inner_component}":r_{inner_port}'
            lines.append(f'  {source} -> {target} [style=dashed, arrowhead=vee];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render(dot_source: str, output_base_path: str, formats: tuple[str, ...] = ("svg", "png")) -> list[str]:
    """
    Writes the DOT source next to the rendered images and returns all written paths.

    Rendering is skipped (with a warning) when Graphviz is not installed.
    """
    written = [output_base_path + ".dot"]
    with open(written[0], "w", encoding="utf-8") as file:
        file.write(dot_source)
    dot_executable = shutil.which("dot")
    if dot_executable is None:
        print("Warning: Graphviz 'dot' not found, only the DOT file was written")
        return written
    for output_format in formats:
        output_path = f"{output_base_path}.{output_format}"
        subprocess.run([dot_executable, f"-T{output_format}", written[0], "-o", output_path], check=True)
        written.append(output_path)
    return written


def create_diagram(workspace: ar_workspace.Workspace,
                   composition_ref: str,
                   output_base_path: str) -> list[str]:
    """
    Creates the architecture diagram of the composition found at composition_ref
    """
    composition = workspace.find(composition_ref)
    if not isinstance(composition, ar_element.CompositionSwComponentType):
        raise ValueError(f"{composition_ref}: Not a composition component")
    os.makedirs(os.path.dirname(output_base_path), exist_ok=True)
    return render(create_dot(workspace, composition), output_base_path)
