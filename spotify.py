import os
import json
import requests
import hashlib
from tqdm import tqdm
from pytube import YouTube, Stream, Playlist
import spotipy
from youtube_search import YoutubeSearch
from pathvalidate import sanitize_filename, sanitize_filepath
from datetime import datetime
from dotenv import load_dotenv


class SpotifyScrapper:
    def __init__(self):
        load_dotenv()
        self.access_token_cache = "./.cache/access_token"
        self.CLIENT_ID = os.environ.get("CLIENT_ID")
        self.CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
        self._init_spotify_()

    def _init_spotify_(self):
        self._read_access_token_()
        self.spotify = spotipy.Spotify(self.access_token)
        try:
            self.spotify.user("random")
        except Exception as e:
            if int(e.args[0]) == 401:
                self._update_access_token_()
                self.spotify = spotipy.Spotify(self.access_token)
            else:
                raise e

    def _update_access_token_(self) -> None:
        auth_options = {
            'grant_type': 'client_credentials',
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }
        res = requests.post('https://accounts.spotify.com/api/token', auth_options)
        self.access_token = res.json()['access_token']
        with open(self.access_token_cache, "w+") as file:
            file.write(self.access_token)

    def _read_access_token_(self) -> None:
        try:
            with open(self.access_token_cache, "r") as file:
                self.access_token = file.read()
        except Exception as e:
            if e.args[0] == 2:
                self._update_access_token_()
            else:
                raise e

    @staticmethod
    def _get_track_info_(track) -> dict:
        track = track["track"]
        track_name = track["name"]
        artist_name = track["artists"][0]["name"]
        return {"name": track_name, "artist": artist_name}

    def get_playlist_info(self, id_: str, artist: bool = False) -> dict:
        print("Getting playlist info.", end="")
        result = {}
        if artist:
            result = self.spotify.artist_albums(id_)
        else:
            result = self.spotify.playlist(id_)
        playlist_name = result['name']

        result = result["tracks"]
        total_tracks = result["total"]
        tracks = [self._get_track_info_(track) for track in result["items"]]

        while result["next"]:
            result = self.spotify.next(result)
            tracks += [self._get_track_info_(track) for track in result["items"]]

        print(" [Done]")

        return {"name": playlist_name, "total_tracks": total_tracks, "tracks": tracks}


class SpotifyDownloader:
    def __init__(self, download_path: str = "."):
        self._playlist_name_ = ""
        self._yt_urls_cache_ = "./.cache/yt_urls"
        if download_path == ".":
            self.download_path = os.path.abspath(download_path)
        else:
            self.download_path = download_path
        self._size_ = 0
        self.failed_downloads = {}
        self._log_file_ = open("log.txt", "a+", encoding="utf-8")
        self._spotify_scrapper_ = SpotifyScrapper()

    def __del__(self):
        self._log_file_.write("\n\n")
        self._log_file_.close()
        if len(self.failed_downloads.keys()) > 0:
            with open("failed_log.txt", "a+") as file:
                file.write(f"{datetime.now()}\n")
                json.dump(self.failed_downloads, file)
                file.write("\n\n")

    def _log_(self, msg: str):
        self._log_file_.write(str(datetime.now()))
        self._log_file_.write("\t")
        try:
            self._log_file_.write(msg)
        except Exception as e:
            print(e)

        self._log_file_.write("\n")

    def clear_cache(self):
        print("Clearing Cache", end="")
        if os.path.exists(self._yt_urls_cache_):
            os.remove(self._yt_urls_cache_)
        if os.path.exists(self._spotify_scrapper_.access_token_cache):
            os.remove(self._spotify_scrapper_.access_token_cache)
        print("\rCache Cleared", "\t"*2)

    def yt_playlist(self, url: str):
        try:
            p = Playlist(url)
        except Exception as e:
            self._log_(f"youtube playlist failed {url}")
            raise e
        self._log_(f"downloading youtube playlist {url}")
        print(f"Downloading youtube playlist: {p.title}")

        for ind, url in enumerate(p.video_urls):
            print(f"\r Downloading {ind + 1} / {len(p.video_urls)}", end=" ")
            self._download_url_(url)

    def playlists(self, playlists: list):
        for playlist_url in playlists:
            self.playlist(playlist_url)

    def playlist(self, playlist_url: str):
        playlist_id = playlist_url.split("/")[-1]
        playlist_id = playlist_id.split("?")[0]

        playlist_info = self._spotify_scrapper_.get_playlist_info(playlist_id, "/artist/" in playlist_url)

        self._playlist_name_ = sanitize_filepath(playlist_info["name"])
        self.failed_downloads[self._playlist_name_] = []

        print(f"Downloading playlist {self._playlist_name_}")
        self._log_(f"Downloading playlist {self._playlist_name_}")

        urls = self._get_yt_urls_(playlist_info["tracks"])
        for ind, url in enumerate(urls):
            print(f"\r{ind+1} / {len(urls)}", end=" ")
            try:
                self._download_url_(url)
                self._log_(f"done {url}")
            except Exception as e:
                self._log_(f"failed {url}")
                self.failed_downloads[self._playlist_name_].append({"url": url, "reason": e.args})

        print("\n")
        print(f"{len(self.failed_downloads[self._playlist_name_])} / {len(urls)} Failed")

        with open("failed_log.txt", "a+") as file:
            file.write(f"{datetime.now()} \n")
            json.dump(self.failed_downloads, file)
            file.write("\n\n")
        self.failed_downloads = {}

    def _get_yt_urls_(self, spotify_tracks: list) -> list:
        yt_links_cache = {}
        links = []
        try:
            with open(self._yt_urls_cache_, "r+") as file:
                yt_links_cache = json.load(file)
        except Exception as e:
            if e.args[0] != 2 and 'Expecting value' not in e.args[0]:
                raise e

        for track in tqdm(spotify_tracks, desc="Getting youtube links"):
            hashed_name = hashlib.sha1(f"{track['name']} {track['artist']}".encode()).hexdigest()
            if hashed_name in yt_links_cache.keys():
                links.append(yt_links_cache[hashed_name])
            else:
                results = YoutubeSearch(f"{track['name']} by {track['artist']} audio", max_results=1).to_dict()
                if len(results) == 0:
                    results = YoutubeSearch(f"{track['name']}", max_results=1).to_dict()
                links.append(results[0]["url_suffix"])
                yt_links_cache[hashed_name] = results[0]["url_suffix"]

        with open(self._yt_urls_cache_, "w+") as file:
            json.dump(yt_links_cache, file)

        return links

    @staticmethod
    def _yt_downloaded_callback_(stream: Stream, _):
        print(f"\rDownloaded {stream.title}", end="\t" * 2)

    def _download_url_(self, url):
        yt = YouTube(url)
        print(f"Downloading {yt.title} \t\t\t", end="")

        file_name = f"{yt.title}.mp3"
        file_name = sanitize_filename(file_name)
        full_path = os.path.join(self.download_path, self._playlist_name_)

        if os.path.exists(os.path.join(full_path, file_name)):
            self._log_(f"{yt.title} already downloaded")
            return

        t = yt.streams.get_audio_only()
        t.download(full_path, file_name)
