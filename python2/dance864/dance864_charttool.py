import json
import os
import shutil
import sys

def convert_chart_to_sm(filename, songlist_entry):
    data = bytearray(open(filename, "rb").read())
    chunks = [data[i:i+8] for i in range(0, len(data), 8) if data[i:i+8] != b"\0\0\0\0\0\0\0\0"]
    events = []

    for chunk_idx, chunk in enumerate(chunks):
        timestamp = int.from_bytes(chunk[0:4], 'little')
        cmd = chunk[4:8]

        print("%04x %08x %02x %02x %02x %02x" % (chunk_idx, timestamp, cmd[0], cmd[1], cmd[2], cmd[3]))

        if cmd[1] == 0x01:
            # Note
            # Note types:
            # 55 = normal
            # 0d = bomb
            # Anything else = special note
            sound_id = int.from_bytes(cmd[2:], 'little')

            print("\tnote[%x]: %04x" % (cmd[0], sound_id))
            events.append({
                "timestamp": timestamp,
                "event": "note",
                "note_id": cmd[0],
                "sound_id": sound_id,
            })

        elif cmd[1] == 0x04:
            # BPM, only used for animations
            bpm = int.from_bytes(cmd[2:], 'little')
            print("\tBPM:", bpm)
            events.append({
                "timestamp": timestamp,
                "event": "bpm",
                "value": bpm,
            })

        elif cmd[1] == 0x05:
            # Start song
            print("\tStart")
            events.append({
                "timestamp": timestamp,
                "event": "start",
            })

        elif cmd[1] == 0x06:
            # End song
            print("\tEnd")
            events.append({
                "timestamp": timestamp,
                "event": "end",
            })

        elif cmd[1] == 0x0a:
            # Measure
            print("\tMeasure:", cmd[2])
            events.append({
                "timestamp": timestamp,
                "event": "measure",
                'value': cmd[2],
            })

        elif cmd[1] == 0x0b:
            # Beat
            print("\tBeat")
            assert(cmd[2:] == b"\xff\xff")
            events.append({
                "timestamp": timestamp,
                "event": "beat",
            })

        elif cmd[1] == 0x0c:
            # Unk, some kind of duration?
            val = int.from_bytes(cmd[2:], 'little')
            print("\tUnk[%d] %04x %d" % (cmd[0], val, val))
            events.append({
                "timestamp": timestamp,
                "event": "unk",
                "target_id": cmd[0],
                "value": val,
            })



    # Generate SM from chart data
    BEAT_QUANT = 192

    bpms = {}
    beat_lookup_by_timestamp = {}
    last_bpm = 0
    cur_bpm = 0
    last_beat = 0
    beat_vals = [x for x in events if x['event'] == "beat" or x['event'] == "end"]

    for event_idx, event in enumerate(events):
        if event['event'] == "beat":
            # Find next beat or end event
            next_event = None

            for event2 in events[event_idx+1:]:
                if event2['event'] in ["beat"]:
                    next_event = event2
                    break

            if next_event['event'] == "end":
                continue

            assert(next_event is not None)

            beat_count = beat_vals.index(event)
            next_beat_count = beat_vals.index(next_event)

            if next_beat_count > last_beat:
                last_beat = next_beat_count

            cur_bpm = 60000 / (next_event['timestamp'] - event['timestamp'])
            if cur_bpm != last_bpm:
                bpms[beat_count] = cur_bpm
                last_bpm = cur_bpm

    last_measure = [x['value'] for x in events if x['event'] == "measure"][-1] + 1
    for event_idx, event in enumerate(events):
        if event['event'] == "measure":
            # Find next beat or end event
            next_event = None

            for event2 in events[event_idx+1:]:
                if event2['event'] in ["measure", "end"]:
                    next_event = event2
                    break

            for i in range(0, BEAT_QUANT):
                k = event['timestamp'] + (((next_event['timestamp'] - event['timestamp']) / BEAT_QUANT) * i)
                beat_lookup_by_timestamp[k] = (event['value'], i)

    note_events_by_beat = []
    for _ in range(5):
        cur_chart = []
        for _ in range(last_measure):
            cur_measure = []
            for _ in range(BEAT_QUANT):
                cur_measure.append(['0', '0', '0', '0'])
            cur_chart.append(cur_measure)
        note_events_by_beat.append(cur_chart)

    for event in events:
        if event['event'] != "note":
            continue

        diff_idx = event['note_id'] // 3

        if event['timestamp'] not in beat_lookup_by_timestamp:
            # Find nearest timestamp
            lower_timestamp = [x for x in beat_lookup_by_timestamp.keys() if x <= event['timestamp']][-1]
            higher_timestamp = [x for x in beat_lookup_by_timestamp.keys() if x >= event['timestamp']][0]

            if abs(lower_timestamp - event['timestamp']) <= abs(higher_timestamp - event['timestamp']):
                current_beat = beat_lookup_by_timestamp[lower_timestamp]
            else:
                current_beat = beat_lookup_by_timestamp[higher_timestamp]

        else:
            current_beat = beat_lookup_by_timestamp[event['timestamp']]

        note_idx = {
            0: 0, # left
            1: 1, # down
            2: 3, # right
        }[event['note_id'] % 3]
        note_events_by_beat[diff_idx][current_beat[0]][current_beat[1]][note_idx] = 'M' if event['sound_id'] == 0x0d else '1'

        # print(diff_idx, current_beat, note_events_by_beat[diff_idx][current_beat[0]][current_beat[1]], event)


    chart = """#TITLE:%s;
    #MUSIC:song.wav;
    #PREVIEW:preview.wav;
    #OFFSET:0;
    #BPMS:%s;
    """ % (songlist_entry['title'], ",".join(["%f=%f" % (k, bpms[k]) for k in bpms]))


    for diff_idx, chart_events in enumerate(note_events_by_beat):
        chart_type, chart_diff = {
            0: ("dance-single", "Beginner"),
            1: ("dance-single", "Easy"),
            2: ("dance-single", "Medium"),
            3: ("dance-single", "Hard"),
            4: ("dance-single", "Challenge"),
        }[diff_idx]
        diff_rating = 1

        arrow_data = ""
        for x_idx, x in enumerate(chart_events):
            for x2_idx, x2 in enumerate(x):
                arrow_data += "".join(x2)
                if x2_idx + 1 != len(x) or (x2_idx + 1 == len(x) and x_idx + 1 != len(chart_events)):
                    arrow_data += "\n"
            if x_idx + 1 != len(chart_events):
                arrow_data += ",\n"

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


OUTPUT_PATH = "converted"
songlist_entries = json.load(open("songlist.json"))

for entry in songlist_entries:
    output_path = os.path.join(OUTPUT_PATH, "%d_%s" % (entry['song_id'], entry['title']))
    os.makedirs(output_path, exist_ok=True)

    # shutil.copyfile(os.path.join("wav", "%08x.vab.wav" % (entry['bgm_file_id'])), os.path.join(output_path, "song.wav"))
    # shutil.copyfile(os.path.join("wav", "%08x.vab.wav" % (entry['preview_file_id'])), os.path.join(output_path, "preview.wav"))

    open(os.path.join(output_path, "chart.sm"), "w").write(
        convert_chart_to_sm(os.path.join("output", "%08x.bin" % entry['chart_file_id']), entry)
    )

    print(entry)
