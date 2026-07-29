from nasagent.discovery.models import ProbeHttpResponse, ProbeTarget, VendorProbeResult


class ZspaceProbe:
    vendor = "zspace"

    def targets(self, host: str) -> list[ProbeTarget]:
        return [
            ProbeTarget(host=host, ports=(5055,), schemes=("http",)),
            ProbeTarget(host=host, ports=(5056,), schemes=("https",)),
        ]

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None:
        haystack = f"{response.headers} {response.text}".lower()
        if "zspace" not in haystack and "极空间" not in haystack:
            return None
        return VendorProbeResult(
            self.vendor,
            "nas_admin",
            response.url,
            response.url,
            0.9,
            {"matched": "zspace"},
        )
