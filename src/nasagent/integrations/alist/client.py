import httpx


class AListClient:
    def __init__(self, *, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    async def login(self, username: str, password: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": username, "password": password},
            )
        response.raise_for_status()
        data = response.json()
        return str(data["data"]["token"])

    async def list_files(self, path: str) -> list[dict[str, object]]:
        headers = {"Authorization": self.token} if self.token else {}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/fs/list",
                json={"path": path},
                headers=headers,
            )
        response.raise_for_status()
        data = response.json()
        return list(data.get("data", {}).get("content", []))
