import pytest

from nasagent.nas.adapters.ugreen.adapter import UgreenNasAdapter
from nasagent.nas.adapters.ugreen.client import UgreenClient
from nasagent.nas.adapters.ugreen.errors import UnsupportedUgreenOperation


@pytest.mark.asyncio
async def test_ugreen_adapter_fails_explicitly_for_unknown_endpoints() -> None:
    adapter = UgreenNasAdapter(client=UgreenClient(base_url="https://nas.local"))

    with pytest.raises(UnsupportedUgreenOperation, match="get_storage_status"):
        await adapter.get_storage_status()
