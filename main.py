import os
import sys
import re
import csv
import json
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env")
    sys.exit(1)

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
))

SEP = " - "


def ms_to_human(ms):
    total_s = ms // 1000
    h, rem  = divmod(total_s, 3600)
    m, s    = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


def safe_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '_', name).strip()


def extract_spotify_id(url_or_id, kind):
    match = re.search(rf"{kind}/([A-Za-z0-9]+)", url_or_id)
    return match.group(1) if match else url_or_id.strip()


def search_albums(query, limit=5):
    results = sp.search(q=query, type="album", limit=limit)
    return results["albums"]["items"]


def get_album_tracks_paginated(album):
    """Fetch ALL tracks for an album, following pagination for albums > 50 tracks."""
    tracks = list(album["tracks"]["items"])
    page   = album["tracks"]
    while page["next"]:
        page   = sp.next(page)
        tracks.extend(page["items"])
    return tracks


def get_album_data(album_id):
    album    = sp.album(album_id)
    tracks   = get_album_tracks_paginated(album)
    total_ms = sum(t["duration_ms"] for t in tracks)
    return {
        "name":         album["name"],
        "artists":      ", ".join(a["name"] for a in album["artists"]),
        "release":      album["release_date"],
        "label":        album.get("label", "N/A"),
        "genres":       ", ".join(album.get("genres", [])) or "N/A",
        "total_tracks": len(tracks),
        "runtime":      ms_to_human(total_ms),
        "cover":        album["images"][0]["url"] if album["images"] else "",
        "spotify_url":  album["external_urls"]["spotify"],
        "tracks": [
            {
                "number":   t["track_number"],
                "name":     t["name"],
                "artists":  ", ".join(a["name"] for a in t["artists"]),
                "duration": ms_to_human(t["duration_ms"]),
                "explicit": t["explicit"],
                "preview":  t["preview_url"] or "",
            }
            for t in tracks
        ],
    }


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
        preview  = f"  preview: {t['preview']}" if t["preview"] else ""
        lines.append(f"{t['number']:>2}. {t['name']}{explicit}  ({t['duration']}){SEP}{t['artists']}{preview}")
    return "\n".join(lines)


def search_artists(query, limit=5):
    results = sp.search(q=query, type="artist", limit=limit)
    return results["artists"]["items"]


def get_artist_albums_paginated(artist_id, album_types):
    """Fetch all albums for the given types, paginating through all results."""
    all_albums = []
    for atype in album_types:
        results = sp.artist_albums(artist_id, album_type=atype, limit=50)
        while results:
            all_albums.extend(results["items"])
            results = sp.next(results) if results["next"] else None
    seen   = set()
    unique = []
    for a in all_albums:
        key = (a["name"].lower(), a["release_date"])
        if key not in seen:
            seen.add(key)
            unique.append(a)
    unique.sort(key=lambda a: a["release_date"], reverse=True)
    return unique


def get_artist_data(artist_id, include_singles=False):
    artist      = sp.artist(artist_id)
    album_types = ["album"]
    if include_singles:
        album_types += ["single", "compilation"]
    albums = get_artist_albums_paginated(artist_id, album_types)
    top10  = sp.artist_top_tracks(artist_id)
    return {
        "name":       artist["name"],
        "followers":  f"{artist['followers']['total']:,}",
        "popularity": artist["popularity"],
        "genres":     ", ".join(artist["genres"]) or "N/A",
        "url":        artist["external_urls"]["spotify"],
        "image":      artist["images"][0]["url"] if artist["images"] else "",
        "albums":     [(a["name"], a["release_date"], a["album_type"]) for a in albums],
        "top_tracks": [
            {"name": t["name"], "album": t["album"]["name"], "duration": ms_to_human(t["duration_ms"])}
            for t in top10["tracks"]
        ],
    }


def format_artist(d):
    lines = [
        f"Artist:     {d['name']}",
        f"Followers:  {d['followers']}",
        f"Popularity: {d['popularity']}/100",
        f"Genres:     {d['genres']}",
        f"URL:        {d['url']}",
        f"Image:      {d['image']}",
        "",
        "Top tracks",
        "-" * 60,
    ]
    for i, t in enumerate(d["top_tracks"], 1):
        lines.append(f"{i:>2}. {t['name']}  ({t['duration']}){SEP}{t['album']}")
    lines += ["", "Discography", "-" * 60]
    for name, date, atype in d["albums"]:
        lines.append(f"  {date}  [{atype.upper()}]  {name}")
    return "\n".join(lines)


def search_playlists(query, limit=5):
    results = sp.search(q=query, type="playlist", limit=limit)
    return results["playlists"]["items"]


def get_playlist_data(playlist_id):
    playlist = sp.playlist(playlist_id)
    tracks   = []
    page     = playlist["tracks"]
    while page:
        for item in page["items"]:
            t = item.get("track")
            if not t or t["type"] != "track":
                continue
            tracks.append({
                "number":   len(tracks) + 1,
                "name":     t["name"],
                "artists":  ", ".join(a["name"] for a in t["artists"]),
                "album":    t["album"]["name"],
                "duration": ms_to_human(t["duration_ms"]),
                "explicit": t["explicit"],
                "added_at": item.get("added_at", "")[:10],
            })
        page = sp.next(page) if page["next"] else None
    owner = playlist.get("owner", {})
    return {
        "name":        playlist["name"],
        "owner":       owner.get("display_name") or owner.get("id", "N/A"),
        "description": playlist.get("description") or "N/A",
        "total":       playlist["tracks"]["total"],
        "public":      playlist.get("public"),
        "url":         playlist["external_urls"]["spotify"],
        "cover":       playlist["images"][0]["url"] if playlist.get("images") else "",
        "tracks":      tracks,
    }


def format_playlist(d):
    pub = {True: "Public", False: "Private", None: "Unknown"}.get(d["public"], "Unknown")
    lines = [
        f"Playlist:    {d['name']}",
        f"Owner:       {d['owner']}",
        f"Description: {d['description']}",
        f"Tracks:      {d['total']}",
        f"Visibility:  {pub}",
        f"URL:         {d['url']}",
        f"Cover:       {d['cover']}",
        "",
        "Tracklist",
        "-" * 60,
    ]
    for t in d["tracks"]:
        explicit = " [E]" if t["explicit"] else ""
        added    = f"  added: {t['added_at']}" if t["added_at"] else ""
        lines.append(
            f"{t['number']:>3}. {t['name']}{explicit}  ({t['duration']})"
            f"{SEP}{t['artists']}  [{t['album']}]{added}"
        )
    return "\n".join(lines)


MODES = {
    "1": "Album search",
    "2": "Album by URL/ID",
    "3": "Artist search",
    "4": "Playlist search",
    "5": "Playlist by URL/ID",
}


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


def ask_format(data_type="album"):
    """Ask which export format to use. For artist mode, warn that CSV uses top_tracks."""
    print("  Export format:")
    print("    1. txt (plain text)")
    print("    2. csv")
    print("    3. json")
    if data_type == "artist":
        print("  Note: CSV will export top tracks only. JSON exports all artist data.")
    choice = pick("  Choice: ", ["1", "2", "3"])
    return {"1": "txt", "2": "csv", "3": "json"}[choice]


def save(base_name, content_txt, data_dict=None, data_type="album"):
    """Save content in the user-chosen format.

    data_type is one of: 'album', 'playlist', 'artist'
    For artist CSV, top_tracks is used as the row source.
    For artist JSON, the full data_dict is written.
    When CSV/JSON cannot be produced meaningfully, the user is asked before
    falling back to txt so they can cancel.
    """
    fmt  = ask_format(data_type)
    ext  = fmt
    path = os.path.join(BASE_DIR, f"{base_name}.{ext}")

    if fmt == "txt":
        with open(path, "w", encoding="utf-8") as f:
            f.write(content_txt)

    elif fmt == "csv":
        if data_dict is None:
            ans = pick("  CSV is not available for this export. Save as txt instead? y/n: ", ["y", "n"])
            if ans == "n":
                print("  Save cancelled.")
                return
            path = os.path.join(BASE_DIR, f"{base_name}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content_txt)
        elif data_type == "artist":
            rows = data_dict.get("top_tracks", [])
            if not rows:
                print("  No top tracks available to export as CSV.")
                return
            fields = list(rows[0].keys())
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        else:
            rows = data_dict.get("tracks", [])
            if not rows:
                print("  No tracks available to export as CSV.")
                return
            fields = list(rows[0].keys())
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

    elif fmt == "json":
        if data_dict is None:
            ans = pick("  JSON is not available for this export. Save as txt instead? y/n: ", ["y", "n"])
            if ans == "n":
                print("  Save cancelled.")
                return
            path = os.path.join(BASE_DIR, f"{base_name}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content_txt)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)

    print(f"  Saved to: {path}")


def main():
    print("\n  Spotify Info Extractor")
    print("  " + "-" * 30)

    try:
        while True:
            print("\n  What do you want to extract?")
            for k, v in MODES.items():
                print(f"    {k}. {v}")
            print("    q. Quit")
            mode = pick("  Choice: ", list(MODES.keys()) + ["q"])
            if mode == "q":
                break

            if mode == "1":
                query   = input("  Search query: ").strip()
                results = search_albums(query)
                if not results:
                    print("  No albums found."); continue
                print()
                album   = choose_from_list(results, lambda a: f"{a['name']}{SEP}{a['artists'][0]['name']}  ({a['release_date'][:4]})")
                data    = get_album_data(album["id"])
                content = format_album(data)
                print("\n" + content)
                fname   = safe_filename(f"{data['artists']} - {data['name']}")
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content, data, data_type="album")

            elif mode == "2":
                raw      = input("  Album URL or ID: ").strip()
                album_id = extract_spotify_id(raw, "album")
                data     = get_album_data(album_id)
                content  = format_album(data)
                print("\n" + content)
                fname    = safe_filename(f"{data['artists']} - {data['name']}")
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content, data, data_type="album")

            elif mode == "3":
                query   = input("  Artist name: ").strip()
                results = search_artists(query)
                if not results:
                    print("  No artists found."); continue
                print()
                artist          = choose_from_list(results, lambda a: f"{a['name']}  ({a['followers']['total']:,} followers)")
                include_singles = pick("  Include singles & EPs? y/n: ", ["y", "n"]) == "y"
                data            = get_artist_data(artist["id"], include_singles=include_singles)
                content         = format_artist(data)
                print("\n" + content)
                fname           = safe_filename(data["name"]) + "_artist"
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content, data, data_type="artist")

            elif mode == "4":
                query   = input("  Playlist search query: ").strip()
                results = search_playlists(query)
                if not results:
                    print("  No playlists found."); continue
                print()
                playlist = choose_from_list(
                    results,
                    lambda p: f"{p['name']}  by {p['owner']['display_name'] or p['owner']['id']}  ({p['tracks']['total']} tracks)"
                )
                data    = get_playlist_data(playlist["id"])
                content = format_playlist(data)
                print("\n" + content)
                fname   = safe_filename(data["name"]) + "_playlist"
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content, data, data_type="playlist")

            elif mode == "5":
                raw         = input("  Playlist URL or ID: ").strip()
                playlist_id = extract_spotify_id(raw, "playlist")
                data        = get_playlist_data(playlist_id)
                content     = format_playlist(data)
                print("\n" + content)
                fname       = safe_filename(data["name"]) + "_playlist"
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content, data, data_type="playlist")

            again = pick("\n  Extract something else? y/n: ", ["y", "n"])
            if again == "n":
                break

    except KeyboardInterrupt:
        print("\n  Interrupted.")
    except spotipy.SpotifyException as e:
        print(f"\n  Spotify API error: {e}")

    print("  Done.")


if __name__ == "__main__":
    main()
