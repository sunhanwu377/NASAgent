from nasagent.discovery.models import ProbeHttpResponse, ProbeTarget, VendorProbeResult


class UgreenProbe:
    vendor = "ugreen"

    def targets(self, host: str) -> list[ProbeTarget]:
        return [
            ProbeTarget(host=host, ports=(9999,), schemes=("http",)),
            ProbeTarget(host=host, ports=(9443,), schemes=("https",)),
        ]

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None:
        haystack = f"{response.headers} {response.text}".lower()
        if "ugreen" not in haystack and "绿联" not in haystack:
            return None
        return VendorProbeResult(
            vendor=self.vendor,
            service_type="nas_admin",
            admin_url=response.url,
            login_url=response.url,
            confidence=0.9,
            evidence={"matched": "ugreen"},
        )
