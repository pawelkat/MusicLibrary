#!/usr/bin/env python3
"""Write ID3v2.4 tags for one release and rename files into sleeve order.

Does not re-encode. Reads a release JSON file. See README.md.
"""

import json
import sys
import unicodedata
import urllib.request
from pathlib import Path

# Termux Python 3.14 has no mutagen. The 3.11 install is still on disk.
_MUTAGEN = Path("/data/data/com.termux/files/usr/lib/python3.11/site-packages")
try:
    import mutagen  # noqa: F401
except ImportError:
    if _MUTAGEN.is_dir():
        sys.path.insert(0, str(_MUTAGEN))

from mutagen.id3 import (  # noqa: E402
    APIC,
    COMM,
    ID3,
    ID3NoHeaderError,
    TALB,
    TCOM,
    TCON,
    TCOP,
    TDRC,
    TEXT,
    TIT2,
    TLAN,
    TMCL,
    TPE1,
    TPE2,
    TPOS,
    TPUB,
    TRCK,
    TXXX,
    WXXX,
    WOAR,
    Encoding,
)

UA = "MusicLibrary/1.0 (phone library tagger)"


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(ch for ch in value if ch.isalnum())


def load_release(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    tracks = data.get("tracks") or []
    if not tracks:
        raise SystemExit(f"{path} has no tracks")
    numbers = [int(track["n"]) for track in tracks]
    if numbers != list(range(1, len(tracks) + 1)):
        raise SystemExit("track n values must be 1..N with no gaps")
    return data


def dest_name(track: dict) -> str:
    return f"{int(track['n']):02d} - {track['title']}.mp3"


def find_source(folder: Path, track: dict) -> Path:
    files = list(folder.glob("*.mp3"))
    numbered = folder / dest_name(track)
    if numbered in files:
        return numbered
    hits = []
    youtube_id = track.get("youtube_id") or ""
    needle = norm(track.get("match") or track["title"])
    for path in files:
        if youtube_id and f"[{youtube_id}]" in path.name:
            hits.append(path)
            continue
        if needle and needle in norm(path.stem):
            hits.append(path)
    unique = []
    for path in hits:
        if path not in unique:
            unique.append(path)
    if len(unique) != 1:
        raise SystemExit(
            f"track {track['n']} {track['title']!r} matched {len(unique)} files: "
            + ", ".join(path.name for path in unique)
        )
    return unique[0]


def fetch_cover(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if not data.startswith(b"\xff\xd8"):
        raise SystemExit("cover URL did not return a JPEG")
    return data


def cover_bytes(release: dict, cover_arg: str | None) -> bytes:
    if cover_arg:
        data = Path(cover_arg).read_bytes()
        if not data.startswith(b"\xff\xd8"):
            raise SystemExit(f"{cover_arg} is not a JPEG")
        return data
    url = release.get("cover_url") or ""
    if not url:
        raise SystemExit("release has no cover_url; pass --cover FILE.jpg")
    return fetch_cover(url)


def add_text(tags, frame_cls, value: str) -> None:
    if value:
        tags.add(frame_cls(encoding=Encoding.UTF8, text=value))


def write_tags(path: Path, release: dict, track: dict, cover: bytes, total: int) -> None:
    try:
        ID3(path).delete(path)
    except ID3NoHeaderError:
        pass
    tags = ID3()
    enc = Encoding.UTF8
    number = int(track["n"])
    disc = str(release.get("disc") or 1)
    disc_total = str(release.get("disc_total") or 1)
    tags.add(TIT2(encoding=enc, text=track["title"]))
    tags.add(TPE1(encoding=enc, text=release["artist"]))
    tags.add(TPE2(encoding=enc, text=release.get("album_artist") or release["artist"]))
    tags.add(TALB(encoding=enc, text=release["album"]))
    tags.add(TRCK(encoding=enc, text=f"{number}/{total}"))
    tags.add(TPOS(encoding=enc, text=f"{disc}/{disc_total}"))
    tags.add(TDRC(encoding=enc, text=release["date"]))
    add_text(tags, TCON, release.get("genre") or "")
    add_text(tags, TLAN, release.get("language") or "eng")
    add_text(tags, TCOM, release.get("composer") or release["artist"])
    add_text(tags, TEXT, track.get("lyricist") or "")
    add_text(tags, TPUB, release.get("publisher") or "")
    add_text(tags, TCOP, release.get("copyright") or "")
    if release.get("comment"):
        tags.add(COMM(encoding=enc, lang="eng", desc="", text=release["comment"]))
    people = release.get("musicians") or []
    if people:
        tags.add(TMCL(encoding=enc, people=[[role, name] for role, name in people]))
    tags.add(
        APIC(
            encoding=enc,
            mime="image/jpeg",
            type=3,
            desc="Front cover",
            data=cover,
        )
    )
    if release.get("artist_url"):
        tags.add(WOAR(url=release["artist_url"]))
    for link in release.get("links") or []:
        tags.add(WXXX(encoding=enc, desc=link["desc"], url=link["url"]))
    youtube_id = track.get("youtube_id") or ""
    if youtube_id:
        tags.add(
            WXXX(
                encoding=enc,
                desc="OFFICIAL_VIDEO",
                url=f"https://www.youtube.com/watch?v={youtube_id}",
            )
        )
    extras = dict(release.get("txxx") or {})
    if track.get("lyricist"):
        extras["LYRICIST"] = track["lyricist"]
    if youtube_id:
        extras["YOUTUBE_VIDEO_ID"] = youtube_id
    for desc, value in extras.items():
        if value:
            tags.add(TXXX(encoding=enc, desc=desc, text=str(value)))
    tags.save(path, v2_version=4)


def main() -> None:
    args = sys.argv[1:]
    dry_run = False
    cover_arg = None
    positional = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--cover":
            index += 1
            cover_arg = args[index]
        else:
            positional.append(arg)
        index += 1
    if len(positional) != 2:
        raise SystemExit(
            "usage: tag_release.py [--dry-run] [--cover FILE.jpg] RELEASE.json ALBUM_DIR"
        )
    release_path = Path(positional[0])
    folder = Path(positional[1])
    if not folder.is_dir():
        raise SystemExit(f"not a directory: {folder}")
    release = load_release(release_path)
    tracks = release["tracks"]
    planned = []
    for track in tracks:
        src = find_source(folder, track)
        dest = folder / dest_name(track)
        planned.append((src, dest, track))
    dests = [dest for _, dest, _ in planned]
    if len(dests) != len(set(dests)):
        raise SystemExit("two tracks would use the same filename")
    for src, dest, track in planned:
        action = "keep" if src == dest else f"rename -> {dest.name}"
        print(f"{int(track['n']):02d} {src.name} ({action})")
    if dry_run:
        return
    cover = cover_bytes(release, cover_arg)
    total = len(tracks)
    for src, dest, track in planned:
        write_tags(src, release, track, cover, total)
    for src, dest, track in planned:
        if src == dest:
            continue
        if dest.exists():
            raise SystemExit(f"refusing to overwrite {dest}")
        src.rename(dest)
        print(f"renamed {dest.name}")


if __name__ == "__main__":
    main()
