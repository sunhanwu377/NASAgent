class UgreenError(RuntimeError):
    """Base error for UGREEN adapter failures."""


class UnsupportedUgreenOperation(UgreenError):
    """Raised when verified UGREEN API details are not available."""
