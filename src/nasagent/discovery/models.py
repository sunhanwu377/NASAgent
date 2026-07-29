from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveredService:
    host: str
    port: int
    scheme: str
    service_type: str
    name: str | None
    source: str
    confidence: float
    login_url: str | None
    admin_url: str | None


@dataclass(frozen=True)
class ProbeTarget:
    host: str
    ports: tuple[int, ...]
    schemes: tuple[str, ...]
    paths: tuple[str, ...] = ("/",)


@dataclass(frozen=True)
class ProbeHttpResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    text: str


@dataclass(frozen=True)
class VendorProbeResult:
    vendor: str
    service_type: str
    admin_url: str | None
    login_url: str | None
    confidence: float
    evidence: dict[str, str]
