from dataclasses import dataclass

import httpx

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
        services = [*await discover_mdns_services(), *await discover_ssdp_services()]
        services.extend(await self._scan_explicit_hosts(hosts))
        return self.deduplicate(services)

    async def _scan_explicit_hosts(self, hosts: list[str]) -> list[DiscoveredService]:
        urls = self._target_urls(hosts)
        services: list[DiscoveredService] = []
        for url in urls:
            response = await self._fetch_response(url)
            if response is None:
                continue
            parsed = httpx.URL(url)
            service = await self.match_vendor_response(
                parsed.host or "",
                parsed.port or self._default_port(parsed.scheme),
                parsed.scheme,
                response,
            )
            if service is not None:
                services.append(service)
        return services

    def _target_urls(self, hosts: list[str]) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        for host in hosts:
            for probe in self.vendors.list():
                for target in probe.targets(host):
                    for scheme in target.schemes:
                        for port in target.ports:
                            for path in target.paths:
                                normalized_path = path if path.startswith("/") else f"/{path}"
                                url = f"{scheme}://{target.host}:{port}{normalized_path}"
                                if url in seen:
                                    continue
                                seen.add(url)
                                urls.append(url)
        return urls

    async def _fetch_response(self, url: str) -> ProbeHttpResponse | None:
        try:
            async with httpx.AsyncClient(timeout=self.options.timeout_seconds) as client:
                response = await client.get(url)
        except httpx.HTTPError:
            return None
        return ProbeHttpResponse(
            url=str(response.url),
            status_code=response.status_code,
            headers=dict(response.headers),
            text=response.text,
        )

    def _default_port(self, scheme: str) -> int:
        if scheme == "https":
            return 443
        return 80

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
