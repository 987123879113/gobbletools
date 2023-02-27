# Master ID reference: https://zenius-i-vanisher.com/ddrmasterlist.txt

import argparse
import logging
import os
import re

from PIL import Image

import tim2png

from formats.csq import *

logger = logging.getLogger("ddranimtool")


def get_re_file_insensitive(f, path):
    results = [os.path.join(path, filename) for filename in os.listdir(path) if re.search(f, filename, re.IGNORECASE)]
    assert (len(results) <= 1)
    return results[0] if results else None


def get_sys573_encoded_mp3_name(title):
    # 800a7714 in DDR Extreme AC
    title = bytearray(title.upper().encode('ascii'))

    # Pad name until it's 5 bytes
    title_sum = sum(title)
    while len(title) < 5:
        title.append((title_sum + (title_sum // 0x1a) * -0x1a + 0x41) & 0xff)

    # Shuffle
    title = bytearray([title[-1]]) + title[:-1]
    title[1], title[3] = title[3], title[1]

    # 800a91e4 in DDR Extreme AC
    for i, c in enumerate(title):
        if c >= 0x30 and c <= 0x39:
            c = ((c - 0x30) * 2) + 0x41

        else:
            t = c - 0x41
            if t < 0x1a:
                if t < 10:
                    c = (t * 2) + 0x42

                elif t < 0x14:
                    c -= 0x1b

        title[i] = c

    return title.decode('ascii')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help="Print lots of debugging statements",
                        action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO)
    parser.add_argument('-l', '--log-output', help="Save log to specified output file", default=None)

    parser.add_argument('-m', '--input-mdb-path', help='Input mdb folder containing song data', required=True)
    parser.add_argument('-s', '--input-mp3-path',
                        help='Input MP3 folder containing decrypted MP3s', default=None)
    parser.add_argument(
        '-i', '--song-id', help='Song ID (4 or 5 letter name found in mdb folder)', required=True)
    parser.add_argument('-o', '--output', help='Output filename', default=None)
    parser.add_argument('-z', '--render-background-image',
                        help='Include background image in rendered video', default=True, action="store_false")
    parser.add_argument('-f', '--force-overwrite', help='Force overwrite', default=False, action="store_true")

    parser.add_argument('-c', '--cache-path', help='Frame cache path', default="frame_cache")
    parser.add_argument('-r', '--video-path', help='Raw video path', default=None)
    parser.add_argument('-t', '--tools-path', help='Tools path', default="tools")

    args = parser.parse_args()

    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    logger.setLevel(args.loglevel)
    stream_logger = logging.StreamHandler()
    stream_logger.setFormatter(log_formatter)
    logger.addHandler(stream_logger)

    if args.log_output is not None:
        file_logger = logging.FileHandler(args.log_output)
        file_logger.setFormatter(log_formatter)
        logger.addHandler(file_logger)

    output_filename = args.output if args.output else os.path.join("output", f"{args.song_id}.mp4")

    if not args.force_overwrite and os.path.exists(output_filename):
        logger.info("File already exists, skipping... %s" % output_filename)
        exit(0)

    os.makedirs(os.path.dirname(output_filename), exist_ok=True)

    logger.info(f"Rendering {args.song_id}...")

    mdb_song_path = get_re_file_insensitive(re.escape(args.song_id) + "$", args.input_mdb_path)
    song_bg_filename = get_re_file_insensitive(
        r'.*_bk\.cmt', mdb_song_path) if args.render_background_image else None
    song_mp3_filename = get_re_file_insensitive(
        r'M..'+re.escape(get_sys573_encoded_mp3_name(args.song_id))+'.*\..*MP3', args.input_mp3_path)
    song_chart_filename = get_re_file_insensitive(r'all\..*sq', mdb_song_path)

    if song_mp3_filename is None:
        logger.warning("Could not find MP3 for %s, video will be silent" % args.song_id)

    assert (song_chart_filename is not None)

    if song_bg_filename is not None:
        # Cropped to match what the actual AC game does.
        # I noticed the PS2 versions seem to use a different crop when looking at YouTube videos for reference.
        bg_image = tim2png.readTimImage(open(song_bg_filename, "rb"), disable_transparency=True)[0]
        top_crop = 25
        bottom_crop = 39
        left_crop = 8
        right_crop = 8
        bg_image = bg_image.crop((left_crop, top_crop, bg_image.width - right_crop, bg_image.height - bottom_crop))

    else:
        bg_image = Image.new('RGB', (304, 176))

    raw_video_render_only = False

    data = bytearray(open(song_chart_filename, "rb").read())
    reader = CsqReader(data)
    bpm_list = reader.get_tempo_events()
    anim_events = reader.get_anim_events()
    timekeeper = reader.timekeeper

    jpsxdec_path = os.path.join(args.tools_path, "jpsxdec", "jpsxdec.jar")
    if not os.path.exists(jpsxdec_path):
        logger.error("ERROR: Could not find jPSXdec! %s" % (jpsxdec_path))
    assert (os.path.exists(jpsxdec_path) == True)
    frame_manager = FrameManager(args.cache_path, args.video_path, jpsxdec_path)

    renderer = CsqAnimationRenderer(anim_events, frame_manager, timekeeper)
    renderer.export(output_filename, song_mp3_filename, bg_image, raw_video_render_only)
