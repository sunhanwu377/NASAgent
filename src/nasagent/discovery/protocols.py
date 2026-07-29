from nasagent.discovery.models import DiscoveredService


async def discover_mdns_services() -> list[DiscoveredService]:
    return []


async def discover_ssdp_services() -> list[DiscoveredService]:
    return []
