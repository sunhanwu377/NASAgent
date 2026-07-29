# NAS Adapters

Adapters implement the `NasAdapter` protocol. The simulator adapter is deterministic and used by tests. The UGREEN adapter contains client, auth, model, and error boundaries but raises explicit unsupported-operation errors until verified API details are supplied.

UGREEN packet-capture data needed: login endpoint, auth payload, session token or cookie behavior, file list endpoint, search endpoint, upload and download behavior, delete endpoint, storage status endpoint, device status endpoint, error schema, required headers, and session refresh behavior.
