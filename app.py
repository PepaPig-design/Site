#!/usr/bin/env python3
import json
import random
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent

ADJECTIVES = [
    "best", "fast", "smart", "clear", "bright", "silent", "swift", "cool", "fresh", "hyper",
    "lucky", "royal", "prime", "urban", "rapid", "epic", "super", "clean", "bold", "magic",
]

NOUNS = [
    "speed", "wave", "cloud", "focus", "vision", "storm", "fox", "wolf", "spark", "byte",
    "light", "forge", "pilot", "nexus", "river", "pulse", "shield", "core", "bridge", "mark",
]

USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$")


class NicknameHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/generate":
            self.handle_generate(parsed.query)
            return

        if parsed.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def handle_generate(self, query: str):
        params = parse_qs(query)
        length = clamp_int(params.get("length", ["9"])[0], 9, 5, 16)
        count = clamp_int(params.get("count", ["10"])[0], 10, 1, 20)

        generated = create_nicknames(length=length, count=count)
        items = []
        for nickname in generated:
            items.append(
                {
                    "nickname": nickname,
                    "available": is_telegram_username_available(nickname),
                }
            )

        payload = json.dumps({"items": items}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def clamp_int(raw: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def create_nicknames(length: int, count: int):
    variants = set()
    attempts = 0
    max_attempts = 1200

    while len(variants) < count and attempts < max_attempts:
        attempts += 1
        nickname = build_word_style_name(length)
        if nickname and nickname.isalpha() and 5 <= len(nickname) <= 16:
            variants.add(nickname.lower())

    return sorted(variants)[:count]


def build_word_style_name(length: int) -> str:
    random.shuffle(ADJECTIVES)
    random.shuffle(NOUNS)

    for first in ADJECTIVES[:10]:
        for second in NOUNS[:10]:
            candidate = first + second
            if len(candidate) == length:
                return candidate

    if random.random() < 0.5:
        pool = ADJECTIVES
    else:
        pool = NOUNS

    for word in pool:
        if len(word) >= length:
            return word[:length]

    one = random.choice(ADJECTIVES)
    two = random.choice(NOUNS)
    candidate = (one + two)[:length]
    return candidate


def is_telegram_username_available(nickname: str) -> bool:
    if not USERNAME_RE.match(nickname):
        return False

    url = f"https://t.me/{nickname}"
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urlopen(req, timeout=7) as response:
            html = response.read().decode("utf-8", errors="ignore").lower()
    except Exception:
        return False

    taken_markers = [
        "if you have telegram, you can contact",
        "send message",
        "tgme_page_title",
    ]

    free_markers = [
        "this page could not be found",
        "username is not occupied",
        "sorry, this username is not available",
    ]

    if any(marker in html for marker in free_markers):
        return True

    if any(marker in html for marker in taken_markers):
        return False

    return False


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), NicknameHandler)
    print("Server running on http://0.0.0.0:8000")
    server.serve_forever()
