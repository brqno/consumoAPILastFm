import os
from dotenv import load_dotenv

load_dotenv()

import requests
import pandas as pd

URL = "https://ws.audioscrobbler.com/2.0"
# Use environment variables when available; fallback to the provided key
API_KEY = os.getenv("LASTFM_API_KEY", "e28d0854009731dced2a241da7ac2d9d")
API_SECRET = os.getenv("LASTFM_API_SECRET", "")
USER = os.getenv("LASTFM_USER", "brqnooT")

def extract_top_artists(limit: int = 10) -> pd.DataFrame:
    params = {
        "method": "chart.getTopArtists",
        "api_key": API_KEY,
        "format": "json",
        "limit": limit
    }
    response = requests.get(URL, params=params)
    response.raise_for_status()
    artists = response.json().get("artists", {}).get("artist", [])

    rows = []
    for a in artists:
        name = a.get("name")
        listeners = a.get("listeners")
        playcount = a.get("playcount")
        try:
            listeners = int(listeners)
        except Exception:
            listeners = 0
        try:
            playcount = int(playcount)
        except Exception:
            playcount = 0
        rows.append({"name": name, "listeners": listeners, "playcount": playcount})

    return pd.DataFrame(rows)

def extract_top_albums(artist: str, limit: int = 5) -> pd.DataFrame:
    params = {
        "method": "artist.getTopAlbums",
        "artist": artist,
        "api_key": API_KEY,
        "format": "json",
        "limit": limit
    }
    response = requests.get(URL, params=params)
    response.raise_for_status()
    albums = response.json().get("topalbums", {}).get("album", [])

    rows = []
    for alb in albums:
        name = alb.get("name")
        playcount = alb.get("playcount")
        try:
            playcount = int(playcount)
        except Exception:
            playcount = 0

        artist_name = None
        if isinstance(alb.get("artist"), dict):
            artist_name = alb.get("artist", {}).get("name")
        if not artist_name:
            artist_name = artist

        rows.append({"name": name, "playcount": playcount, "artist_name": artist_name})

    return pd.DataFrame(rows)


def search_artist(query: str, limit: int = 20) -> pd.DataFrame:
    params = {
        "method": "artist.search",
        "artist": query,
        "api_key": API_KEY,
        "format": "json",
        "limit": limit,
    }
    response = requests.get(URL, params=params)
    response.raise_for_status()
    artists = response.json().get("results", {}).get("artistmatches", {}).get("artist", [])

    rows = []
    for artist in artists:
        name = artist.get("name")
        listeners = artist.get("listeners")
        try:
            listeners = int(listeners)
        except Exception:
            listeners = 0
        rows.append({"Nome do artista": name, "Ouvintes": listeners})

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Ouvintes", ascending=False).head(3).reset_index(drop=True)

    return df


def _get_album_playcount(album_name: str, artist_name: str) -> int:
    params = {
        "method": "album.getinfo",
        "artist": artist_name,
        "album": album_name,
        "api_key": API_KEY,
        "format": "json",
    }
    try:
        response = requests.get(URL, params=params, timeout=10)
        response.raise_for_status()
        album = response.json().get("album", {})
        playcount = album.get("playcount")
        return int(playcount) if playcount is not None else 0
    except Exception:
        return 0


def search_album(query: str, limit: int = 20) -> pd.DataFrame:
    params = {
        "method": "album.search",
        "album": query,
        "api_key": API_KEY,
        "format": "json",
        "limit": limit,
    }
    response = requests.get(URL, params=params)
    response.raise_for_status()
    albums = response.json().get("results", {}).get("albummatches", {}).get("album", [])

    rows = []
    for alb in albums:
        name = alb.get("name")
        artist_name = alb.get("artist") if not isinstance(alb.get("artist"), dict) else alb.get("artist", {}).get("name")
        playcount = _get_album_playcount(name, artist_name) if name and artist_name else 0
        rows.append({"Nome do albúm": name, "Artista": artist_name, "Playcount do Albúm": playcount})

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Playcount do Albúm", ascending=False).head(3).reset_index(drop=True)

    return df


def run_extract(limit_artists: int = 5, limit_albums: int = 3):
    df_artists = extract_top_artists(limit=limit_artists)

    all_albums = []
    for artist in df_artists["name"]:
        try:
            df_albums = extract_top_albums(artist, limit=limit_albums)
            if not df_albums.empty:
                all_albums.append(df_albums)
        except Exception as e:
            print(f"[EXTRACT] Erro ao buscar álbuns de {artist}: {e}")

    if all_albums:
        df_all_albums = pd.concat(all_albums, ignore_index=True)
    else:
        df_all_albums = pd.DataFrame(columns=["name", "playcount", "artist_name"])

    return df_artists, df_all_albums