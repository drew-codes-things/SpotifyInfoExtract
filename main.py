import os
import sys
import re
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


def get_album_data(album_id):
    album    = sp.album(album_id)
    tracks   = album["tracks"]["items"]
    total_ms = sum(t["duration_ms"] for t in tracks)
    return {
        "name":         album["name"],
        "artists":      ", ".join(a["name"] for a in album["artists"]),
        "release":      album["release_date"],
        "label":        album.get("label", "N/A"),
        "genres":       ", ".join(album.get("genres", [])) or "N/A",
        "total_tracks": album["total_tracks"],
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
        lines.append(f"{t['number']:>2}. {t['name']}{explicit}  ({t['duration']})  \u2014 {t['artists']}{preview}")
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
    # De-duplicate by name (some albums appear in multiple markets)
    seen = set()
    unique = []
    for a in all_albums:
        key = (a["name"].lower(), a["release_date"])
        if key not in seen:
            seen.add(key)
            unique.append(a)
    unique.sort(key=lambda a: a["release_date"], reverse=True)
    return unique


def get_artist_data(artist_id, include_singles=False):
    artist     = sp.artist(artist_id)
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
        lines.append(f"{i:>2}. {t['name']}  ({t['duration']})  \u2014 {t['album']}")
    lines += ["", "Discography", "-" * 60]
    for name, date, atype in d["albums"]:
        lines.append(f"  {date}  [{atype.upper()}]  {name}")
    return "\n".join(lines)


MODES = {
    "1": "Album search",
    "2": "Album by URL/ID",
    "3": "Artist search",
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


def save(filename, content):
    path = os.path.join(BASE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
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
                album   = choose_from_list(results, lambda a: f"{a['name']}  \u2014  {a['artists'][0]['name']}  ({a['release_date'][:4]})")
                data    = get_album_data(album["id"])
                content = format_album(data)
                print("\n" + content)
                fname   = safe_filename(f"{data['artists']} - {data['name']}") + ".txt"
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content)

            elif mode == "2":
                raw      = input("  Album URL or ID: ").strip()
                album_id = extract_spotify_id(raw, "album")
                data     = get_album_data(album_id)
                content  = format_album(data)
                print("\n" + content)
                fname    = safe_filename(f"{data['artists']} - {data['name']}") + ".txt"
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content)

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
                fname           = safe_filename(data["name"]) + "_artist.txt"
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content)

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
