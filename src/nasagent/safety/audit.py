from pydantic import BaseModel


class AuditEvent(BaseModel):
    tool_name: str
    risk_level: str
    allowed: bool
    reason: str
