from moviepy.editor import AudioFileClip
import os

from tqdm import tqdm

CONVERTED_PATH = "./converted"

class Transcoder:

    @staticmethod
    def convert_playlists(path: str):
        print(f"[+] finding playlists in '{path}'")
        dirs = [os.path.join(path, d) for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        print(f"[+] found {len(dirs)} playlists in '{path}'")
        for d in dirs:
            Transcoder.convert_playlist(d)


    def convert_playlist(path: str):
        print(f"[+] converting playlist '{path}'", end="")

        if not os.path.exists(CONVERTED_PATH):
            os.mkdir(CONVERTED_PATH)

        playlist_name = os.path.split(path)[-1]
        converted_playlist_path = os.path.join(CONVERTED_PATH, playlist_name)

        print(f" to converting {converted_playlist_path}")

        if not os.path.exists(converted_playlist_path):
            os.mkdir(converted_playlist_path)

        for file in tqdm(os.listdir(path)):
            out_path = os.path.join(converted_playlist_path, str(file).replace(".mp4", "").replace(".mp3", "") + ".mp3")
            in_path = os.path.join(path, file)
            if not os.path.isfile(in_path) or os.path.exists(out_path): continue

            Transcoder._convert_mp4_to_mp3_(in_path, out_path)

        print(f"[+] done")        

    @staticmethod
    def _convert_mp4_to_mp3_(input_file, output_file):
        try:
            clip = AudioFileClip(input_file)
            clip.write_audiofile(output_file, logger=None)
            clip.close()
        except Exception as e:
            print(f"An error occurred during conversion of {input_file}:", str(e))
