# Classic-to-Adaptive bridge (v0 prototype)

> **Prototype, not a certified toolchain.** The output is for demonstration and discussion only.
> It is not qualified (ISO 26262 or otherwise), not validated against the AUTOSAR XSD and not a
> complete `ara::com` binding. Do not use it for production or safety-related software.

`classic_to_adaptive.py` reads a Classic AUTOSAR SWC with `autosar.xml.Reader` and generates, for the
[COG-GTM/Adaptive-AUTOSAR](https://github.com/COG-GTM/Adaptive-AUTOSAR) simulator:

| File | Content |
| --- | --- |
| `<service>.arxml` | Adaptive `SERVICE-INTERFACE`, its C++ data types and a `SOMEIP-SERVICE-INTERFACE-DEPLOYMENT` |
| `<service>_types.h` | C++ aliases of the ImplementationDataTypes |
| `<service>_common.h` | SOME/IP IDs, big-endian payload serialization, event notification message |
| `<service>_skeleton.h` | Provider side: `<Service>Skeleton` |
| `<service>_proxy.h` | Consumer side: `<Service>Proxy` |

The mapping logic lives in [`src/autosar/generator/adaptive_bridge.py`](../../../src/autosar/generator/adaptive_bridge.py),
its unit tests in [`tests/generator/test_adaptive_bridge.py`](../../../tests/generator/test_adaptive_bridge.py).

## Mapping rules (v0)

| Classic | Adaptive |
| --- | --- |
| SWC | One ServiceInterface `<SWC>Service`, namespace `generated::<swcservice>` |
| Provided sender-receiver port / data element | Event (IDs from `0x8001`, in port order; one event group `1`) |
| Provided client-server port / operation | Method (IDs from `0x0001`, in port order); `IN`/`INOUT` arguments in the request, `OUT`/`INOUT` in the response |
| ImplementationDataType, category `VALUE` | `using <Name> = <fixed width type>;` from the size and encoding of its SwBaseType |
| ImplementationDataType, category `TYPE_REFERENCE` | `using <Name> = <ReferencedName>;` |

An event or method takes the name of its data element or operation; if that is not unique in the
service it becomes `<Port>_<Element>`.

## Usage

```bash
# Demo 1 SWC (examples/template/generated/WheelSpeedSensor.arxml) -> generated/wheel_speed_sensor_service/
python examples/generator/adaptive/classic_to_adaptive.py

# Another SWC with its own inputs, service ID and output directory
G=examples/template/generated
python examples/generator/adaptive/classic_to_adaptive.py --swc TimerComponent --service-id 0x1001 \
    $G/AUTOSAR_Platform.arxml $G/PortInterfaces.arxml $G/TimerComponent.arxml
```

The output is deterministic: no timestamps, absolute paths or UUIDs, and the order follows the input
ARXML. The committed `generated/` directory is compared against a fresh run by the unit tests.

- `generated/wheel_speed_sensor_service/`: the WheelSpeedSensor SWC (sender-receiver -> event).
- `generated/timer_component_service/`: the TimerComponent SWC of the same example, kept as a second
  fixture because WheelSpeedSensor has no client-server port (client-server -> method).

The headers include the Adaptive-AUTOSAR sources relative to `src/generated/<service>/` of that
repository (`--ara-include-prefix`, default `../../ara`).

## Limitations

- Only provided ports are mapped. Require ports, mode-switch, parameter and NV-data interfaces are
  skipped and listed as "not mapped" in the console output and in the generated skeleton.
- Only `VALUE` and `TYPE_REFERENCE` ImplementationDataTypes are supported; arrays, records and
  ApplicationDataTypes stop the generator with an error.
- CompuMethods, data constraints, units, init values and end-to-end protection are not carried over:
  events and methods transport the raw internal value.
- Possible errors of client-server operations are not mapped; a method reports only success or failure.
- No fields, no queued/unqueued semantics, no timing (the Classic runnable period is ignored).
- SOME/IP IDs are assigned by position, not taken from a system description. Adding a port renumbers
  the following events or methods.
- The ARXML is written by a small emitter in the bridge (this library has no Adaptive elements). Its
  structure follows the Adaptive manifest element names but is **not validated against the XSD** and
  cannot be read back with `autosar.xml.Reader`.
- The C++ API is `ara::com`-like, not `ara::com`: no `FindService`, no `ara::core::Future` (methods
  take a callback), `Subscribe` and `OfferService` are local switches and do not drive SOME/IP-SD.
