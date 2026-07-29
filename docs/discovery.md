# Discovery

NASAgent has discovery plumbing for mDNS/Bonjour, SSDP/UPnP, constrained HTTP probing, and vendor probes. Current mDNS and SSDP functions are placeholders that return no results.

`nasagent config init` asks before discovery and currently calls `DiscoveryScanner().scan_hosts([])`, so config initialization does not probe explicit hosts and does not enumerate subnets. HTTP and vendor probes only run when callers pass explicit hosts to `DiscoveryScanner.scan_hosts(hosts)`.

Vendor probes live under `nasagent.discovery.vendors`. To add a vendor, create a probe class with `targets(host)` and `match(response)`, then register it in `VendorProbeRegistry.default()`.

Default vendor probes include UGREEN, Synology, FNOS, Zspace, and generic NAS web admin detection.
