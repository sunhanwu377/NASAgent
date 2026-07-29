from typing import Protocol

from nasagent.nas.models import DeviceStatus, NasFile, StorageStatus


class NasAdapter(Protocol):
    async def authenticate(self) -> None:
        raise NotImplementedError

    async def get_device_status(self) -> DeviceStatus:
        raise NotImplementedError

    async def get_storage_status(self) -> StorageStatus:
        raise NotImplementedError

    async def list_files(self, path: str) -> list[NasFile]:
        raise NotImplementedError

    async def search_files(self, query: str, path: str | None = None) -> list[NasFile]:
        raise NotImplementedError

    async def upload_file(self, local_path: str, remote_path: str) -> NasFile:
        raise NotImplementedError

    async def download_file(self, remote_path: str, local_path: str) -> NasFile:
        raise NotImplementedError

    async def delete_file(self, path: str) -> None:
        raise NotImplementedError
