import pytest

from nasagent.integrations.alist.client import AListClient


@pytest.mark.asyncio
async def test_alist_client_posts_login(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="http://nas.local:5244/api/auth/login",
        json={"code": 200, "data": {"token": "alist-token"}},
    )
    client = AListClient(base_url="http://nas.local:5244")

    token = await client.login("admin", "password")

    assert token == "alist-token"


@pytest.mark.asyncio
async def test_alist_client_lists_files(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="http://nas.local:5244/api/fs/list",
        json={"code": 200, "data": {"content": [{"name": "movie.mkv"}]}},
    )
    client = AListClient(base_url="http://nas.local:5244", token="alist-token")

    result = await client.list_files("/")

    assert result == [{"name": "movie.mkv"}]
