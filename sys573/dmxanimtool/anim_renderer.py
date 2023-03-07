import argparse
import logging
import os
import re

from mdbtool import parse_mdb
from formats.dmx import *

logger = logging.getLogger("dmxanimtool")


def get_re_file_insensitive(f, path):
    results = [os.path.join(path, filename) for filename in os.listdir(path) if re.search(f, filename, re.IGNORECASE)]
    assert (len(results) <= 1)
    return results[0] if results else None



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help="Print lots of debugging statements", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO)
    parser.add_argument('-l', '--log-output', help="Save log to specified output file", default=None)

    parser.add_argument('-m', '--input-data-path', help='Input folder containing game data', required=True)
    parser.add_argument('-s', '--input-mp3-path', help='Input MP3 folder containing decrypted MP3s', default=None)
    parser.add_argument('-i', '--song-id', help='Song ID (4 or 5 letter name found in mdb folder)', required=True)

    parser.add_argument('-o', '--output', help='Output filename', default=None)
    parser.add_argument('-p', '--fps', help='Output video fps', default=60, type=int, choices=range(1,301), metavar="[1-300]")
    parser.add_argument('-f', '--force-overwrite', help='Force overwrite', default=False, action="store_true")

    parser.add_argument('-c', '--cache-path', help='Frame cache path', default="frame_cache")
    parser.add_argument('-r', '--video-path', help='Raw video path (can specify multiple times)', default=[], action='append', nargs='+')
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

    mdb_path = get_re_file_insensitive(r".+_mdb\.bin", args.input_data_path)
    mdb = parse_mdb(mdb_path)

    chart_path = get_re_file_insensitive(re.escape(args.song_id) + "$", args.input_data_path)
    mbk_path = get_re_file_insensitive(re.escape(args.song_id) + ".mbk", args.input_data_path)

    assert (chart_path is not None)
    assert (mbk_path is not None)
    assert (mdb_path is not None)

    song_mp3_filename = get_re_file_insensitive(re.escape("D%04d.mp3" % mdb[args.song_id.lower()]['mp3_full_id']), args.input_mp3_path)
    if song_mp3_filename is None:
        logger.warning("Could not find MP3 for %s, video will be silent" % args.song_id)

    raw_video_render_only = False

    chart_data = bytearray(open(chart_path, "rb").read())
    mbk_data = bytearray(open(mbk_path, "rb").read())

    reader = DmxReader(chart_data, mbk_data)

    jpsxdec_path = os.path.join(args.tools_path, "jpsxdec", "jpsxdec.jar")
    if not os.path.exists(jpsxdec_path):
        logger.error("ERROR: Could not find jPSXdec! %s" % (jpsxdec_path))
    assert (os.path.exists(jpsxdec_path) == True)
    frame_manager = FrameManager(args.cache_path, [os.path.abspath(x[0]) for x in args.video_path], jpsxdec_path)

    renderer = DmxAnimationRenderer(reader, frame_manager)
    renderer.export(output_filename, song_mp3_filename, raw_video_render_only, fps=args.fps)
