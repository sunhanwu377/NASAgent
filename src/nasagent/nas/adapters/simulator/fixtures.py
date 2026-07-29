from nasagent.nas.models import DeviceStatus, NasFile, StorageStatus


def default_files() -> dict[str, list[NasFile]]:
    return {
        "/downloads": [
            NasFile(path="/downloads/movie.iso", name="movie.iso", size_bytes=4_700_000_000),
            NasFile(path="/downloads/photos.zip", name="photos.zip", size_bytes=950_000_000),
        ],
        "/": [
            NasFile(path="/downloads", name="downloads", size_bytes=0, is_dir=True),
        ],
    }


def default_device_status() -> DeviceStatus:
    return DeviceStatus(
        name="simulator",
        model="NASAgent Simulator",
        firmware_version="0.1.0",
        uptime_seconds=12345,
    )


def default_storage_status() -> StorageStatus:
    return StorageStatus(
        total_bytes=8_000_000_000_000,
        used_bytes=5_100_000_000_000,
        free_bytes=2_900_000_000_000,
    )
