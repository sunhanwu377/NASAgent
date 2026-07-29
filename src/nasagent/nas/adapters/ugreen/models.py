from pydantic import BaseModel


class UgreenSession(BaseModel):
    authenticated: bool = False
