import json

import httpx
import pytest

from text_service.client import exchange, read_multiline


def test_list() -> None:

    
    #test exchange function with a mock response for the /texts endpoint
    def respond_list(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/texts"
        assert request.headers["Authorization"] == "Bearer example"
        return httpx.Response(200, json={"data": []})

    with httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(respond_list)
    ) as client:
        assert exchange(client, "GET", "/texts", "example") == (200, {"data": []})



def test_echo_common() -> None:

    test_text = "Hello, World!"

    def respond_echo(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/echo"
        assert request.method == "POST"
        assert json.loads(request.read()) == {"text": test_text}
        return httpx.Response(200, json={"data": test_text})

    with httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(respond_echo)
    ) as client:
        assert exchange(client, "POST", "/echo", body={"text": test_text}) == (
            200,
            {"data": test_text}
        )


    
def test_echo_unicode() -> None:
    test_text = "Hello, World! こんにちは😀"

    def respond_echo(request: httpx.Request) -> httpx.Response:
            assert json.loads(request.read()) == {"text": test_text}
            return httpx.Response(200, json={"data": test_text})
    
    with httpx.Client(
            base_url="http://localhost", transport=httpx.MockTransport(respond_echo)
        ) as client:
            assert exchange(client, "POST", "/echo", body={"text": test_text}) == (
                200,
                {"data": test_text}
            )

def test_echo_empty() -> None:

    test_text = ""

    def respond_echo(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.read()) == {"text": test_text}
        return httpx.Response(200, json={"data": test_text})

    with httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(respond_echo)
    ) as client:
        assert exchange(client, "POST", "/echo", body={"text": test_text}) == (
            200,
            {"data": test_text}
        )

def test_echo_multiline(monkeypatch: pytest.MonkeyPatch) -> None:
    input_lines = ["Hello,", "World!", ""] 
    def fake_input(prompt: str = "") -> str:
        if not input_lines:
            raise EOFError
        return input_lines.pop(0)
    monkeypatch.setattr("builtins.input", fake_input)
    assert read_multiline() == "Hello,\nWorld!\n"
def test_ping() -> None:
     
    def respond_ping(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ping"
        return httpx.Response(200, json={"data": "pong"})

    with httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(respond_ping)
    ) as client:
        assert exchange(client, "GET", "/ping") == (200, {"data": "pong"})

def test_register() -> None:
    test_username = "testuser"
    test_password = "testpass"

    def respond_register(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/users"
        assert request.method == "POST"
        assert json.loads(request.read()) == {
            "username": test_username,
            "password": test_password,
        }
        return httpx.Response(201, json={"data": {"username": test_username}})

    with httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(respond_register)
    ) as client:
        assert exchange(
            client,
            "POST",
            "/users",
            body={"username": test_username, "password": test_password},
        ) == (201, {"data": {"username": test_username}})

def test_login() -> None:
    test_username = "testuser"
    test_password = "testpass"
    test_token = "exampletoken"

    def respond_login(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/sessions"
        assert request.method == "POST"
        assert json.loads(request.read()) == {
            "username": test_username,
            "password": test_password,
        }
        return httpx.Response(200, json={"data": {"token": test_token}})

    with httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(respond_login)
    ) as client:
        assert exchange(
            client,
            "POST",
            "/sessions",
            body={"username": test_username, "password": test_password},
        ) == (200, {"data": {"token": test_token}})

def test_logout() -> None:
    test_token = "exampletoken"

    def respond_logout(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/sessions/current"
        assert request.method == "DELETE"
        assert request.headers["Authorization"] == f"Bearer {test_token}"
        return httpx.Response(200,json={"data": None})

    with httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(respond_logout)
    ) as client:
        assert exchange(client, "DELETE", "/sessions/current", token=test_token) == (
            200,
            {"data": None},
        )