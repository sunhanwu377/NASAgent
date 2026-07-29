from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter
from nasagent.nas.registry import AdapterRegistry


def test_registry_creates_adapter_by_name() -> None:
    registry = AdapterRegistry()
    registry.register("simulator", lambda: SimulatorNasAdapter())

    adapter = registry.create("simulator")

    assert isinstance(adapter, SimulatorNasAdapter)
