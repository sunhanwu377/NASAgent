from typing import Protocol

from nasagent.discovery.models import ProbeHttpResponse, ProbeTarget, VendorProbeResult


class VendorProbe(Protocol):
    vendor: str

    def targets(self, host: str) -> list[ProbeTarget]: ...

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None: ...


class VendorProbeRegistry:
    def __init__(self) -> None:
        self._probes: list[VendorProbe] = []

    def register(self, probe: VendorProbe) -> None:
        self._probes.append(probe)

    def list(self) -> list[VendorProbe]:
        return list(self._probes)

    @classmethod
    def default(cls) -> "VendorProbeRegistry":
        from nasagent.discovery.vendors.fnos import FnosProbe
        from nasagent.discovery.vendors.generic import GenericNasProbe
        from nasagent.discovery.vendors.synology import SynologyProbe
        from nasagent.discovery.vendors.ugreen import UgreenProbe
        from nasagent.discovery.vendors.zspace import ZspaceProbe

        registry = cls()
        registry.register(UgreenProbe())
        registry.register(SynologyProbe())
        registry.register(FnosProbe())
        registry.register(ZspaceProbe())
        registry.register(GenericNasProbe())
        return registry
