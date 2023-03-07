import os
import sys

from formats.dmx.frame_manager import FrameManager


movie_folder = "movies"

input_data_folder = sys.argv[1]
input_mp3_folder = sys.argv[2]
input_song_id = sys.argv[3]

print("Processing", input_song_id)

mdb_data = bytearray(open(os.path.join(input_data_folder, "ja_mdb.bin"), "rb").read())
song_entries_start = int.from_bytes(mdb_data[0:4], 'little')
song_entries_len = int.from_bytes(mdb_data[4:8], 'little')
mp3_filename = None
for offset in range(song_entries_start, song_entries_start + song_entries_len, 0x24):
    song_id = mdb_data[offset:offset+6].decode('ascii').strip('\0').strip()
    mp3_id = int.from_bytes(mdb_data[offset+8:offset+10], 'little')

    if song_id == input_song_id:
        mp3_filename = os.path.join(input_mp3_folder, "D%04d.mp3" % mp3_id)
        break

assert(mp3_filename is not None)

chart_path = os.path.join(input_data_folder, input_song_id)
chart_data = bytearray(open(chart_path, "rb").read())

mbk_path = os.path.join(input_data_folder, input_song_id + ".mbk")
mbk_data = bytearray(open(mbk_path, "rb").read())

dmxreader = DmxReader(chart_data, mbk_data)

from formats.dmx.dmxanimationrenderer import DmxAnimationRenderer
frame_manager = FrameManager("frame_cache")
dmxanimrenderer = DmxAnimationRenderer(
    dmxreader.get_anim_events(),
    dmxreader.get_timestamp_vals(),
    frame_manager
)

dmxanimrenderer.export("test.mp4", mp3_filename)
