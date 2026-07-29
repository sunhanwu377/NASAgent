import pytest

from nasagent.discovery import scanner as scanner_module
from nasagent.discovery.models import DiscoveredService, ProbeHttpResponse
from nasagent.discovery.scanner import DiscoveryOptions, DiscoveryScanner


@pytest.mark.asyncio
async def test_scanner_deduplicates_services() -> None:
    scanner = DiscoveryScanner(options=DiscoveryOptions(timeout_seconds=0.1, concurrency=1))
    services = scanner.deduplicate(
        [
            DiscoveredService(
                "192.168.1.2",
                9443,
                "https",
                "nas_admin",
                "UGREEN",
                "vendor",
                0.9,
                "https://192.168.1.2:9443/",
                "https://192.168.1.2:9443/",
            ),
            DiscoveredService(
                "192.168.1.2",
                9443,
                "https",
                "nas_admin",
                "UGREEN",
                "vendor",
                0.8,
                "https://192.168.1.2:9443/",
                "https://192.168.1.2:9443/",
            ),
        ]
    )

    assert len(services) == 1
    assert services[0].confidence == 0.9


@pytest.mark.asyncio
async def test_scanner_converts_vendor_match_to_discovered_service() -> None:
    scanner = DiscoveryScanner(options=DiscoveryOptions(timeout_seconds=0.1, concurrency=1))
    response = ProbeHttpResponse(
        "https://192.168.1.2:9443/", 200, {"server": "ugreen"}, "UGREEN NAS login"
    )

    service = await scanner.match_vendor_response("192.168.1.2", 9443, "https", response)

    assert service is not None
    assert service.host == "192.168.1.2"
    assert service.port == 9443
    assert service.name == "ugreen"


@pytest.mark.asyncio
async def test_scan_hosts_includes_protocol_discovery(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def fake_mdns_services() -> list[DiscoveredService]:
        return [
            DiscoveredService(
                "nas.local",
                5244,
                "http",
                "alist",
                "AList",
                "mdns",
                0.6,
                "http://nas.local:5244/",
                "http://nas.local:5244/",
            )
        ]

    async def fake_ssdp_services() -> list[DiscoveredService]:
        return []

    monkeypatch.setattr(scanner_module, "discover_mdns_services", fake_mdns_services)
    monkeypatch.setattr(scanner_module, "discover_ssdp_services", fake_ssdp_services)
    scanner = DiscoveryScanner(options=DiscoveryOptions(timeout_seconds=0.1, concurrency=1))

    services = await scanner.scan_hosts([])

    assert len(services) == 1
    assert services[0].source == "mdns"
