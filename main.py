import os
import sys
import re
import csv
import json
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException

import logging

_log_handlers = [logging.StreamHandler()]
_log_file = os.environ.get("LOG_FILE")
if _log_file:
    _log_handlers.append(logging.FileHandler(_log_file))
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(levelname)s: %(message)s",
    handlers=_log_handlers,
)
logger = logging.getLogger("spotifyinfoextract")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
CACHE_PATH = os.path.join(BASE_DIR, ".cache")

load_dotenv(ENV_PATH)

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
sp = None

SEP = " - "


def ms_to_human(ms):
    total_s = ms // 1000
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


def safe_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '_', name).strip()


def init_spotify_client():
    global sp
    if sp is not None:
        return True

    if not CLIENT_ID or not CLIENT_SECRET:
        logger.error(f"SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in {ENV_PATH}")
        return False

    try:
        kwargs = dict(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        try:
            from spotipy.cache_handler import CacheFileHandler
            kwargs["cache_handler"] = CacheFileHandler(cache_path=CACHE_PATH)
        except Exception:
            pass
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(**kwargs))
        return True
    except Exception as e:
        logger.error(f"Could not initialize Spotify client: {e}")
        return False


def extract_spotify_id(url_or_id, kind):
    escaped_kind = re.escape(kind)
    match = re.search(
        rf"https?://open\.spotify\.com/(?:intl-[^/]+/)?{escaped_kind}/([A-Za-z0-9]+)",
        url_or_id,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            rf"spotify:{escaped_kind}:([A-Za-z0-9]+)",
            url_or_id,
            flags=re.IGNORECASE,
        )
    return match.group(1) if match else url_or_id.strip()


def search_albums(query, limit=5):
    results = sp.search(q=query, type="album", limit=limit)
    return results["albums"]["items"]


def get_album_tracks_paginated(album):
    tracks = list(album["tracks"]["items"])
    page = album["tracks"]
    while page["next"]:
        page = sp.next(page)
        tracks.extend(page["items"])
    return tracks


def get_album_data(album_id):
    album = sp.album(album_id)
    tracks = get_album_tracks_paginated(album)
    total_ms = sum(t["duration_ms"] for t in tracks)
    return {
        "name": album["name"],
        "artists": ", ".join(a["name"] for a in album["artists"]),
        "release": album["release_date"],
        "label": album.get("label", "N/A"),
        "genres": ", ".join(album.get("genres", [])) or "N/A",
        "total_tracks": len(tracks),
        "runtime": ms_to_human(total_ms),
        "cover": album["images"][0]["url"] if album["images"] else "",
        "spotify_url": album["external_urls"]["spotify"],
        "tracks": [
            {
                "number": t["track_number"],
                "name": t["name"],
                "artists": ", ".join(a["name"] for a in t["artists"]),
                "duration": ms_to_human(t["duration_ms"]),
                "explicit": t["explicit"],
                "preview": t.get("preview_url") or "",
            }
            for t in tracks
        ],
    }


def get_playlist_data(playlist_id):
    pl = sp.playlist(playlist_id)
    items = list(pl["tracks"]["items"])
    page = pl["tracks"]
    while page["next"]:
        page = sp.next(page)
        items.extend(page["items"])

    tracks = []
    total_ms = 0
    for it in items:
        t = it.get("track")
        if not t:
            continue
        dur = t.get("duration_ms") or 0
        total_ms += dur
        tracks.append({
            "number": len(tracks) + 1,
            "name": t["name"],
            "artists": ", ".join(a["name"] for a in t["artists"]),
            "album": t.get("album", {}).get("name", ""),
            "duration": ms_to_human(dur),
            "explicit": t.get("explicit", False),
            "preview": t.get("preview_url") or "",
        })

    return {
        "name": pl["name"],
        "owner": pl["owner"].get("display_name") or pl["owner"].get("id", ""),
        "description": pl.get("description", ""),
        "total_tracks": len(tracks),
        "runtime": ms_to_human(total_ms),
        "cover": pl["images"][0]["url"] if pl.get("images") else "",
        "spotify_url": pl["external_urls"]["spotify"],
        "tracks": tracks,
    }


def format_playlist(d):
    lines = [f"Playlist: {d['name']}", f"Owner:    {d['owner']}"]
    if d["description"]:
        lines.append(f"About:    {d['description']}")
    lines += [
        f"Tracks:   {d['total_tracks']}",
        f"Runtime:  {d['runtime']}",
        f"URL:      {d['spotify_url']}",
        f"Cover:    {d['cover']}",
        "",
        "Tracklist",
        "-" * 60,
    ]
    for t in d["tracks"]:
        explicit = " [E]" if t["explicit"] else ""
        lines.append(f"{t['number']:>3}. {t['name']}{explicit}  ({t['duration']}){SEP}{t['artists']}")
    return "\n".join(lines)


def get_artist_data(artist_id):
    a = sp.artist(artist_id)
    top = sp.artist_top_tracks(artist_id)["tracks"]
    # Spotify's artists/{id}/albums endpoint filters via "include_groups", not the
    # "album_type" query param spotipy forwards here, so the server-side filter is
    # unreliable across API/spotipy versions. Fetch everything and filter client-side.
    albums_raw = sp.artist_albums(artist_id, limit=50)

    albums = []
    seen = set()
    for al in albums_raw.get("items", []):
        if al.get("album_type") not in ("album", "single"):
            continue
        key = al["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        albums.append({
            "name": al["name"],
            "release": al.get("release_date", ""),
            "type": al.get("album_type", ""),
        })

    tracks = [{
        "number": i,
        "name": t["name"],
        "artists": ", ".join(x["name"] for x in t["artists"]),
        "album": t.get("album", {}).get("name", ""),
        "duration": ms_to_human(t["duration_ms"]),
        "explicit": t.get("explicit", False),
        "preview": t.get("preview_url") or "",
    } for i, t in enumerate(top, 1)]

    return {
        "name": a["name"],
        "genres": ", ".join(a.get("genres", [])) or "N/A",
        "followers": a.get("followers", {}).get("total"),
        "popularity": a.get("popularity"),
        "spotify_url": a["external_urls"]["spotify"],
        "cover": a["images"][0]["url"] if a.get("images") else "",
        "albums": albums,
        "tracks": tracks,
    }


def format_artist(d):
    followers = f"{d['followers']:,}" if d["followers"] is not None else "N/A"
    lines = [
        f"Artist:     {d['name']}",
        f"Genres:     {d['genres']}",
        f"Followers:  {followers}",
        f"Popularity: {d['popularity']}",
        f"URL:        {d['spotify_url']}",
        f"Cover:      {d['cover']}",
        "",
        "Top Tracks",
        "-" * 60,
    ]
    for t in d["tracks"]:
        explicit = " [E]" if t["explicit"] else ""
        lines.append(f"{t['number']:>2}. {t['name']}{explicit}  ({t['duration']}){SEP}{t['artists']}")
    if d["albums"]:
        lines += ["", "Albums & Singles", "-" * 60]
        for al in d["albums"]:
            yr = al["release"][:4] if al["release"] else "????"
            lines.append(f"  {al['name']} ({yr}) [{al['type']}]")
    return "\n".join(lines)


def format_album(d):
    lines = [
        f"Album:    {d['name']}",
        f"Artist:   {d['artists']}",
        f"Released: {d['release']}",
        f"Label:    {d['label']}",
        f"Genres:   {d['genres']}",
        f"Tracks:   {d['total_tracks']}",
        f"Runtime:  {d['runtime']}",
        f"URL:      {d['spotify_url']}",
        f"Cover:    {d['cover']}",
        "",
        "Tracklist",
        "-" * 60,
    ]
    for t in d["tracks"]:
        explicit = " [E]" if t["explicit"] else ""
        preview = f"  preview: {t['preview']}" if t["preview"] else ""
        lines.append(f"{t['number']:>2}. {t['name']}{explicit}  ({t['duration']}){SEP}{t['artists']}{preview}")
    return "\n".join(lines)


def pick(prompt, options):
    while True:
        ans = input(prompt).strip()
        if ans in options:
            return ans
        print(f"  Please enter one of: {', '.join(options)}")


def choose_from_list(items, label_fn):
    for i, item in enumerate(items, 1):
        print(f"  {i}. {label_fn(item)}")
    while True:
        raw = input("Select number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1]
        print("  Invalid choice.")


def ask_format():
    print("  Export format:")
    print("    1. txt (plain text)")
    print("    2. csv")
    print("    3. json")
    choice = pick("  Choice: ", ["1", "2", "3"])
    return {"1": "txt", "2": "csv", "3": "json"}[choice]


def next_available_path(target_path):
    if not os.path.exists(target_path):
        return target_path
    stem, extension = os.path.splitext(target_path)
    counter = 2
    while True:
        candidate = f"{stem}_{counter}{extension}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def save_output(base_name, content_txt, data_dict):
    fmt = ask_format()
    path = os.path.join(BASE_DIR, f"{base_name}.{fmt}")
    saved_path = next_available_path(path)

    if fmt == "txt":
        with open(saved_path, "w", encoding="utf-8") as f:
            f.write(content_txt)

    elif fmt == "csv":
        rows = data_dict.get("tracks", [])
        if not rows:
            print("  No tracks available to export as CSV.")
            return
        fields = list(rows[0].keys())
        with open(saved_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    elif fmt == "json":
        with open(saved_path, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)

    print(f"  Saved to: {saved_path}")


def main():
    print("\n  Spotify Info Extractor")
    print("  " + "-" * 30)
    if not init_spotify_client():
        sys.exit(1)

    modes = {
        "1": "Album search",
        "2": "Album by URL/ID",
        "3": "Playlist by URL/ID",
        "4": "Artist search",
        "5": "Artist by URL/ID",
    }

    try:
        while True:
            print("\n  What do you want to extract?")
            for k, v in modes.items():
                print(f"    {k}. {v}")
            print("    q. Quit")
            mode = pick("  Choice: ", ["1", "2", "3", "4", "5", "q"])
            if mode == "q":
                break

            if mode == "1":
                query = input("  Search query: ").strip()
                results = search_albums(query)
                if not results:
                    print("  No albums found.")
                    continue
                print()
                album = choose_from_list(
                    results,
                    lambda a: f"{a['name']}{SEP}{a['artists'][0]['name']}  ({a['release_date'][:4]})",
                )
                data = get_album_data(album["id"])
                content = format_album(data)
                print("\n" + content)
                fname = safe_filename(f"{data['artists']} - {data['name']}")
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save_output(fname, content, data)

            elif mode == "2":
                raw = input("  Album URL or ID: ").strip()
                album_id = extract_spotify_id(raw, "album")
                data = get_album_data(album_id)
                content = format_album(data)
                print("\n" + content)
                fname = safe_filename(f"{data['artists']} - {data['name']}")
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save_output(fname, content, data)

            elif mode == "3":
                raw = input("  Playlist URL or ID: ").strip()
                playlist_id = extract_spotify_id(raw, "playlist")
                data = get_playlist_data(playlist_id)
                content = format_playlist(data)
                print("\n" + content)
                fname = safe_filename(f"{data['name']} - playlist")
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save_output(fname, content, data)

            elif mode == "4":
                query = input("  Artist name: ").strip()
                results = sp.search(q=query, type="artist", limit=5)["artists"]["items"]
                if not results:
                    print("  No artists found.")
                    continue
                print()
                artist = choose_from_list(
                    results,
                    lambda a: f"{a['name']}  ({a.get('followers', {}).get('total', 0):,} followers)",
                )
                data = get_artist_data(artist["id"])
                content = format_artist(data)
                print("\n" + content)
                fname = safe_filename(f"{data['name']} - artist")
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save_output(fname, content, data)

            elif mode == "5":
                raw = input("  Artist URL or ID: ").strip()
                artist_id = extract_spotify_id(raw, "artist")
                data = get_artist_data(artist_id)
                content = format_artist(data)
                print("\n" + content)
                fname = safe_filename(f"{data['name']} - artist")
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save_output(fname, content, data)

            again = pick("\n  Extract something else? y/n: ", ["y", "n"])
            if again == "n":
                break

    except KeyboardInterrupt:
        print("\n  Interrupted.")
    except SpotifyException as e:
        print(f"\n  Spotify API error: {e}")

    print("  Done.")


if __name__ == "__main__":
    main()
