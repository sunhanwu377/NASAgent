from nasagent.nas.adapters.ugreen.client import UgreenClient
from nasagent.nas.adapters.ugreen.errors import UnsupportedUgreenOperation
from nasagent.nas.models import DeviceStatus, NasFile, StorageStatus


class UgreenNasAdapter:
    def __init__(self, client: UgreenClient) -> None:
        self._client = client

    async def authenticate(self) -> None:
        raise UnsupportedUgreenOperation("authenticate requires verified UGREEN API details")

    async def get_device_status(self) -> DeviceStatus:
        raise UnsupportedUgreenOperation("get_device_status requires verified UGREEN API details")

    async def get_storage_status(self) -> StorageStatus:
        raise UnsupportedUgreenOperation("get_storage_status requires verified UGREEN API details")

    async def list_files(self, path: str) -> list[NasFile]:
        raise UnsupportedUgreenOperation("list_files requires verified UGREEN API details")

    async def search_files(self, query: str, path: str | None = None) -> list[NasFile]:
        raise UnsupportedUgreenOperation("search_files requires verified UGREEN API details")

    async def upload_file(self, local_path: str, remote_path: str) -> NasFile:
        raise UnsupportedUgreenOperation("upload_file requires verified UGREEN API details")

    async def download_file(self, remote_path: str, local_path: str) -> NasFile:
        raise UnsupportedUgreenOperation("download_file requires verified UGREEN API details")

    async def delete_file(self, path: str) -> None:
        raise UnsupportedUgreenOperation("delete_file requires verified UGREEN API details")
