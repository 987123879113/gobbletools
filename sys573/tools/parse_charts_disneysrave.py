import glob
import json
import os
import shutil

import hexdump

USE_TIMESIGS = False

def read_string(data, offset):
    string_bytes = data[offset:data.index(b'\0', offset)]
    return string_bytes.decode('shift-jis').strip('\0')


def convert_raw_chart(found_charts, song_info=None):
    song_id = song_info['song_id']
    bpm = song_info['bpm']

    # Parse ttb file for timestamps
    ttb_by_measure = {}
    ttb_data = bytearray(open(os.path.join("raw_data", "ttb%03d02.bin" % song_id), "rb").read())
    ttb_header = ttb_data[:8]
    ttb_data = ttb_data[8:]

    measure_timestamps = {}
    cur_bars = 0

    bpms = {0: 0}

    song_offset_time = int.from_bytes(ttb_data[2:4], 'little')
    song_offset = (((song_offset_time * 441) / 75) * 100) / 44100
    song_offset = -song_offset

    timing_info_by_bar = {}
    requires_timing_info = False
    last_time_sig = None
    measure_to_beat = {}
    last_measure = 0

    cur_bar_len = 4
    for i in range(4, len(ttb_data) - 4, 4):
        prev_bar_len = cur_bar_len
        cur_time = int.from_bytes(ttb_data[i+2:i+4], 'little')
        prev_time = int.from_bytes(ttb_data[i+2-4:i+4-4], 'little')
        cur_bar_len = int.from_bytes(ttb_data[i-4:i+2-4], 'little')

        cur_timestamp = (((cur_time * 441) / 75) * 100) / 44100
        prev_timestamp = (((prev_time * 441) / 75) * 100) / 44100

        if song_offset is None:
            song_offset = -prev_timestamp

        d = (cur_bar_len / 4) * 4 if USE_TIMESIGS else 4
        cur_bpm = 1 / (((cur_timestamp - prev_timestamp) * (1000 / d)) / 60000)

        # print(cur_bars, "%04x (%f) %04x (%f)" % (prev_time, prev_timestamp, cur_time, cur_timestamp), cur_bpm, cur_bar_len)

        if last_time_sig is None or cur_bar_len != last_time_sig:
            timing_info_by_bar[cur_bars] = cur_bar_len
            last_time_sig = cur_bar_len

            if cur_bar_len != 4:
                requires_timing_info = True

        bpms[cur_bars] = cur_bpm
        cur_bars += cur_bar_len if USE_TIMESIGS else 4

        if cur_bar_len != 4:
            print("Found bar of %d in %s" % (cur_bar_len, song_info['title']))

    ### Handle conversion of chart
    chart = """#TITLE:%s;
#MUSIC:bgm.mp3;
#PREVIEW:preview.mp3;
#OFFSET:%lf;
#BPMS:%s;
#DISPLAYBPM:%d;
""" % (song_info.get('title', '(Untitled)'), song_offset, ",".join(["%d=%f" % (k, bpms[k]) for k in bpms]), song_info.get('bpm', 128))

    if requires_timing_info and USE_TIMESIGS:
        chart += "#TIMESIGNATURES:%s;" % (",".join(["%d=%d=4" % (k, timing_info_by_bar[k]) for k in timing_info_by_bar]))

    for idx, data in found_charts:
        chart_type = {
            0: "dance-single",
            1: "dance-single",
            2: "dance-single",
            7: "dance-double",
            8: "dance-double",
        }[idx]

        chart_diff = {
            0: "Easy",
            1: "Medium",
            2: "Hard",
            7: "Easy",
            8: "Medium",
        }[idx]

        diff_rating = {
            0: song_info['diffs']['single']['basic'],
            1: song_info['diffs']['single']['trick'],
            2: song_info['diffs']['single']['maniac'],
            7: song_info['diffs']['double']['basic'],
            8: song_info['diffs']['double']['trick'],
        }[idx]

        chunks = [data[i:i+8] for i in range(0, len(data), 8)]
        events = []
        last_measure = 0

        for chunk in chunks:
            def get_arrows_str(n):
                s = ""
                s += "1" if (n & 8) else "0"
                s += "1" if (n & 4) else "0"
                s += "1" if (n & 2) else "0"
                s += "1" if (n & 1) else "0"
                return s

            measure = chunk[2]
            beat = chunk[3]
            cmd = int.from_bytes(chunk[4:], 'little')

            beat = round((beat / 256) * 192)

            event = {
                'measure': measure,
                'beat': beat,
            }

            if cmd == 4:
                # Is a note
                p1_note = chunk[0]
                p2_note = chunk[1]

                p1_str = get_arrows_str(p1_note)
                p2_str = get_arrows_str(p2_note)

                note_data = p1_str

                if chart_type == "dance-single":
                    if p2_note != 0:
                        print("P2 note has data for single chart")
                        exit(1)

                else:
                    note_data += p2_str

                event['cmd'] = 'note'
                event['data'] = note_data

            elif cmd == 0x100:
                # End song
                event['cmd'] = 'end'
                last_measure = measure + 1

            else:
                print("Unknown cmd value", cmd)
                exit(1)

            events.append(event)

        if song_info is None:
            song_info = {}

        measure_data = {}
        for i in range(last_measure):
            measure_data[i] = []

        measure_data = {}
        for event in events:
            if event['cmd'] != "note":
                continue

            if event['measure'] not in measure_data:
                d = "00000000" if "double" in chart_type else "0000"
                measure_data[event['measure']] = [d] * 192

            # print(event['beat'], len(measure_data[event['measure']]))
            measure_data[event['measure']][event['beat']] = event['data']

        for i in range(last_measure):
            if i not in measure_data:
                d = "00000000" if "double" in chart_type else "0000"
                measure_data[i] = [d]

        arrow_data = "\n,\n".join(["\n".join(measure_data[k]) for k in sorted(list(measure_data.keys()))])

        chart +="""
#NOTES:
     %s:
     :
     %s:
     %d:
     0,0,0,0,0:
%s
;""" % (chart_type, chart_diff, diff_rating, arrow_data)

    return chart



songlist_info = {}
data = bytearray(open("disney_rave.exe", "rb").read())

base_diff = 0x8000f800
songlist_offset = 0x487c
song_count = 0x780 // 0x40

for i in range(0, song_count * 0x40, 0x40):
    chunk = data[songlist_offset+i:songlist_offset+i+0x40]

    song_id = int.from_bytes(chunk[0x06:0x08], 'little')
    is_unlocked = chunk[0]
    unk_flag = chunk[1]
    timing_type = int.from_bytes(chunk[2:4], 'little')
    audio_idx = chunk[0x15]
    bpm = int.from_bytes(chunk[0x04:0x06], 'little')

    diffs = {
        'single': {
            'basic': int.from_bytes(chunk[0x22:0x22+2], 'little') / 2,
            'trick': int.from_bytes(chunk[0x24:0x24+2], 'little') / 2,
            'maniac': int.from_bytes(chunk[0x26:0x26+2], 'little') / 2,
        },
        'double': {
            'basic': int.from_bytes(chunk[0x32:0x32+2], 'little') / 2,
            'trick': int.from_bytes(chunk[0x34:0x34+2], 'little') / 2,
        },
        'couple': {
            'basic': int.from_bytes(chunk[0x2a:0x2a+2], 'little') / 2,
            'trick': int.from_bytes(chunk[0x2c:0x2c+2], 'little') / 2,
            'maniac': int.from_bytes(chunk[0x2e:0x2e+2], 'little') / 2,
        },
    }

    title_ptr = int.from_bytes(chunk[8:8+4], 'little') - base_diff
    title = read_string(data, title_ptr)

    artist_ptr = int.from_bytes(chunk[12:12+4], 'little') - base_diff
    artist = read_string(data, artist_ptr)

    image_ptr = int.from_bytes(chunk[16:16+4], 'little') - base_diff
    image = read_string(data, image_ptr)

    songlist_info[song_id] = {
        'song_id': song_id,
        'title': title,
        'artist': artist,
        'title_image': image,
        'diffs': diffs,
        'bpm': bpm,
        'timing_type': timing_type,
        'is_unlocked': is_unlocked,
        'bgm_filename': "D%04d.MP3" % (audio_idx - 2),
        'preview_filename': "D%04d.MP3" % (audio_idx - 28),
    }

    print(title)
    hexdump.hexdump(chunk)
    print()


for filename in glob.glob("charts/seq*.bin"):
    data = bytearray(open(filename, "rb").read())

    header = data[:0x78]
    data = data[0x78:]

    found_charts = []
    for i in range(0, len(header), 0x0c):
        idx = i // 0x0c
        exists = int.from_bytes(header[i:i+4], 'little')
        length = int.from_bytes(header[i+4:i+8], 'little') * 8
        offset = int.from_bytes(header[i+8:i+12], 'little') * 8

        if exists == 0:
            assert(length == 0 and offset == 0)
            continue

        # print("%d %d %04x %04x | %08x -> %08x (%08x)" % (idx, exists, length, offset, offset, offset + length, len(data)))

        chart_data = data[offset:offset+length]
        found_charts.append((idx, chart_data))

    if len(found_charts) != 5:
        print("Found %d charts in %s" % (len(found_charts), filename))

    basename = os.path.splitext(os.path.basename(filename))[0]
    song_id = int(basename[3:6], 10)

    song_info = songlist_info.get(song_id, None)
    if song_info is not None:
        basename = song_info['title']

    basepath = os.path.join("charts_output", basename)
    os.makedirs(basepath, exist_ok=True)

    for idx, chart in found_charts:
        chart_mapping = {
            0: "single_basic.bin",
            1: "single_trick.bin",
            2: "single_maniac.bin",
            7: "double_basic.bin",
            8: "double_trick.bin",
        }

        chart_filename = chart_mapping.get(idx, "%02d.bin" % idx)

        if idx not in chart_mapping:
            print("Found unknown chart", idx)

        # open(os.path.join(basepath, chart_filename), "wb").write(chart)

    # if "night" in song_info['title'].lower():
    # try:
    chart_converted = convert_raw_chart(found_charts, song_info)
    open(os.path.join(basepath, "chart.sm"), "w").write(chart_converted)
    # except:
    #     print("Couldn't convert %s" % (filename))

    if song_info is not None:
        # json.dump(song_info, open(os.path.join(basepath, "_metadata.json"), "w"), indent=4)

        if 'bgm_filename' in song_info:
            shutil.copyfile(os.path.join("cd_data", song_info['bgm_filename']), os.path.join(basepath, "bgm.mp3"))

        if 'preview_filename' in song_info:
            shutil.copyfile(os.path.join("cd_data", song_info['preview_filename']), os.path.join(basepath, "preview.mp3"))

    # shutil.copyfile(filename, os.path.join(basepath, os.path.basename(filename)))

