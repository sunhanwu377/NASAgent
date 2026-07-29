from pydantic import BaseModel


class NasFile(BaseModel):
    path: str
    name: str
    size_bytes: int
    is_dir: bool = False


class DeviceStatus(BaseModel):
    name: str
    model: str
    firmware_version: str
    uptime_seconds: int


class StorageStatus(BaseModel):
    total_bytes: int
    used_bytes: int
    free_bytes: int
