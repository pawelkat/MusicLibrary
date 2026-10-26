# MusicLibrary

Tag a folder of MP3s to one release and rename the files into sleeve order. Audio is not re-encoded.

Rules for this phone's library live in the Obsidian note `Music library` (`/sdcard/Music`). This repo is the script.

## Scripts

| Script | What it does |
|---|---|
| `scripts/inspect_album.py` | Duration, track, artist, album, title, date, genre |
| `scripts/tag_release.py` | ID3v2.4 plus `NN - Title.mp3` |

On this phone, Termux Python 3.14 has no mutagen. Both scripts add `/data/data/com.termux/files/usr/lib/python3.11/site-packages` when the import fails. Elsewhere: `pip install -r requirements.txt`.

```bash
python3 scripts/inspect_album.py "/sdcard/Music/ALBUM"
python3 scripts/tag_release.py --dry-run releases/release.json "/sdcard/Music/ALBUM"
python3 scripts/tag_release.py releases/release.json "/sdcard/Music/ALBUM"
```

`--cover FILE.jpg` overrides `cover_url`. Cover images and `releases/*.json` stay out of git.

`termux-media-scan` hangs in PRoot. Rescan from the player after a real run.

## Release file

JSON. `tracks[].n` is `1..N` with no gaps. A file matches when its name is already `NN - Title.mp3`, or contains `[youtube_id]`, or its stem contains the title (or `match`). One match or the script stops.

No barcode, ISRC, BPM, or lyric text unless the JSON already has that fact. Do not invent them.

A file already named `NN - ...` is that track, even when the title text still differs. Filenames drop `? * : " < > | \\`. The title tag keeps those characters. A release JSON may list `discs` with a `folder` for each disc (`TPOS` `n/total`, track numbers restart).

Keep each release JSON on the machine under `releases/`. Do not commit it.
