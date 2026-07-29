import pytest

from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter


@pytest.mark.asyncio
async def test_simulator_returns_storage_status() -> None:
    adapter = SimulatorNasAdapter()

    status = await adapter.get_storage_status()

    assert status.total_bytes == 8_000_000_000_000
    assert status.used_bytes == 5_100_000_000_000
    assert status.free_bytes == 2_900_000_000_000


@pytest.mark.asyncio
async def test_simulator_lists_files() -> None:
    adapter = SimulatorNasAdapter()

    files = await adapter.list_files("/downloads")

    assert [file.name for file in files] == ["movie.iso", "photos.zip"]


@pytest.mark.asyncio
async def test_simulator_deletes_file() -> None:
    adapter = SimulatorNasAdapter()

    await adapter.delete_file("/downloads/movie.iso")

    files = await adapter.list_files("/downloads")
    assert [file.name for file in files] == ["photos.zip"]
