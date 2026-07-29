from nasagent.discovery.models import ProbeHttpResponse, ProbeTarget, VendorProbeResult


class GenericNasProbe:
    vendor = "generic"

    def targets(self, host: str) -> list[ProbeTarget]:
        return [
            ProbeTarget(host=host, ports=(80,), schemes=("http",)),
            ProbeTarget(host=host, ports=(443,), schemes=("https",)),
        ]

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None:
        haystack = f"{response.headers} {response.text}".lower()
        if "nas" not in haystack and "network attached storage" not in haystack:
            return None
        return VendorProbeResult(
            self.vendor,
            "nas_admin",
            response.url,
            response.url,
            0.5,
            {"matched": "nas"},
        )
