import os
import sys
import re
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID") or os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET") or os.getenv("CLIENT_SECRET")

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
    """Accept a raw Spotify ID or a full URL, return just the ID."""
    match = re.search(rf"{kind}/([A-Za-z0-9]+)", url_or_id)
    return match.group(1) if match else url_or_id.strip()


def search_albums(query, limit=5):
    results = sp.search(q=query, type="album", limit=limit)
    return results["albums"]["items"]


def get_album_data(album_id):
    album  = sp.album(album_id)
    tracks = album["tracks"]["items"]
    total_ms = sum(t["duration_ms"] for t in tracks)
    return {
        "name":        album["name"],
        "artists":     ", ".join(a["name"] for a in album["artists"]),
        "release":     album["release_date"],
        "label":       album.get("label", "N/A"),
        "genres":      ", ".join(album.get("genres", [])) or "N/A",
        "total_tracks":album["total_tracks"],
        "runtime":     ms_to_human(total_ms),
        "cover":       album["images"][0]["url"] if album["images"] else "",
        "spotify_url": album["external_urls"]["spotify"],
        "tracks": [
            {
                "number": t["track_number"],
                "name":   t["name"],
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
        lines.append(f"{t['number']:>2}. {t['name']}{explicit}  ({t['duration']})  — {t['artists']}{preview}")
    return "\n".join(lines)


def get_playlist_data(playlist_id):
    pl     = sp.playlist(playlist_id)
    items  = []
    results = pl["tracks"]
    while results:
        for item in results["items"]:
            t = item.get("track")
            if not t or t["type"] != "track":
                continue
            items.append({
                "name":     t["name"],
                "artists":  ", ".join(a["name"] for a in t["artists"]),
                "album":    t["album"]["name"],
                "duration": ms_to_human(t["duration_ms"]),
                "explicit": t["explicit"],
                "added":    item.get("added_at", "")[:10],
                "preview":  t["preview_url"] or "",
            })
        results = sp.next(results) if results["next"] else None

    total_ms = sum(
        item["track"]["duration_ms"]
        for item in pl["tracks"]["items"]
        if item.get("track") and item["track"]["type"] == "track"
    )
    return {
        "name":        pl["name"],
        "owner":       pl["owner"]["display_name"],
        "description": pl["description"] or "N/A",
        "total":       pl["tracks"]["total"],
        "runtime":     ms_to_human(total_ms),
        "url":         pl["external_urls"]["spotify"],
        "cover":       pl["images"][0]["url"] if pl["images"] else "",
        "tracks":      items,
    }


def format_playlist(d):
    lines = [
        f"Playlist:    {d['name']}",
        f"Owner:       {d['owner']}",
        f"Description: {d['description']}",
        f"Tracks:      {d['total']}",
        f"Runtime:     {d['runtime']}",
        f"URL:         {d['url']}",
        f"Cover:       {d['cover']}",
        "",
        "Track list",
        "-" * 60,
    ]
    for i, t in enumerate(d["tracks"], 1):
        explicit = " [E]" if t["explicit"] else ""
        lines.append(f"{i:>3}. {t['name']}{explicit}  ({t['duration']})  — {t['artists']}  [added {t['added']}]")
    return "\n".join(lines)


def search_artists(query, limit=5):
    results = sp.search(q=query, type="artist", limit=limit)
    return results["artists"]["items"]


def get_artist_data(artist_id):
    artist = sp.artist(artist_id)
    albums = sp.artist_albums(artist_id, album_type="album", limit=20)
    top10  = sp.artist_top_tracks(artist_id)
    return {
        "name":       artist["name"],
        "followers":  f"{artist['followers']['total']:,}",
        "popularity": artist["popularity"],
        "genres":     ", ".join(artist["genres"]) or "N/A",
        "url":        artist["external_urls"]["spotify"],
        "image":      artist["images"][0]["url"] if artist["images"] else "",
        "albums":     [(a["name"], a["release_date"]) for a in albums["items"]],
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
        lines.append(f"{i:>2}. {t['name']}  ({t['duration']})  — {t['album']}")
    lines += ["", "Albums", "-" * 60]
    for name, date in d["albums"]:
        lines.append(f"  {date}  {name}")
    return "\n".join(lines)


MODES = {
    "1": "Album search",
    "2": "Album by URL/ID",
    "3": "Playlist by URL/ID",
    "4": "Artist search",
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
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Saved to: {filename}")


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
                query = input("  Search query: ").strip()
                results = search_albums(query)
                if not results:
                    print("  No albums found."); continue
                print()
                album = choose_from_list(results, lambda a: f"{a['name']}  —  {a['artists'][0]['name']}  ({a['release_date'][:4]})")
                data = get_album_data(album["id"])
                content = format_album(data)
                print("\n" + content)
                fname = safe_filename(f"{data['artists']} - {data['name']}") + ".txt"
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content)

            elif mode == "2":
                raw = input("  Album URL or ID: ").strip()
                album_id = extract_spotify_id(raw, "album")
                data = get_album_data(album_id)
                content = format_album(data)
                print("\n" + content)
                fname = safe_filename(f"{data['artists']} - {data['name']}") + ".txt"
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content)

            elif mode == "3":
                raw = input("  Playlist URL or ID: ").strip()
                pl_id = extract_spotify_id(raw, "playlist")
                print("  Fetching playlist (may take a moment for large playlists)...")
                data = get_playlist_data(pl_id)
                content = format_playlist(data)
                print("\n" + content)
                fname = safe_filename(data["name"]) + "_playlist.txt"
                if pick("\n  Save to file? y/n: ", ["y", "n"]) == "y":
                    save(fname, content)

            elif mode == "4":
                query = input("  Artist name: ").strip()
                results = search_artists(query)
                if not results:
                    print("  No artists found."); continue
                print()
                artist = choose_from_list(results, lambda a: f"{a['name']}  ({a['followers']['total']:,} followers)")
                data = get_artist_data(artist["id"])
                content = format_artist(data)
                print("\n" + content)
                fname = safe_filename(data["name"]) + "_artist.txt"
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
