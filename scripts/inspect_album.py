#!/usr/bin/env python3
"""Print duration and the tags a player uses to order an album folder."""

import sys
from pathlib import Path

_MUTAGEN = Path("/data/data/com.termux/files/usr/lib/python3.11/site-packages")
try:
    import mutagen  # noqa: F401
except ImportError:
    if _MUTAGEN.is_dir():
        sys.path.insert(0, str(_MUTAGEN))

from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import MP3


def text(tags, key):
    frame = tags.get(key) if tags is not None else None
    if frame is None or not getattr(frame, "text", None):
        return ""
    return str(frame.text[0])


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_album.py ALBUM_DIR")
    folder = Path(sys.argv[1])
    files = sorted(folder.glob("*.mp3"))
    if not files:
        raise SystemExit(f"no mp3 files in {folder}")
    for path in files:
        audio = MP3(path)
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = None
        print(
            f"{path.name}\t{audio.info.length:.3f}s\t"
            f"{text(tags, 'TRCK')}\t{text(tags, 'TPE1')}\t"
            f"{text(tags, 'TALB')}\t{text(tags, 'TIT2')}\t"
            f"{text(tags, 'TDRC')}\t{text(tags, 'TCON')}"
        )


if __name__ == "__main__":
    main()
