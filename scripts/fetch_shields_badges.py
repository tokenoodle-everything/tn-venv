"""Download shields.io badge URLs found in docs/ into docs/_static/badges/
and rewrite the source files to point at the local copies.

This is a one-shot tool, not part of the normal docs build. Run it
whenever you add new badges to community.md or index.md. The
rewrites are idempotent: a second run is a no-op once the URLs in
the source already point at local paths.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import time
import urllib.error
import urllib.request

_USER_AGENT = (
    "Mozilla/5.0 (Sphinx; tn-venv-docs) "
    "AppleWebKit/537.36 (KHTML, like Gecko)"
)
_BADGE_RE = re.compile(r"https?://img\.shields\.io/badge/[^)\"\s']+")
_REQUEST_TIMEOUT = 30
_MAX_RETRIES = 3
_RETRY_DELAYS = (0.5, 1.0, 2.0)

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "docs"
BADGE_DIR = SRC_DIR / "_static" / "badges"
BADGE_DIR.mkdir(parents=True, exist_ok=True)

# Files we rewrite. Files under docs/_static/ and docs/changelog.md
# are skipped; see below.
SKIP_DOCNAMES = {"changelog", "_static/badges"}


def fetch(url: str) -> bytes:
    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])
                continue
            raise
    raise last_err


def _cache_path(url: str) -> pathlib.Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return BADGE_DIR / f"{digest}.svg"


def _download(url: str) -> pathlib.Path | None:
    path = _cache_path(url)
    if path.exists() and path.stat().st_size > 0:
        return path
    try:
        body = fetch(url)
    except Exception as exc:
        print(
            f"WARN: failed to fetch {url!r}: {type(exc).__name__}: {exc}",
            flush=True,
        )
        return None
    if not (body.startswith(b"<svg") or body.startswith(b"<?xml")):
        print(
            f"WARN: shields.io returned non-SVG for {url!r} (len={len(body)})",
            flush=True,
        )
        return None
    path.write_bytes(body)
    return path


def _relpath(target: pathlib.Path, badge: pathlib.Path) -> str:
    """Relative path from ``target``'s HTML to ``badge``.

    Sphinx writes HTML at <srcdir>/<docpath-without-ext>/index.html,
    so the depth of the doc HTML file under srcdir is the number of
    parent-directory components of the source file.
    """
    src_rel = target.relative_to(SRC_DIR)
    depth = len(src_rel.parent.parts)
    up = pathlib.Path(*([".."] * depth))
    return (up / "_static" / "badges" / badge.name).as_posix()


def rewrite_file(target: pathlib.Path) -> int:
    text = target.read_text(encoding="utf-8")
    urls = list(dict.fromkeys(_BADGE_RE.findall(text)))
    if not urls:
        return 0
    n = 0
    for url in urls:
        local = _download(url)
        if local is None:
            continue
        rel = _relpath(target, local)
        if rel not in text:
            text = text.replace(url, rel)
            n += 1
    if n:
        target.write_text(text, encoding="utf-8")
    return n


def main() -> int:
    rewrites_total = 0
    files_touched: list[pathlib.Path] = []
    for path in sorted(SRC_DIR.rglob("*.md")):
        rel = path.relative_to(SRC_DIR).as_posix()
        if rel in SKIP_DOCNAMES or rel.startswith("_static/"):
            continue
        if "_static" in path.parts:
            continue
        if path.name == "changelog.md":
            continue
        n = rewrite_file(path)
        if n:
            files_touched.append(path)
            rewrites_total += n
    print(
        f"local-shields: rewrote {rewrites_total} URL(s) across "
        f"{len(files_touched)} file(s) -> {BADGE_DIR.relative_to(ROOT)}"
    )
    for p in files_touched:
        print(f"  - {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())