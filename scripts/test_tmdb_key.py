"""Quick check that TMDb credentials in .env work."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
URL = "https://api.themoviedb.org/3/configuration"


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def main() -> int:
    env = {**load_env(ENV_PATH), **os.environ}
    api_key = env.get("TMDB_API_KEY", "").strip()
    token = env.get("TMDB_ACCESS_TOKEN", "").strip()

    if not api_key and not token:
        print("No TMDB_API_KEY or TMDB_ACCESS_TOKEN in .env")
        return 1

    headers = {"Accept": "application/json"}
    url = URL

    # Short hex-looking values are usually the v3 API key, not a Bearer JWT.
    if token and not token.startswith("eyJ") and "." not in token and not api_key:
        print("Note: TMDB_ACCESS_TOKEN looks like an API key; using it as api_key=…")
        api_key = token
        token = ""

    if token:
        headers["Authorization"] = f"Bearer {token}"
        auth_mode = "Bearer token"
    else:
        url = f"{URL}?{urllib.parse.urlencode({'api_key': api_key})}"
        auth_mode = "api_key"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"FAIL ({auth_mode}): HTTP {e.code}")
        print(body[:500])
        return 1
    except urllib.error.URLError as e:
        print(f"FAIL ({auth_mode}): {e}")
        return 1

    images = data.get("images", {})
    base = images.get("secure_base_url") or images.get("base_url")
    print(f"OK ({auth_mode}): TMDb answered.")
    if base:
        print(f"image base url: {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
