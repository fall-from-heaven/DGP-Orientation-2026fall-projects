import argparse
import getpass
import re
from typing import Any

_NAME_RE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


def valid_name(name: str) -> bool:
    return _NAME_RE.fullmatch(name) is not None



import httpx


def read_multiline() -> str:
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:          # Ctrl+Z 触发，作为结束
        pass
    return "\n".join(lines)

def exchange(
    client: httpx.Client, method: str, path: str, token: str = "", body: object = None
) -> tuple[int, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = client.request(method, path, json=body, headers=headers)
    try:
        result = response.json()
    except ValueError:
        result = {"message": response.text}
    return response.status_code, result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:7878")
    args = parser.parse_args()
    token = ""
    with httpx.Client(
        base_url=args.url, timeout=12, follow_redirects=False, trust_env=False
    ) as client:
        try:
            while True:
                command = input(
                    "ping / register / login / logout / list / echo / "
                    "delete-user / put / get / delete / q > "
                ).strip()
                body = None
                if command == "q":
                    break
                if command in ("register", "login"):
                    body = {
                        "username": input("username: "),
                        "password": getpass.getpass("password: "),
                    }
                    method, path = "POST", "/users" if command == "register" else "/sessions"
                elif command in ("ping", "logout", "list"):
                    method, path = {
                        "ping": ("GET", "/ping"),
                        "logout": ("DELETE", "/sessions/current"),
                        "list": ("GET", "/texts"),
                    }[command]
                elif command == "echo":
                    print("Enter text (press Ctrl+Z to finish):")
                    body = {"text": read_multiline()}
                    method, path = "POST", "/echo"
                elif command == "put":
                    name = input("Enter name of the text file to upload: ")
                    print("Enter text (press Ctrl+Z to finish):")
                    body = {"text": read_multiline()}
                    if not valid_name(name):
                        print("Invalid file name.")
                        continue
                    method ,path = "PUT", f"/texts/{name}"
                elif command == "get":
                    name = input("Enter name of the text file to download: ")
                    if not valid_name(name):
                        print("Invalid file name.")
                        continue
                    body = None
                    method, path = "GET", f"/texts/{name}"
                elif command == "delete":
                    name = input("Enter name of the text file to delete: ")
                    if not valid_name(name):
                        print("Invalid file name.")
                        continue
                    body = None
                    method, path = "DELETE", f"/texts/{name}"
                elif command == "delete-user":
                    body = None
                    method, path = "DELETE", "/users/me"
                else:
                    print("Unknown command.")
                    continue
                try:
                    status, result = exchange(client, method, path, token, body)
                    print(status, result)
                    if command == "login" and status == 200:
                        token = result["data"]["token"]
                    if status == 401:
                        print("Please log in again.")
                    if status == 401 or (command == "logout" and status == 200):
                        token = ""
                    if command == "delete-user" and status == 200:
                        token = ""
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    print(f"Request failed: {exc}")
        except (EOFError, KeyboardInterrupt):
            print()
