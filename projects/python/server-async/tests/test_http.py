from collections.abc import AsyncGenerator

import pytest
from httpx2 import ASGITransport, AsyncClient

from text_service.server import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    app = create_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client,
    ):
        yield client


async def test_http_routes(client: AsyncClient) -> None:
    assert (await client.get("/ping")).status_code == 200
    response = await client.post("/users", json={"username": "alice", "password": "password1"})
    assert response.status_code == 201
    response = await client.post("/sessions", json={"username": "alice", "password": "password1"})
    token = response.json()["data"]["token"]
    assert (
        await client.get("/texts", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 200
    assert (await client.get("/texts")).status_code == 401
    assert (
        await client.post(
            "/users", content=b"not JSON", headers={"Content-Type": "application/json"}
        )
    ).status_code == 400
    assert (
        await client.post(
            "/users", content=b"x" * 524289, headers={"Content-Type": "application/json"}
        )
    ).status_code == 413


@pytest.mark.parametrize("body", [b"not JSON", b"\xff", b"NaN"])
async def test_invalid_json(client: AsyncClient, body: bytes) -> None:
    assert (await client.post("/users", content=body)).status_code == 400


async def test_body_limit_and_routing(client: AsyncClient) -> None:
    exact = b"{}" + b" " * (524288 - 2)
    assert (await client.post("/users", content=exact)).status_code == 400
    assert (await client.post("/users", content=exact + b" ")).status_code == 413
    assert (await client.get("/missing")).status_code == 404
    assert (await client.get("/echo")).status_code == 405
    assert (await client.patch("/ping")).status_code == 405
    assert (await client.get("/ping?test=1")).json() == {"data": "pong"}




@pytest.mark.parametrize("path", ["/ping", "/users", "/sessions", "/sessions/current", "/texts"])
async def test_wrong_method_precedes_authentication(client: AsyncClient, path: str) -> None:
    assert (await client.patch(path)).status_code == 405



async def test_text_crud_flow(client: AsyncClient) -> None:
    await client.post("/users", json={"username": "alice", "password": "password1"})
    login = await client.post("/sessions", json={"username": "alice", "password": "password1"})
    token = login.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert (await client.put("/texts/note", json={"text": "hello world"}, headers=headers)).status_code == 200
    get = await client.get("/texts/note", headers=headers)
    assert get.status_code == 200
    assert get.json()["data"] == "hello world"
    lst = await client.get("/texts", headers=headers)
    assert lst.json()["data"] == ["note"]
    assert (await client.delete("/texts/note", headers=headers)).status_code == 200
    assert (await client.get("/texts/note", headers=headers)).status_code == 404


async def test_delete_user(client: AsyncClient) -> None:
    await client.post("/users", json={"username": "bob", "password": "password1"})
    login = await client.post("/sessions", json={"username": "bob", "password": "password1"})
    token = login.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert (await client.delete("/users/me", headers=headers)).status_code == 200
    assert (await client.get("/texts", headers=headers)).status_code == 401   # 旧 token 失效
    assert (await client.post("/sessions", json={"username": "bob", "password": "password1"})).status_code == 401  # 账号已删


async def test_missing_token_is_401(client: AsyncClient) -> None:
    assert (await client.get("/texts")).status_code == 401
    assert (await client.get("/texts/note")).status_code == 401
    assert (await client.delete("/users/me")).status_code == 401
