from spotify import SpotifyDownloader

spotify_downloader = SpotifyDownloader(download_path="./downloads/")
spotify_downloader.playlist("https://open.spotify.com/playlist/4NFshdRZa6MdYjbGADyXIy?si=a279f902c1e14794")

from transcoder import Transcoder
Transcoder.convert_playlists("D:\\")