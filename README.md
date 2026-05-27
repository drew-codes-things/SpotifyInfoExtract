# SpotifyInfoExtract

A Python command-line tool that extracts detailed info from Spotify and saves it to a text file. Supports albums, playlists, and artists — search by name or paste a Spotify URL/ID directly.

Uses the [Spotipy](https://spotipy.readthedocs.io) library with Client Credentials flow — no user login required.

---

## Setup

**Requirements:** Python 3.8+

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

3. Run:
   ```bash
   python main.py
   ```

---

## Getting Spotify API credentials

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app (any name, any description)
3. Copy the **Client ID** and **Client Secret** into your `.env`

No redirect URI or user login is needed — this tool uses the Client Credentials flow which is entirely server-side.

---

## What it extracts

### Album (search or URL/ID)

- Name, artist(s), release date, label, genres
- Full tracklist with track number, duration, explicit flag, and 30-second preview URL
- Total runtime
- Album cover URL
- Spotify link

### Playlist (URL/ID)

- Name, owner, description
- Full paginated tracklist — works on playlists of any size
- Per-track: name, artist(s), album, duration, explicit flag, date added
- Total runtime

### Artist (search)

- Follower count, popularity score, genres
- Top 10 tracks with duration and album name
- Discography (album titles + release dates)

---

## Output

Each extraction prints to the terminal and optionally saves to a `.txt` file named after the album/playlist/artist.

Example output filename: `Radiohead - OK Computer.txt`

---

## Accepting URLs

You can paste a full Spotify URL or just the ID for albums, playlists, and artists:

```
https://open.spotify.com/album/5Z9iiGl2FcIfa3BMiv6OIw
5Z9iiGl2FcIfa3BMiv6OIw          ← both work
```

---

## License

MIT
