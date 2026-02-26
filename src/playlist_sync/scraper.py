import json
import random
import re
import time
from urllib.parse import urlparse

import requests


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

MAX_RETRIES = 3
RETRY_DELAY_BASE = 2


def validate_url(url: str) -> None:
    """Validate that URL is from apple.com."""
    parsed = urlparse(url)
    if parsed.netloc not in ("music.apple.com", "apple.co"):
        raise ValueError(f"URL must be from apple.com, got: {parsed.netloc}")


def extract_longest_script(html_text: str) -> str:
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html_text, flags=re.S | re.I)
    return max(scripts, key=len) if scripts else ""


def extract_json_array_bruteforce(script_text: str):
    """Find the JSON array containing 'PlaylistDetailPageIntent'."""
    needle = "PlaylistDetailPageIntent"
    idx = script_text.find(needle)
    if idx == -1:
        raise RuntimeError("Couldn't find PlaylistDetailPageIntent in script blob.")

    start = script_text.rfind("[", 0, idx)
    if start == -1:
        raise RuntimeError("Couldn't find '[' starting playlist JSON array.")

    depth = 0
    end = None
    for i, ch in enumerate(script_text[start:], start=start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end is None:
        raise RuntimeError("Bracket match failed while extracting playlist JSON.")

    blob = script_text[start:end + 1]
    return json.loads(blob)


def locate_playlist_entry(arr: list) -> dict:
    """Find the dict whose intent.$kind/intent.kind includes 'PlaylistDetailPageIntent'."""
    if not isinstance(arr, list):
        raise RuntimeError("Top-level playlist blob was not a list.")

    for entry in arr:
        if not isinstance(entry, dict):
            continue
        intent = entry.get("intent", {})
        kind = intent.get("$kind") or intent.get("kind") or ""
        if "PlaylistDetailPageIntent" in kind:
            return entry

    raise RuntimeError("Couldn't locate playlist entry with PlaylistDetailPageIntent in parsed JSON.")


def get_sections_from_entry(entry: dict) -> list:
    """Get sections list from entry."""
    data = entry.get("data", {}) or {}
    sections = data.get("sections")
    if not isinstance(sections, list):
        raise RuntimeError("Couldn't locate data.sections.")
    return sections


def get_playlist_name(entry: dict, sections: list) -> str:
    """Return the playlist display name."""
    data = entry.get("data", {}) or {}
    attrs = data.get("attributes", {}) or {}

    cand = (
        attrs.get("name")
        or attrs.get("title")
        or data.get("title")
        or ""
    ).strip()
    if cand:
        return cand

    for sec in sections:
        sec_id = sec.get("id", "")
        if "playlist-detail-header-section" in sec_id:
            items = sec.get("items") or []
            if items and isinstance(items[0], dict):
                header_title = items[0].get("title", "")
                if isinstance(header_title, str) and header_title.strip():
                    return header_title.strip()

    return ""


def try_extract_artist_structured(item: dict) -> str | None:
    """Try common shapes for artist info in Apple's playlist item dicts."""
    for key in ("artistName", "artist", "artistNames"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    for key in ("artists", "contributors", "bylines"):
        arr = item.get(key)
        if isinstance(arr, list):
            names = []
            for sub in arr:
                if isinstance(sub, dict):
                    for nk in ("name", "text", "artistName", "artist"):
                        v = sub.get(nk)
                        if isinstance(v, str) and v.strip():
                            names.append(v.strip())
                elif isinstance(sub, str) and sub.strip():
                    names.append(sub.strip())
            if names:
                dedup = []
                for n in names:
                    if n not in dedup:
                        dedup.append(n)
                return " & ".join(dedup)

    return None


def try_extract_artist_regex(item: dict) -> str | None:
    """Last-resort fallback: regex search for any 'artist...' field in raw JSON."""
    it_json = json.dumps(item, ensure_ascii=False)
    m = re.search(r'"artist[^"]*"\s*:\s*"([^"]+)"', it_json, flags=re.I)
    return m.group(1).strip() if m else None


def extract_track_items_from_sections(sections: list) -> list:
    """Heuristic: pick the 'items' list with the most dicts that have a 'title'."""
    best_items = []
    for sec in sections:
        items = sec.get("items") or []
        if not isinstance(items, list):
            continue
        has_title = [x for x in items if isinstance(x, dict) and "title" in x]
        if has_title and len(items) > len(best_items):
            best_items = items
    return best_items


def build_track_display(item: dict) -> str | None:
    """Return 'Title - Artist' with em dashes normalized to '-'."""
    if not isinstance(item, dict):
        return None

    title = str(item.get("title", "")).strip()
    artist = (
        try_extract_artist_structured(item)
        or try_extract_artist_regex(item)
        or ""
    ).strip()

    if not title:
        return None

    if artist:
        disp = f"{title} - {artist}"
    else:
        disp = title

    return disp.replace("—", "-")


def fetch_playlist(url: str) -> tuple[str, list[str]]:
    """Fetch playlist name and track displays from Apple Music URL.

    Returns:
        Tuple of (playlist_name, list of track displays)
    """
    validate_url(url)

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
            response.raise_for_status()
            break
        except requests.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
            continue

    if last_error:
        raise RuntimeError(f"Failed to fetch playlist after {MAX_RETRIES} attempts: {last_error}")

    html_text = response.text
    script_blob = extract_longest_script(html_text)
    parsed_arr = extract_json_array_bruteforce(script_blob)
    playlist_entry = locate_playlist_entry(parsed_arr)
    sections = get_sections_from_entry(playlist_entry)

    playlist_name = get_playlist_name(playlist_entry, sections)
    track_items = extract_track_items_from_sections(sections)

    track_displays = []
    for item in track_items:
        disp = build_track_display(item)
        if disp:
            track_displays.append(disp)

    return playlist_name, track_displays
