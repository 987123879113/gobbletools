import sys

data = bytearray(open(sys.argv[1], "rb").read())

tracks = {
    0: [],
    1: [],

    2: [],
    3: [],

    4: [],
    5: [],
}

cur_track = 0
s = 0x8000
for i in range(0, len(data), s):
    chunk = data[i:i+s]
    tracks[cur_track].append(chunk)
    cur_track = (cur_track + 1) % len(tracks.keys())

# Combine left and right channels into one interleaved file
for filename, lidx, ridx in [("track_bgm.bin", 0, 1), ("track_drum.bin", 2, 3), ("track_clap.bin", 4, 5)]:
    with open(filename, "wb") as outfile:
        left = bytearray()
        right = bytearray()

        for chunk in tracks[lidx]:
            left += chunk

        for chunk in tracks[ridx]:
            right += chunk

        assert(len(left) == len(right))

        for i in range(0, len(left), 0x10):
            outfile.write(left[i:i+0x10])
            outfile.write(right[i:i+0x10])

