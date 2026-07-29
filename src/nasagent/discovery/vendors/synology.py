from nasagent.discovery.models import ProbeHttpResponse, ProbeTarget, VendorProbeResult


class SynologyProbe:
    vendor = "synology"

    def targets(self, host: str) -> list[ProbeTarget]:
        return [
            ProbeTarget(host=host, ports=(5000,), schemes=("http",)),
            ProbeTarget(host=host, ports=(5001,), schemes=("https",)),
        ]

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None:
        haystack = f"{response.headers} {response.text}".lower()
        if "synology" not in haystack and "diskstation" not in haystack:
            return None
        return VendorProbeResult(
            self.vendor,
            "nas_admin",
            response.url,
            response.url,
            0.9,
            {"matched": "synology"},
        )
