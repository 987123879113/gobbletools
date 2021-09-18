# Convert videos for use in custom build of MAME with video support hacked in (https://github.com/987123879113/mame/tree/bemani)
# mplayer.exe: https://sourceforge.net/projects/mplayer-win32/files/MPlayer%20and%20MEncoder/r38313%2Bg7ee17ec7e4/MPlayer-x86_64-r38313%2Bg7ee17ec7e4.7z/download
# vcdxrip.exe: https://www.videohelp.com/software/VCDImager
# ffmpeg.exe: https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z

import glob
import os
import re
import shutil
import string
import subprocess
import sys

from pathlib import Path

VCD_MPEG_QUALITY = 0
DVD_MPEG_QUALITY = 8

# Parameters for cropping in the tool to reduce strain on the emulator
OUTPUT_WIDTH = 640
OUTPUT_HEIGHT = 240


def find_tool(toolname, default):
    result = None

    for name in [toolname, default]:
        for ext in [".exe", ""]:
            # Check if tool exists in path
            guess = str(Path(name).with_suffix(ext))
            if shutil.which(guess) is not None:
                result = guess
                break

        if result is not None:
            break

    if result is not None and not sys.platform.startswith('win32'):
        # If the system is non-Windows and only the EXE is available, try using wine to run it.
        # TODO: Not sure how this works with Cygwin.
        result = Path(result)

        if result.suffix.lower() == ".exe":
            return "wine " + str(result)

        return str(result)

    return result


CHDMAN_PATH = find_tool("chdman", Path("videos_iidx", "tools", "chdman"))
assert CHDMAN_PATH != None, "chdman could not be found"
FFMPEG_PATH = find_tool("ffmpeg", Path("videos_iidx", "tools", "ffmpeg"))
assert FFMPEG_PATH != None, "ffmpeg could not be found"
VCDXRIP_PATH = find_tool("vcdxrip", Path("videos_iidx", "tools", "vcdxrip"))
assert VCDXRIP_PATH != None, "vcdxrip could not be found"
MPLAYER_PATH = find_tool("mplayer", Path("videos_iidx", "tools", "mplayer"))
assert MPLAYER_PATH != None, "mplayer could not be found"


def convert_vcd(rom):
    if not rom.exists():
        print("File doesn't exist!", rom)
        return

    Path("videos_iidx", rom.stem).mkdir(parents=True, exist_ok=True)

    input_file = Path("videos_iidx", rom.stem, rom.stem)
    subprocess.run(f'{CHDMAN_PATH} extractcd -i {rom} -o {input_file}.cue -f', shell=True)

    subprocess.run(f'{VCDXRIP_PATH} -b {input_file}.bin', shell=True)

    vcd_output_path = Path(os.getcwd())

    avseq_filenames = []
    with open(Path.joinpath(vcd_output_path, "videocd.xml"), "r") as infile:
        # I don't want to introduce a dependency on lxml just for this so do some regexing
        for match in re.findall(r'\<sequence-item src="([^\"]+)"', infile.read()):
            avseq_filenames.append(str(Path.joinpath(vcd_output_path, match)))

    if not avseq_filenames:
        print("Couldn't find avseq videos!")
        return

    for idx, f in enumerate(avseq_filenames):
        subprocess.run(f'{FFMPEG_PATH} -y -i {f} -c:v mpeg1video -an -q:v {VCD_MPEG_QUALITY} -format mpeg -vf "[in]crop=iw-6:ih:6:0[vid1]; [vid1]scale=w={OUTPUT_WIDTH}:h=ih[vid2]; [vid2]pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:-1:-1[vid]" -bf 0 {Path(input_file.parent, "track%d"%(idx+1))}.mpg -y', shell=True)

        f = Path(f)
        if f.exists():
            f.unlink()

    remove_files = [
        Path(f'{input_file}.cue'),
        Path(f'{input_file}.bin'),
        Path(vcd_output_path, 'videocd.xml'),
    ]
    for f in remove_files:
        if f.exists():
            f.unlink()


def convert_dvd(rom):
    if not rom.exists():
        print("File doesn't exist!", rom)
        return

    Path("videos_iidx", rom.stem).mkdir(parents=True, exist_ok=True)

    input_file = Path("videos_iidx", rom.stem, rom.stem+".iso")
    subprocess.run(f'{CHDMAN_PATH} extractraw -i {rom} -o {input_file} -f', shell=True)

    print("Getting chapter count from DVD...")
    chapter_count = subprocess.check_output(f'{MPLAYER_PATH} -vo null -ao null -frames 0 dvd://0 -dvd-device {input_file} -identify 2>NUL', shell=True).decode()
    chapters_key = 'ID_CHAPTERS='

    if chapters_key not in chapter_count:
        print("Couldn't find chapter count!", chapter_count)
        return

    start_idx = chapter_count.index(chapters_key)+len(chapters_key)
    chapter_count = int("".join([x for x in chapter_count[start_idx:chapter_count.index('\n', start_idx)] if x in string.digits]))

    print("Found %d chapters!" % chapter_count)

    for chapter in range (1, chapter_count+1):
        dumpfile = Path(input_file.parent, "track"+str(chapter)+".vob")
        subprocess.run(f'{MPLAYER_PATH} dvd://0 -dvd-device {input_file} -chapter {chapter}-{chapter} -dumpstream -dumpfile {dumpfile}', shell=True)
        subprocess.run(f'{FFMPEG_PATH} -i {Path(input_file.parent, "track"+str(chapter)+".vob")} -c:v mpeg1video -q:v {DVD_MPEG_QUALITY} -an -format mpeg -vf "[in]crop=iw-24-52:ih:52:0[vid1]; [vid1]scale=w={OUTPUT_WIDTH}:h={OUTPUT_HEIGHT}[vid]" {Path(input_file.parent, "track"+str(chapter)+".mpg")} -y', shell=True)

        if dumpfile.exists():
            dumpfile.unlink()

    if input_file.exists():
        input_file.unlink()

convert_vcd(Path("roms", "bmiidx", "gq863a04.chd"))
convert_vcd(Path("roms", "bmiidx2", "gc985a04.chd"))
convert_vcd(Path("roms", "bmiidx3", "gc992-jaa04.chd"))
convert_vcd(Path("roms", "bmiidx4", "a03jaa02.chd"))
convert_vcd(Path("roms", "bmiidx5", "a17jaa02.chd"))
convert_vcd(Path("roms", "bmiidxs", "gc983a04.chd"))

convert_dvd(Path("roms", "bmiidx6", "b4ujaa02.chd"))
convert_dvd(Path("roms", "bmiidx7", "b44jaa02.chd"))
convert_dvd(Path("roms", "bmiidx8", "c44jaa02.chd"))
