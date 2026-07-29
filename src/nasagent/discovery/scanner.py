from dataclasses import dataclass

from nasagent.discovery.models import DiscoveredService, ProbeHttpResponse
from nasagent.discovery.protocols import discover_mdns_services, discover_ssdp_services
from nasagent.discovery.vendors.base import VendorProbeRegistry


@dataclass(frozen=True)
class DiscoveryOptions:
    timeout_seconds: float = 0.5
    concurrency: int = 32
    ports: tuple[int, ...] = (80, 443, 5000, 5001, 5244, 16601)


class DiscoveryScanner:
    def __init__(
        self,
        *,
        options: DiscoveryOptions | None = None,
        vendors: VendorProbeRegistry | None = None,
    ) -> None:
        self.options = options or DiscoveryOptions()
        self.vendors = vendors or VendorProbeRegistry.default()

    async def scan_hosts(self, hosts: list[str]) -> list[DiscoveredService]:
        del hosts
        services = [*await discover_mdns_services(), *await discover_ssdp_services()]
        return self.deduplicate(services)

    async def match_vendor_response(
        self, host: str, port: int, scheme: str, response: ProbeHttpResponse
    ) -> DiscoveredService | None:
        for probe in self.vendors.list():
            result = await probe.match(response)
            if result is None:
                continue
            return DiscoveredService(
                host=host,
                port=port,
                scheme=scheme,
                service_type=result.service_type,
                name=result.vendor,
                source="vendor",
                confidence=result.confidence,
                login_url=result.login_url,
                admin_url=result.admin_url,
            )
        return None

    def deduplicate(self, services: list[DiscoveredService]) -> list[DiscoveredService]:
        best: dict[tuple[str, int, str, str], DiscoveredService] = {}
        for service in services:
            key = (service.host, service.port, service.scheme, service.service_type)
            current = best.get(key)
            if current is None or service.confidence > current.confidence:
                best[key] = service
        return list(best.values())
