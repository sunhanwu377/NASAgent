# Discovery

NASAgent discovers services through mDNS/Bonjour, SSDP/UPnP, constrained HTTP probing, and vendor probes.

Vendor probes live under `nasagent.discovery.vendors`. To add a vendor, create a probe class with `targets(host)` and `match(response)`, then register it in `VendorProbeRegistry.default()`.

Default vendor probes include UGREEN, Synology, FNOS, Zspace, and generic NAS web admin detection.
