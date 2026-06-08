<div align="center">

# SpotifyInfoExtract

**A Python CLI tool for extracting Spotify album metadata and tracklists, with export to TXT, CSV, or JSON.**

[![Python](https://img.shields.io/badge/python-3.8+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Spotipy](https://img.shields.io/badge/spotipy-2.x-1DB954?style=flat-square&logo=spotify&logoColor=white)](https://spotipy.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

</div>

---

## Overview

SpotifyInfoExtract authenticates with the Spotify Web API using Client Credentials flow (no user login required) and extracts full data for **albums, playlists, and artists** - metadata plus a complete paginated tracklist (or an artist's top tracks and discography). Results are printed to the terminal and can optionally be saved as a plain-text summary, a CSV of the tracklist, or a full JSON export. The tool runs as an interactive loop, so you can extract multiple items in one session. The access token is cached to `.cache` and reused between runs.

---

## What It Extracts

### Album-level metadata

- Album name and artist(s)
- Release date and record label
- Genres (if available from the API)
- Total track count and full runtime (formatted as `Xm Ys`)
- Spotify URL and cover image URL

### Per-track data

- Track number, name, and contributing artists
- Duration (formatted as `Xm Ys`)
- Explicit flag
- Preview URL (if available)

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Requires: `spotipy`, `python-dotenv`

### 2. Create a Spotify app

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Copy the **Client ID** and **Client Secret**

### 3. Configure credentials

Copy `.env.example` to `.env`:

```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

---

## Usage

```bash
python main.py
```

The tool presents these input modes:

| Mode | Description |
|---|---|
| Album search | Search by artist or album name, then pick from up to 5 results |
| Album by URL/ID | Paste a Spotify album URL or bare album ID directly |
| Playlist by URL/ID | Paste a Spotify playlist URL or ID - extracts metadata and the full tracklist |
| Artist search | Search by artist name, then pick from up to 5 results |
| Artist by URL/ID | Paste a Spotify artist URL or ID - extracts metadata, top tracks, and discography |

Both full URLs (`https://open.spotify.com/album/...`) and locale-prefixed URLs (`/intl-xx/album/...`) are accepted, as well as raw Spotify URIs (`spotify:album:...`), for albums, playlists, and artists alike.

After displaying results, the tool asks whether to save them. If saving, you choose the export format:

| Format | Contents |
|---|---|
| `txt` | Formatted plain-text summary with full tracklist |
| `csv` | Tracklist rows only (track number, name, artists, duration, explicit, preview URL) |
| `json` | Full album object including metadata and tracklist |

Output files are saved to the same directory as `main.py`. If a file with the same name already exists, a numeric suffix is appended automatically (e.g. `Artist - Album_2.json`).

---

## Example Output (txt)

```
Album:    Discovery
Artist:   Daft Punk
Released: 2001-02-26
Label:    Virgin Records France
Genres:   N/A
Tracks:   14
Runtime:  1h 14m 44s
URL:      https://open.spotify.com/album/...
Cover:    https://i.scdn.co/image/...

Tracklist
------------------------------------------------------------
 1. One More Time (5m 20s) - Daft Punk
 2. Aerodynamic (3m 27s) - Daft Punk
...
```

---

## Notes

- Client Credentials flow is used throughout, so no Spotify account login or OAuth callback is needed.
- Paginated albums (more than 50 tracks) are fetched in full automatically.
- If `SPOTIFY_CLIENT_ID` or `SPOTIFY_CLIENT_SECRET` are missing from `.env`, the tool prints a clear error with the path it searched and exits.

---

---

## Install as a command (pipx)

Install this folder as a CLI so it is available on your PATH:

```bash
pipx install .
spotify-info-extract
```

Logging: set `LOG_LEVEL` (e.g. `DEBUG`) and `LOG_FILE` to also write logs to a file.


## Get the Code

Clone with git:

```bash
git clone https://github.com/drew-codes-things/SpotifyInfoExtract.git
```

Or with the [GitHub CLI](https://cli.github.com/):

```bash
gh repo clone drew-codes-things/SpotifyInfoExtract
```

## License

MIT - made by [Drew](https://github.com/drew-codes-things)
