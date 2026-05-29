# SpotifyInfoExtract

A robust Python CLI tool that extracts rich metadata from Spotify (albums, playlists, artists) using Spotipy and saves it as clean, formatted text files.

## Technical Architecture

- **Library**: Spotipy (Spotify Web API wrapper)
- **Auth**: Client Credentials flow (no user login required)
- **Input Support**: Search by name **or** direct URL/ID paste
- **Pagination**: Full support for large playlists via `sp.next()`
- **Output**: Human-readable `.txt` files with consistent formatting

## Key Functions (main.py)

- `ms_to_human(ms)` -> Converts milliseconds to readable duration (e.g. `6m 5s`)
- `safe_filename(name)` -> Sanitizes strings for safe filenames
- `extract_spotify_id(url_or_id, kind)` -> Regex-based ID extraction from URLs
- `get_album_data(album_id)` -> Full album + tracklist with total runtime
- `get_playlist_data(playlist_id)` -> Paginated track fetching + added dates
- `get_artist_data(artist_id)` -> Artist profile + top tracks + discography
- `format_album / format_playlist / format_artist` -> Structured text output
- `main()` -> Interactive menu with 4 modes + save option

## Supported Modes

1. Album search -> select from results
2. Album by URL/ID
3. Playlist by URL/ID (supports very large playlists)
4. Artist search -> profile + top tracks + albums

## File Structure

```
SpotifyInfoExtract/
├── main.py
├── requirements.txt
├── .env.example
├── README.md
└── LICENSE
```

## Installation

### Linux (Recommended - Virtual Environment)

```bash
git clone https://github.com/drew-codes-things/SpotifyInfoExtract.git
cd SpotifyInfoExtract

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### macOS / Windows (Simple Method)

```bash
git clone https://github.com/drew-codes-things/SpotifyInfoExtract.git
cd SpotifyInfoExtract

pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Follow the menu prompts. You can paste full Spotify URLs or just IDs.

## Output Example

```
Album:    OK Computer
Artist:   Radiohead
Released: 1997-06-16
...

Tracklist
------------------------------------------------------------
 1. Airbag                     (4m 44s)  -> Radiohead
```

## Requirements

- Python 3.8+
- Spotify Developer App (Client Credentials)

## License

MIT License
