from nasagent.nas.adapters.simulator.fixtures import (
    default_device_status,
    default_files,
    default_storage_status,
)
from nasagent.nas.models import DeviceStatus, NasFile, StorageStatus


class SimulatorNasAdapter:
    def __init__(self) -> None:
        self._files = default_files()

    async def authenticate(self) -> None:
        return None

    async def get_device_status(self) -> DeviceStatus:
        return default_device_status()

    async def get_storage_status(self) -> StorageStatus:
        return default_storage_status()

    async def list_files(self, path: str) -> list[NasFile]:
        return list(self._files.get(path, []))

    async def search_files(self, query: str, path: str | None = None) -> list[NasFile]:
        roots = [path] if path is not None else list(self._files)
        results: list[NasFile] = []
        for root in roots:
            for file in self._files.get(root, []):
                if query.lower() in file.name.lower():
                    results.append(file)
        return results

    async def upload_file(self, local_path: str, remote_path: str) -> NasFile:
        name = remote_path.rstrip("/").split("/")[-1]
        parent = remote_path.rsplit("/", 1)[0] or "/"
        file = NasFile(path=remote_path, name=name, size_bytes=0)
        self._files.setdefault(parent, []).append(file)
        return file

    async def download_file(self, remote_path: str, local_path: str) -> NasFile:
        for files in self._files.values():
            for file in files:
                if file.path == remote_path:
                    return file
        name = remote_path.rstrip("/").split("/")[-1]
        return NasFile(path=remote_path, name=name, size_bytes=0)

    async def delete_file(self, path: str) -> None:
        for root, files in list(self._files.items()):
            self._files[root] = [file for file in files if file.path != path]
