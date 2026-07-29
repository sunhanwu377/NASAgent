import pytest

from nasagent.discovery.models import ProbeHttpResponse
from nasagent.discovery.vendors.base import VendorProbeRegistry
from nasagent.discovery.vendors.generic import GenericNasProbe
from nasagent.discovery.vendors.ugreen import UgreenProbe


def test_ugreen_probe_targets_vendor_ports() -> None:
    probe = UgreenProbe()
    targets = probe.targets("192.168.1.2")

    flattened = {(target.schemes, target.ports) for target in targets}
    assert (("http",), (9999,)) in flattened
    assert (("https",), (9443,)) in flattened


@pytest.mark.asyncio
async def test_ugreen_probe_matches_login_page() -> None:
    probe = UgreenProbe()
    response = ProbeHttpResponse(
        url="https://192.168.1.2:9443/",
        status_code=200,
        headers={"server": "ugreen"},
        text="UGREEN NAS login",
    )

    result = await probe.match(response)

    assert result is not None
    assert result.vendor == "ugreen"
    assert result.confidence >= 0.8


def test_vendor_registry_registers_default_probes() -> None:
    registry = VendorProbeRegistry.default()
    vendors = {probe.vendor for probe in registry.list()}

    assert {"ugreen", "synology", "fnos", "zspace", "generic"}.issubset(vendors)


@pytest.mark.asyncio
async def test_generic_probe_uses_word_boundary_for_nas() -> None:
    probe = GenericNasProbe()
    response = ProbeHttpResponse(
        url="http://192.168.1.2/",
        status_code=200,
        headers={},
        text="bananas service dashboard",
    )

    assert await probe.match(response) is None


@pytest.mark.asyncio
async def test_generic_probe_matches_nas_word() -> None:
    probe = GenericNasProbe()
    response = ProbeHttpResponse(
        url="http://192.168.1.2/",
        status_code=200,
        headers={},
        text="NAS admin dashboard",
    )

    result = await probe.match(response)

    assert result is not None
    assert result.vendor == "generic"
