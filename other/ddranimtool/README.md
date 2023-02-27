# ddranimtool

This tool renders the videos from Sys573 DDR games (MAX and later). It's not perfect but it gets the job done.

## Prerequisites
- Python 3 (tested on 3.9.6)
- Java Runtime Environment (tested with openjdk 17.0.6, other recent versions should work too)
- [jPSXdec](https://github.com/m35/jpsxdec/releases)
- [sys573tool](https://github.com/987123879113/gobbletools/tree/master/sys573/sys573tool)
- [py573a](https://github.com/987123879113/gobbletools/tree/master/sys573/py573a)

## Setup
Install python3 requirements:
```sh
python3 -m pip install -r requirements.txt
```

Extract the jPSXdec binary zip downloaded from the [official releases](https://github.com/m35/jpsxdec/releases) page into the `tools/jpsxdec` folder. Your path should look like `tools/jpsxdec/jpsxdec.jar` if done correctly.

Additional, follow the build steps for sys573tool and py573a to get those working for the following steps.

## How to prepare data

1. (Optional if using a MAME CHD) Extract CHD to CUE/BIN using chdman
```sh
chdman extractcd -i game.chd -o game.cue
```
2. Extract contents of cue/bin (or your CD image or physical CD) to a separate folder.
3. Use [sys573tool](https://github.com/987123879113/gobbletools/tree/master/sys573/sys573tool) to extract the GAME.DAT and CARD.DAT
```sh
python3 sys573tool.py --mode dump --input game_cd_contents --output game_data_extracted
```
This gives you the mdb folder, located at `game_data_extracted/0/mdb`, and the common movies, located at `game_data_extracted/0/movies/common`.
4. Grab required data from game_data_extracted:
- Copy the files from `game_data_extracted/0/movies/common` into `game_cd_contents/MOV`.
- (DDR Extreme only) Copy the files from `game_data_extracted/0/mp3/enc` into `game_cd_contents/DAT`
5. Decrypt all of the MP3 .DATs using [py573a](https://github.com/987123879113/gobbletools/tree/master/sys573/py573a)
```sh
(Linux/macOS)
find game_cd_contents/DAT -type f -iname "*.dat" -exec sh -c 'python3 py573a.py --input "$0" --output "$(echo "$0" | sed "s/\(.*\)\..*/\1/").mp3"' {} \;

(Windows)
for %s in (game_cd_contents/DAT/*.dat) do python3 py573a.py --input "%s" --output "%~ns.mp3"
```
6. (Optional) Prepare video cache. This step may take a significant amount of time so be prepared to wait potentially an hour. Alternatively, the video animation renderer tool will cache the videos it needs on demand if they aren't in the cache already. Letting the tool cache what's needed is recommended if you don't plan on rendering every song.
```sh
python3 video_frame_cacher.py -i game_cd_contents/MOV
```
Expect a full frame cache for each specific game to be somewhere around 2gb-3gb each.

I would recommend creating a new cache folder for every individual game you want to render so as to not run into issues where a video may have changed in some way between game releases. You can use the `-o frame_cache_folder_name` parameter to specify the output cache folder.
```sh
python3 video_frame_cacher.py -i game_cd_contents/MOV -o frame_cache_folder_name
```
### How to render video using anim_renderer.py
```sh
python3 anim_renderer.py -m game_data_extracted/0/mdb -s game_cd_contents/DAT -c frame_cache_folder_name -i song_id
```

Replace the `song_id` value at the end with the 4/5 letter song ID for the song you wish to render. You can reference [this list](https://zenius-i-vanisher.com/ddrmasterlist.txt) to easily figure out what the song ID is for a specific song.

## anim_renderer.py usage
```
usage: anim_renderer.py [-h] [-v] [-l LOG_OUTPUT] -m INPUT_MDB_PATH [-s INPUT_MP3_PATH] -i SONG_ID [-o OUTPUT] [-z] [-f] [-c CACHE_PATH] [-r VIDEO_PATH] [-t TOOLS_PATH]

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Print lots of debugging statements
  -l LOG_OUTPUT, --log-output LOG_OUTPUT
                        Save log to specified output file
  -m INPUT_MDB_PATH, --input-mdb-path INPUT_MDB_PATH
                        Input mdb folder containing song data
  -s INPUT_MP3_PATH, --input-mp3-path INPUT_MP3_PATH
                        Input MP3 folder containing decrypted MP3s
  -i SONG_ID, --song-id SONG_ID
                        Song ID (4 or 5 letter name found in mdb folder)
  -o OUTPUT, --output OUTPUT
                        Output filename
  -z, --render-background-image
                        Include background image in rendered video
  -f, --force-overwrite
                        Force overwrite
  -c CACHE_PATH, --cache-path CACHE_PATH
                        Frame cache path
  -r VIDEO_PATH, --video-path VIDEO_PATH
                        Raw video path
  -t TOOLS_PATH, --tools-path TOOLS_PATH
                        Tools path
```

## video_frame_cacher.py usage
```
usage: video_frame_cacher.py [-h] -i INPUT [-o OUTPUT] [-t TOOLS_PATH]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input path containing raw video files
  -o OUTPUT, --output OUTPUT
                        Output path to store cached video frames
  -t TOOLS_PATH, --tools-path TOOLS_PATH
                        Tools path
```