from text_service.service import Service


def test_account_lifecycle() -> None:
    service = Service()
    account = {"username": "alice", "password": "password1"}
    assert service.handle("GET", "/ping", None, "") == (200, {"data": "pong"})
    assert service.handle("POST", "/users", account, "")[0] == 201
    assert service.handle("POST", "/users", account, "")[0] == 409
    assert service.handle("POST", "/sessions", {**account, "password": "incorrect"}, "")[0] == 401
    token = service.handle("POST", "/sessions", account, "")[1]["data"]["token"]
    next_token = service.handle("POST", "/sessions", account, "")[1]["data"]["token"]
    assert token != next_token
    assert service.handle("GET", "/texts", None, f"Bearer {token}")[0] == 401
    assert service.handle("GET", "/texts", None, f"Bearer {next_token}") == (200, {"data": []})
    assert service.handle("DELETE", "/sessions/current", None, f"Bearer {next_token}")[0] == 200
    assert service.handle("GET", "/texts", None, f"Bearer {next_token}")[0] == 401


def test_validation() -> None:
    service = Service()
    for body in (
        None,
        [],
        {},
        {"username": True, "password": "password1"},
        {"username": "a/b", "password": "password1"},
    ):
        assert service.handle("POST", "/users", body, "")[0] == 400


def test_concurrent_registration() -> None:
    from concurrent.futures import ThreadPoolExecutor

    service = Service()
    body = {"username": "alice", "password": "password1"}
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(lambda _: service.handle("POST", "/users", body, "")[0], range(4)))
    assert sorted(statuses) == [201, 409, 409, 409]
def test_login_returns_expires_in() -> None:
    service = Service(token_ttl=300)
    account = {"username": "alice", "password": "password1"}
    service.handle("POST", "/users", account, "")
    status, result = service.handle("POST", "/sessions", account, "")
    assert status == 200
    assert result["data"]["expires_in"] == 300
    assert "token" in result["data"]


def test_token_valid_within_ttl() -> None:
    service = Service(token_ttl=300)
    account = {"username": "alice", "password": "password1"}
    service.handle("POST", "/users", account, "")
    _, login = service.handle("POST", "/sessions", account, "")
    token = login["data"]["token"]
    # 有效期内访问 → 200
    assert service.handle("GET", "/texts", None, f"Bearer {token}")[0] == 200


def test_token_expired() -> None:
    service = Service(token_ttl=0)  # 有效期 0 秒 → 登录瞬间就过期
    account = {"username": "alice", "password": "password1"}
    service.handle("POST", "/users", account, "")
    _, login = service.handle("POST", "/sessions", account, "")
    token = login["data"]["token"]
    # 已过期 → 401
    assert service.handle("GET", "/texts", None, f"Bearer {token}")[0] == 401
