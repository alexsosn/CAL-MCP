from __future__ import annotations

import asyncio
from html import unescape
import re
from urllib.parse import urlsplit

from cal_mcp.client import CalClientConfig, CalHttpClient, CalRequest, CalResponse
from cal_mcp.lexicon import _parse_lines


def inspect(response: CalResponse) -> str:
    text = response.body.decode("utf-8", errors="replace")
    lines = _parse_lines(response)
    print(f"STATUS={response.status_code}")
    print(f"URL={response.url}")
    print(f"BYTES={len(response.body)}")
    print(f"CONTENT_TYPE={response.content_type}")
    print(f"SEMANTIC_LINES={len(lines)}")

    for index, line in enumerate(lines[:40]):
        rendered = line.text.replace("\n", " ")[:220]
        links = [f"{link.text[:80]!r}->{link.href[:180]}" for link in line.links]
        print(f"LINE[{index}]={rendered!r} LINKS={links}")

    hrefs = re.findall(r"href\s*=\s*['\"]([^'\"]+)", text, flags=re.IGNORECASE)
    path_counts: dict[str, int] = {}
    for href in hrefs:
        path = urlsplit(unescape(href)).path.rsplit("/", 1)[-1]
        path_counts[path] = path_counts.get(path, 0) + 1
    print(f"HREF_PATH_COUNTS={sorted(path_counts.items())}")

    for needle in ("oneentry.php", "cal_entry_web.php", "browseSKEYheaders.php", "No entries"):
        positions = [match.start() for match in re.finditer(re.escape(needle), text, re.IGNORECASE)]
        print(f"RAW_NEEDLE={needle!r} COUNT={len(positions)}")
        for pos in positions[:5]:
            start = max(0, pos - 180)
            end = min(len(text), pos + 320)
            snippet = re.sub(r"\s+", " ", unescape(text[start:end]))
            print(f"RAW[{needle}]={snippet[:500]!r}")
    return "ok"


async def main() -> None:
    client = CalHttpClient(
        config=CalClientConfig(
            connect_timeout_seconds=5.0,
            read_timeout_seconds=10.0,
            total_timeout_seconds=15.0,
            max_concurrency=1,
            max_retries=0,
            max_response_bytes=262_144,
            cache_enabled=False,
        )
    )
    try:
        await client.fetch(
            CalRequest(
                method="GET",
                path="browseSKEYheaders.php",
                params=(("first3", '"br"'),),
            ),
            parser=inspect,
            cache_namespace="issue47-research",
        )
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
