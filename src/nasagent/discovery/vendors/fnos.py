from nasagent.discovery.models import ProbeHttpResponse, ProbeTarget, VendorProbeResult


class FnosProbe:
    vendor = "fnos"

    def targets(self, host: str) -> list[ProbeTarget]:
        return [
            ProbeTarget(host=host, ports=(5666,), schemes=("http",)),
            ProbeTarget(host=host, ports=(5667,), schemes=("https",)),
        ]

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None:
        haystack = f"{response.headers} {response.text}".lower()
        if "fnos" not in haystack and "feiniu" not in haystack and "飞牛" not in haystack:
            return None
        return VendorProbeResult(
            self.vendor,
            "nas_admin",
            response.url,
            response.url,
            0.9,
            {"matched": "fnos"},
        )
