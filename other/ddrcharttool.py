import argparse
import copy
import json
import os
import shutil
import string
import struct
import sys

from enum import IntEnum

from PIL import Image


class PlaybackMethod(IntEnum):
    Unknown = 0
    Normal = 1
    PingPong = 2
    # Unknown3 = 3


class PlaybackDirection(IntEnum):
    Freeze = 0
    Forward = 1
    Reverse = -1


class AnimationFlags(IntEnum):
    PlaybackNormal = 1
    PlaybackPingPong = 2
    PlaybackForward = 4
    PlaybackReverse = 8


class AnimationCommands(IntEnum):
    Normal = 1
    # NoShift = 2
    # NoShiftStretch = 3
    Speed = 4
    AppendLoopAll = 5
    FreezeFrame = 6
    AppendLoopLast = 7

    Clear = 9


class CsqWriter:
    def __init__(self, chunks):
        self.chunks = chunks

    def export(self, filename):
        if not self.chunks:
            return

        chunk_parsers = {
            'tempo': self.parse_tempo_chunk,
            'events': self.parse_events_chunk,
            'notes': self.parse_note_events_chunk,
            'lamps': self.parse_lamp_events_chunk,
            'anim': self.parse_anim_chunk_raw,
        }

        output = bytearray()

        # These orders are based on the common layout found in DDR Extreme files
        order = ['tempo', 'events', 'notes', 'lamps', 'anim']
        notes_order = ["single-basic", "double-basic", "single-standard", "double-standard", "single-heavy", "double-heavy", "single-beginner", "double-beginner", "single-challenge", "double-challenge", "double-battle", "solo-basic", "solo-standard", "solo-heavy", "solo-beginner", "solo-challenge"]

        for k in order:
            chunks = []

            for chunk in self.chunks:
                if chunk['type'] != k:
                    continue

                chunks.append(chunk)

            # Sort if needed. This is some quick bad code to sort these odd event formats
            if k == "notes":
                sorted_chunks = []

                for k2 in notes_order:
                    for chunk in chunks:
                        if chunk['events']['chart_type'] == k2:
                            sorted_chunks.append(chunk)

                chunks = sorted_chunks

            for chunk in chunks:
                raw_chunk = chunk_parsers.get(chunk['type'], lambda x: [])(chunk)

                output += int.to_bytes(len(raw_chunk) + 4, 4, 'little')
                output += raw_chunk

        output += int.to_bytes(0, 4, 'little')

        open(filename, "wb").write(output)

        return output


    def padded_chunk(self, chunk, pad_len):
        diff = len(chunk) % pad_len

        if diff != pad_len and diff != 0:
            chunk += b'\0' * (pad_len - diff)

        return chunk


    def parse_note_events_chunk(self, chunk):
        chart_type = {
            "single-basic": 0x0114,
            "single-standard": 0x0214,
            "single-heavy": 0x0314,
            "single-beginner": 0x0414,
            "single-challenge": 0x0614,

            "solo-basic": 0x0116,
            "solo-standard": 0x0216,
            "solo-heavy": 0x0316,
            "solo-beginner": 0x0416,
            "solo-challenge": 0x0616,

            "double-basic": 0x0118,
            "double-standard": 0x0218,
            "double-heavy": 0x0318,
            "double-beginner": 0x0418,
            "double-challenge": 0x0618,

            "double-battle": 0x1024,
        }.get(chunk['events']['chart_type'], chunk['events']['chart_type'])

        note_lookup = {
            'p1_l': 0x00,
            'p1_d': 0x01,
            'p1_u': 0x02,
            'p1_r': 0x03,

            'p2_l': 0x04,
            'p2_d': 0x05,
            'p2_u': 0x06,
            'p2_r': 0x07,
        }

        # Sort events so that release events happen directly after their starting event
        sorted_events = []
        freeze_events = []
        for event in chunk['events']['events']:
            if 'freeze_end' in event.get('extra', []):
                freeze_events.append(event)

            else:
                sorted_events.append(event)

        sorted_events = sorted(sorted_events, key=lambda x:sum(x['measure']))

        # # Merge freeze note ends
        # freeze_events_merged = []
        # while freeze_events:
        #     merge = []

        #     for event in freeze_events[::]:
        #         if event['measure'] == freeze_events[0]['measure']:
        #             merge.append(event)
        #             freeze_events.remove(event)

        #     merged_event = merge[0]
        #     for event in merge[1:]:
        #         merged_event['notes'] += event['notes']

        #     merged_event['notes'] = list(set(merged_event['notes']))
        #     freeze_events_merged.append(merged_event)

        # freeze_events = freeze_events_merged

        for event in freeze_events:
            found = False

            # Find where the current measure would be
            for i in range(len(sorted_events)):
                found = False

                if sum(sorted_events[i]['measure']) > sum(event['measure']):
                    start_i = i
                    while i > 0:
                        i -= 1

                        if bool(set(sorted_events[i]['notes']) & set(event['notes'])):
                            print(sorted_events[i], start_i, i)
                            print(event)
                            print()

                            sorted_events.insert(i+1, event)

                            found = True
                            break

                if found:
                    break

            if not found:
                sorted_events.append(event)

        for event in sorted_events:
            print(event)


        output = bytearray()
        output += int.to_bytes(0x03, 2, 'little')
        output += int.to_bytes(chart_type, 2, 'little')
        output += int.to_bytes(len(sorted_events), 2, 'little')
        output += int.to_bytes(0, 2, 'little')

        offset_chunk = bytearray()
        data_chunk = bytearray()
        extra_data_chunk = bytearray()
        for event in sorted_events:
            offset_chunk += struct.pack("<i", int((event['measure'][0] + event['measure'][1]) * 4096))

            note = 0

            for note_str in event['notes']:
                if note_str == "shock":
                    note = 0xff

                else:
                    note |= 1 << note_lookup[note_str]


            if 'freeze_end' in event.get('extra', []):
                data_chunk += int.to_bytes(0, 1, 'little')
                extra_data_chunk += int.to_bytes(note, 1, 'little')
                extra_data_chunk += int.to_bytes(0x01, 1, 'little') # This can change if there are more events, but when are there more events?

            else:
                data_chunk += int.to_bytes(note, 1, 'little')

        output = self.padded_chunk(output + offset_chunk, 4)
        output = self.padded_chunk(output + data_chunk, 2)
        output = self.padded_chunk(output + extra_data_chunk, 4)

        return output


    def parse_tempo_chunk(self, chunk):
        tick_rate = chunk['events'].get('tick_rate', 150)

        output = bytearray()
        output += int.to_bytes(0x01, 2, 'little')
        output += int.to_bytes(tick_rate, 2, 'little')
        output += int.to_bytes(len(chunk['events']['events']), 2, 'little')
        output += int.to_bytes(0, 2, 'little')

        offset_chunk = bytearray()
        timestamp_chunk = bytearray()
        for event in chunk['events']['events']:
            offset_chunk += struct.pack("<i", int((event['measure'][0] + event['measure'][1]) * 4096))
            timestamp_chunk += struct.pack("<i", int(event['timestamp'] * tick_rate))

        output = self.padded_chunk(output + offset_chunk, 4)
        output = self.padded_chunk(output + timestamp_chunk, 4)

        return output


    def parse_events_chunk(self, chunk):
        output = bytearray()
        output += int.to_bytes(0x02, 2, 'little')
        output += int.to_bytes(1, 2, 'little')
        output += int.to_bytes(len(chunk['events']), 2, 'little')
        output += int.to_bytes(0, 2, 'little')

        event_lookup = {
            "start": 0x0202, # Display "Ready?"
            "end": 0x0302, # End of chart
            "clear": 0x0402, # End of stage/move to result screen
        }

        offset_chunk = bytearray()
        data_chunk = bytearray()
        for event in chunk['events']:
            offset_chunk += struct.pack("<i", int((event['measure'][0] + event['measure'][1]) * 4096))
            data_chunk += int.to_bytes(event_lookup.get(event['event'], event['event']), 2, 'little')

        output = self.padded_chunk(output + offset_chunk, 4)
        output = self.padded_chunk(output + data_chunk, 4)

        return output


    def parse_lamp_events_chunk(self, chunk):
        output = bytearray()
        output += int.to_bytes(0x04, 2, 'little')
        output += int.to_bytes(1, 2, 'little')
        output += int.to_bytes(len(chunk['events']), 2, 'little')
        output += int.to_bytes(0, 2, 'little')

        offset_chunk = bytearray()
        data_chunk = bytearray()
        for event in chunk['events']:
            offset_chunk += struct.pack("<i", int((event['measure'][0] + event['measure'][1]) * 4096))
            data_chunk += int.to_bytes(event['event'], 1, 'little')

        output = self.padded_chunk(output + offset_chunk, 4)
        output = self.padded_chunk(output + data_chunk, 4)

        return output


    def parse_anim_chunk_raw(self, chunk):
        output = bytearray()
        output += int.to_bytes(0x05, 2, 'little')
        output += int.to_bytes(0, 2, 'little')
        output += int.to_bytes(len(chunk['events']), 2, 'little')
        output += int.to_bytes(0, 2, 'little')

        common_lookup = {
            "end": 0x14,
            "ccclma": 0x15,
            "ccclca": 0x16,
            "ccddra": 0x17,
            "ccdrga": 0x18,
            "ccheaa": 0x19,
            "ccitaa": 0x1a,
            "ccltaa": 0x1b,
            "ccrgca": 0x1c,
            "ccsaca": 0x1d,
        }

        filenames = []
        for event in chunk['events']:
            if type(event['clip_filename']) is str and event['clip_filename'] not in filenames and event['clip_filename'] not in common_lookup:
                filenames.append(event['clip_filename'])

        offset_chunk = bytearray()
        data_chunk = bytearray()
        for event in chunk['events']:
            offset_chunk += struct.pack("<i", int((event['measure'][0] + event['measure'][1]) * 4096))

            data_chunk += int.to_bytes(event['cmd_raw'], 1, 'little')

            if event['clip_filename'] in filenames:
                data_chunk += int.to_bytes(filenames.index(event['clip_filename']), 1, 'little')

            elif event['clip_filename'] in common_lookup:
                data_chunk += int.to_bytes(common_lookup[event['clip_filename']], 1, 'little')

            else:
                data_chunk += int.to_bytes(0, 1, 'little')

            data_chunk += int.to_bytes(event['param_raw'], 2, 'little')

        output = self.padded_chunk(output + offset_chunk, 4)
        output = self.padded_chunk(output + data_chunk, 4)

        output += int.to_bytes(len(filenames), 4, 'little')
        for filename in filenames:
            chunk = 0

            for i in range(6):
                c = filename[i] if i < len(filename) else 0
                c2 = (ord(c) - 0x61) & 0x1f if c != 0 else 0
                chunk |= (c2 << (5 * i))

            output += int.to_bytes(chunk, 4, 'little')

        output = self.padded_chunk(output, 4)

        return output



class CsqReader:
    def __init__(self, data):
        self.data = data
        self.bpm_list = None
        self.chunks = self.parse()


    def export_json(self, filename=None):
        chunks = []

        for chunk in self.chunks[::]:
            sanitized_events = []

            if chunk['type'] == "tempo":
                sanitized_events = {
                    'tick_rate': chunk['events']['tick_rate'],
                    'events': [],
                }

                for event in sorted(chunk['events']['events'], key=lambda x:x['start_offset']):
                    sanitized_events['events'].append({
                        'measure': event['start_measure'],
                        'timestamp': event['start_timestamp'],
                        '_bpm': event['bpm'],
                    })

                sanitized_events['events'].append({
                    'measure': event['end_measure'],
                    'timestamp': event['end_timestamp'],
                    '_bpm': event['bpm'],
                })

            elif chunk['type'] in ["events", "lamps"]:
                for event in chunk['events']:
                    sanitized_events.append({
                        '_meta_timestamp': event['timestamp'],
                        'measure': event['measure'],
                        'event': event['event'],
                    })

            elif chunk['type'] == "notes":
                sanitized_events = {
                    'chart_type': chunk['events']['chart_type'],
                    'events': [],
                }

                for event in chunk['events']['events']:
                    sanitized_events['events'].append({
                        '_meta_timestamp': event['timestamp'],
                        'measure': event['measure'],
                        'notes': event['notes'],
                    })

                    if 'extra' in event:
                        sanitized_events['events'][-1]['extra'] = event['extra']

            elif chunk['type'] == "anim":
                for event in chunk['events']:
                    sanitized_events.append({
                        '_meta_timestamp': event['timestamp'],
                        'measure': event['measure'],
                        'cmd_raw': event['cmd_raw'],
                        'param_raw': event['param_raw'],
                        'clip_filename': event['clip_filename'],
                    })

            chunk['events'] = sanitized_events

            chunks.append(chunk)

        if filename:
            import json
            json.dump(chunks, open(filename, "w"), indent=4, ensure_ascii=False)

        return chunks


    def calculate_measure(self, value):
        m = int(value / 4096)
        n = (value - (m * 4096)) / 4096
        return (m, n)


    def calculate_timestamp(self, value):
        if not self.bpm_list:
            return None

        for bpm_info in self.bpm_list:
            if value >= bpm_info['start_offset'] and value < bpm_info['end_offset']:
                break

        timestamp = bpm_info['start_timestamp'] + (((value - bpm_info['start_offset']) / 1024) / bpm_info['bpm']) * 60

        return timestamp * 1000


    def calculate_offset(self, value):
        if not self.bpm_list:
            return None

        for bpm_info in self.bpm_list:
            if value >= bpm_info['start_data'] and value < bpm_info['end_data']:
                break

        offset = bpm_info['start_offset'] + (bpm_info['end_offset'] - bpm_info['start_offset']) * ((value - bpm_info['start_data']) / (bpm_info['end_data'] - bpm_info['start_data']))

        return offset


    def get_bpm(self, value):
        if not self.bpm_list:
            return None

        for bpm_info in self.bpm_list:
            if value >= bpm_info['start_offset'] and value < bpm_info['end_offset']:
                break

        return bpm_info['bpm']


    def parse(self):
        data = self.data

        chunks = []

        chunk_parsers = {
            'tempo': self.parse_tempo_chunk,
            'events': self.parse_events_chunk,
            'notes': self.parse_note_events_chunk,
            'lamps': self.parse_lamp_events_chunk,
            # 'anim': self.parse_anim_chunk_raw,
        }

        while data:
            chunk_len = int.from_bytes(data[:4], 'little')

            if len(data) - 4 <= 0:
                break

            chunk_type = int.from_bytes(data[4:6], 'little')
            chunk_raw = data[6:chunk_len]
            data = data[chunk_len:]

            chunks.append({
                'type': {
                    0x01: 'tempo',
                    0x02: 'events',
                    0x03: 'notes',
                    0x04: 'lamps',
                    0x05: 'anim',
                }[chunk_type],
                '_raw': chunk_raw,
            })

        bpm_chunk = None
        for chunk in chunks:
            if chunk['type'] == "tempo":
                chunk['events'] = chunk_parsers.get(chunk['type'], lambda x: [])(chunk['_raw'])
                bpm_chunk = copy.deepcopy(chunk)
                break

        if bpm_chunk is None:
            print("Couldn't find BPM chunk")
            exit(1)

        self.bpm_list = bpm_chunk['events']['events']

        for chunk in chunks:
            chunk['events'] = chunk_parsers.get(chunk['type'], lambda x: [])(chunk['_raw'])

            # if 'anim' in chunk['type']:
            #     render_animation(chunk['events'], "output_anim", mp3_filename, bpm_chunk['events'])

            del chunk['_raw']

        return chunks


    def parse_tempo_chunk(self, data):
        tick_rate = int.from_bytes(data[:2], 'little')
        count = int.from_bytes(data[2:4], 'little')
        assert(int.from_bytes(data[4:6], 'little') == 0)

        time_offsets = [int.from_bytes(data[6+x*4:6+(x+1)*4], 'little', signed=True) for x in range(count)]
        time_data = [max(0, min(int.from_bytes(data[6+x*4:6+(x+1)*4], 'little'), 0x7fff)) for x in range(count, count * 2)]

        sample_rate = 294 * tick_rate

        bpm_changes = []
        for i in range(1, count):
            start_timestamp = time_data[i-1] / tick_rate
            end_timestamp = time_data[i] / tick_rate
            time_delta = (end_timestamp - start_timestamp) * 1000
            offset_delta = (time_offsets[i] - time_offsets[i-1])
            bpm = 60000 / (time_delta / (offset_delta / 1024)) if offset_delta != 0 else 0

            bpm_changes.append({
                'start_offset': time_offsets[i-1],
                'start_measure': self.calculate_measure(time_offsets[i-1]),
                'end_offset': time_offsets[i],
                'end_measure': self.calculate_measure(time_offsets[i]),
                'start_data': time_data[i-1],
                'end_data': time_data[i],
                'start_timestamp': start_timestamp,
                'end_timestamp': end_timestamp,
                'bpm': bpm
            })

        return {
            'tick_rate': tick_rate,
            'events': bpm_changes,
        }


    def parse_events_chunk(self, data):
        assert(int.from_bytes(data[:2], 'little') == 1)
        count = int.from_bytes(data[2:4], 'little')
        assert(int.from_bytes(data[4:6], 'little') == 0)

        event_offsets = [int.from_bytes(data[6+x*4:6+(x+1)*4], 'little', signed=True) for x in range(count)]
        event_data = [int.from_bytes(data[6+(count*4)+x*2:6+(count*4)+(x+1)*2], 'little') for x in range(count)]

        event_lookup = {
            0x0202: "start", # Display "Ready?"
            0x0302: "end", # End of chart
            0x0402: "clear", # End of stage/move to result screen
        }

        events = []
        for i in range(count):
            events.append({
                'offset': event_offsets[i],
                'measure': self.calculate_measure(event_offsets[i]),
                'timestamp': self.calculate_timestamp(event_offsets[i]),
                '_bpm': self.get_bpm(event_offsets[i]),
                'event': event_lookup.get(event_data[i], event_data[i])
            })

        return events


    def parse_note_events_chunk(self, data):
        def clamp(val, boundary):
            if (val % boundary) == 0:
                return val

            return val + (boundary - (val % boundary))

        chart_type = int.from_bytes(data[:2], 'little')
        count = int.from_bytes(data[2:4], 'little')
        assert(int.from_bytes(data[4:6], 'little') == 0)

        chart_type = {
            0x0114: "single-basic",
            0x0214: "single-standard",
            0x0314: "single-heavy",
            0x0414: "single-beginner",
            0x0614: "single-challenge",

            0x0116: "solo-basic",
            0x0216: "solo-standard",
            0x0316: "solo-heavy",
            0x0416: "solo-beginner",
            0x0616: "solo-challenge",

            0x0118: "double-basic",
            0x0218: "double-standard",
            0x0318: "double-heavy",
            0x0418: "double-beginner",
            0x0618: "double-challenge",

            0x1024: "double-battle",
        }.get(chart_type, chart_type)

        event_offsets = [int.from_bytes(data[6+x*4:6+(x+1)*4], 'little', signed=True) for x in range(count)]
        event_data = data[6+(count*4):clamp(6+(count*4)+count, 2)]
        event_extra_data = data[clamp(6+(count*4)+count, 2):]

        events = []
        for offset in event_offsets:
            event = {
                'offset': offset,
                'measure': self.calculate_measure(offset),
                'timestamp': self.calculate_timestamp(offset),
                '_bpm': self.get_bpm(offset),
            }

            note_raw = event_data[0]
            event_data = event_data[1:]

            if note_raw == 0:
                note_raw = event_extra_data[0]
                extra_type = event_extra_data[1]
                event_extra_data = event_extra_data[2:]

                if (extra_type & 1) != 0:
                    event['extra'] = ['freeze_end']

                if (extra_type & ~1) != 0:
                    print("Unknown extra event: %02x" % extra_type)
                    exit(1)

            notes = []
            if note_raw == 0xff:
                notes.append('shock')

            else:
                for i in range(8):
                    if (note_raw & (1 << i)) != 0:
                        if "solo" in chart_type:
                            n = {
                                0x00: 'solo_l',
                                0x01: 'solo_d',
                                0x02: 'solo_u',
                                0x03: 'solo_r',
                                0x04: 'solo_ul',
                                0x06: 'solo_ur',
                            }[i]

                        else:
                            n = {
                                0x00: 'p1_l',
                                0x01: 'p1_d',
                                0x02: 'p1_u',
                                0x03: 'p1_r',
                                0x04: 'p2_l',
                                0x05: 'p2_d',
                                0x06: 'p2_u',
                                0x07: 'p2_r',
                            }[i]

                        notes.append(n)

            event['notes'] = notes

            events.append(event)

        # Add freeze start commands
        events = sorted(events, key=lambda x:x['offset'])
        for i in range(len(events)):
            if "freeze_end" in events[i].get('extra', []):
                for x in range(i-1, -1, -1):
                    if events[i]['notes'] == events[x]['notes']:
                        events[x]['extra'] = events[x].get('extra', []) + ['freeze_start']
                        break

        return {
            'chart_type': chart_type,
            'events': events,
        }


    def parse_lamp_events_chunk(self, data):
        assert(int.from_bytes(data[:2], 'little') == 1)
        count = int.from_bytes(data[2:4], 'little')
        assert(int.from_bytes(data[4:6], 'little') == 0)

        event_offsets = [int.from_bytes(data[6+x*4:6+(x+1)*4], 'little', signed=True) for x in range(count)]
        event_data = [data[6+(count*4)+x] for x in range(count)]

        events = []
        for i in range(count):
            events.append({
                'offset': event_offsets[i],
                'measure': self.calculate_measure(event_offsets[i]),
                'timestamp': self.calculate_timestamp(event_offsets[i]),
                '_bpm': self.get_bpm(event_offsets[i]),
                'event': event_data[i],
            })

        return events


    def parse_anim_chunk_raw(self, data):
        assert(int.from_bytes(data[:2], 'little') == 0) # What is this used for?
        count = int.from_bytes(data[2:4], 'little')
        assert(int.from_bytes(data[4:6], 'little') == 0)

        event_offsets = [int.from_bytes(data[6+x*4:6+(x+1)*4], 'little', signed=True) for x in range(count)]
        event_data = [data[6+(count*4)+x*4:6+(count*4)+(x+1)*4] for x in range(count)]

        filename_chunk_count = int.from_bytes(data[6+(count*8):6+(count*8)+4], 'little')
        filename_chunks = [int.from_bytes(data[6+(count*8)+4+x*4:6+(count*8)+4+(x+1)*4], 'little') for x in range(filename_chunk_count)]

        clip_filenames = []

        for chunk in filename_chunks:
            output_string = ""

            for i in range(6):
                c = chunk & 0x1f

                if c < 0x1b:
                    output_string += chr(c + 0x61)

                chunk >>= 5

            clip_filenames.append(output_string)

        events = []
        last_direction = 1
        for i in range(count):
            cmd = event_data[i][0]
            cmd_upper = (cmd >> 4) & 0x0f

            clip_idx = event_data[i][1]
            param = int.from_bytes(event_data[i][2:4], 'little')

            common_lookup = {
                0x14: "end",
                0x15: "ccclma",
                0x16: "ccclca",
                0x17: "ccddra",
                0x18: "ccdrga",
                0x19: "ccheaa",
                0x1a: "ccitaa",
                0x1b: "ccltaa",
                0x1c: "ccrgca",
                0x1d: "ccsaca",
            }

            clip_filename = common_lookup[clip_idx] if clip_idx in common_lookup else clip_filenames[clip_idx]

            event = {
                'offset': event_offsets[i],
                'measure': self.calculate_measure(event_offsets[i]),
                'timestamp': self.calculate_timestamp(event_offsets[i]),
                '_bpm': self.get_bpm(event_offsets[i]),
                'cmd_raw': cmd,
                'param_raw': param,
                'clip_filename': clip_filename
            }

            events.append(event)

        return events


    def parse_anim_chunk(self, data):
        assert(int.from_bytes(data[:2], 'little') == 0)
        count = int.from_bytes(data[2:4], 'little')
        assert(int.from_bytes(data[4:6], 'little') == 0)

        event_offsets = [int.from_bytes(data[6+x*4:6+(x+1)*4], 'little', signed=True) for x in range(count)]
        event_data = [data[6+(count*4)+x*4:6+(count*4)+(x+1)*4] for x in range(count)]

        filename_chunk_count = int.from_bytes(data[6+(count*8):6+(count*8)+4], 'little')
        filename_chunks = [int.from_bytes(data[6+(count*8)+4+x*4:6+(count*8)+4+(x+1)*4], 'little') for x in range(filename_chunk_count)]

        clip_filenames = []

        for chunk in filename_chunks:
            output_string = ""

            for i in range(6):
                c = chunk & 0x1f

                if c < 0x1b:
                    output_string += chr(c + 0x61)

                chunk >>= 5

            clip_filenames.append(output_string)

        events = []
        last_direction = 1
        for i in range(count):
            cmd = event_data[i][0]
            cmd_upper = (cmd >> 4) & 0x0f

            clip_idx = event_data[i][1]
            clip_offset = int.from_bytes(event_data[i][2:4], 'little')

            common_lookup = {
                0x14: "end",
                0x15: "ccclma",
                0x16: "ccclca",
                0x17: "ccddra",
                0x18: "ccdrga",
                0x19: "ccheaa",
                0x1a: "ccitaa",
                0x1b: "ccltaa",
                0x1c: "ccrgca",
                0x1d: "ccsaca",
            }

            clip_filename = common_lookup[clip_idx] if clip_idx in common_lookup else clip_filenames[clip_idx]

            event = {
                'offset': event_offsets[i],
                'measure': self.calculate_measure(event_offsets[i]),
                'timestamp': self.calculate_timestamp(event_offsets[i]),
                '_bpm': self.get_bpm(event_offsets[i]),
                'cmd_raw': cmd,
                'method': PlaybackMethod.Normal,
                'direction': PlaybackDirection.Freeze,
                'speed': None,
                'clips': [],
            }

            max_frames = 80 # There's a calculation for this, but from what I can tell, it always ends up being 80 frames

            clip = {
                'filename': clip_filename,
                'frame_start': 0,
                'loop': True,
                'stretch': False,
            }

            # Set method
            if (cmd & AnimationFlags.PlaybackNormal) != 0:
                event['method'] = PlaybackMethod.Normal

            elif (cmd & AnimationFlags.PlaybackPingPong) != 0:
                event['method'] = PlaybackMethod.PingPong

            # Set direction
            if (cmd & AnimationFlags.PlaybackForward) != 0 and (cmd & AnimationFlags.PlaybackReverse) == 0:
                event['direction'] = PlaybackDirection.Forward

            elif (cmd & AnimationFlags.PlaybackReverse) != 0 and (cmd & AnimationFlags.PlaybackForward) == 0:
                event['direction'] = PlaybackDirection.Reverse

            if cmd_upper == 7:
                # Freeze just turns into -0 which is still freeze
                event['direction'] = PlaybackDirection.Reverse if last_direction == PlaybackDirection.Forward else PlaybackDirection.Forward

            # Set other params
            if cmd_upper in [0, 8]:
                # ???
                raise Exception("Unknown upper command:", cmd_upper)

            elif cmd_upper in [AnimationCommands.Normal, AnimationCommands.FreezeFrame]:
                # Normal
                clip['frame_start'] = clip_offset

            elif cmd_upper == 2:
                # ???
                clip['frame_start'] = clip_offset
                event['no_shift'] = True

            elif cmd_upper == 3:
                # Seems to have some kind of half time animation?
                clip['frame_start'] = clip_offset
                event['no_shift'] = True
                clip['stretch'] = True
                event['speed'] = 4 * 2 * round(80 / (80 - clip['frame_start']))

            elif cmd_upper == AnimationCommands.Speed:
                if clip_offset == 0:
                    clip_offset = 4

                event['speed'] = clip_offset

            elif cmd_upper == AnimationCommands.AppendLoopAll:
                # Append to previous event, the two will loop continuous as one
                events[-1]['clips'].append(clip)

            elif cmd_upper == AnimationCommands.AppendLoopLast:
                # Append, only loop last clip
                # Plays the first clip normally, then repeats the 2nd clip for the remainder of the time
                # An offset can be specified
                events[-1]['clips'][-1]['loop'] = False
                events[-1]['clips'].append(clip)

            elif cmd_upper == AnimationCommands.Clear:
                # Display nothing
                event['filename'] = None

            if cmd_upper not in [AnimationCommands.AppendLoopAll, AnimationCommands.AppendLoopLast]:
                event['clips'].append(clip)
                events.append(event)

            last_direction = events[-1]['direction']

            # print("Playing %8s from frame %2d @ %8f... %02x speed[%s]" % (clip_filename, clip_offset, event['timestamp'] / 1000, cmd, str(event['speed'])), event)
            # hexdump.hexdump(event_data[i])
            # print()

        return events


    def render_animation(self, events, output_folder, mp3_filename):
        # WARNING!!! This isn't finished! Use at your own risk!
        # The logic requires is roughly implemented but the timings and such are still very rough.
        # In particular, animation speeds seem to be off.
        os.makedirs(output_folder, exist_ok=True)

        raw_frames = {}

        def get_raw_frames(filenames, ext):
            req_frames = []

            for filename in filenames:
                filename += ext

                if not filename in raw_frames:
                    raw_frames[filename] = []

                    with open(os.path.join("ddrextreme_sbs", filename), "rb") as infile:
                        data = bytearray(infile.read())
                        chunks = [data[i:i+0x2000] for i in range(0, len(data), 0x2000)]

                        for frame_idx, chunk in enumerate(chunks):
                            JPSXDEC_COMMAND = "java -jar jpsxdec_v1-00_rev3921/jpsxdec.jar -f {0} -static bs -dim {1}x{2}"

                            frame_filename = "%s_%04d.bin" % (os.path.basename(os.path.splitext(filename)[0]), frame_idx)
                            output_filename = os.path.splitext(frame_filename)[0] + ".png"
                            new_output_filename = os.path.join("mov_cache", output_filename)

                            os.makedirs("mov_cache", exist_ok=True)

                            if not os.path.exists(new_output_filename):
                                cmd = JPSXDEC_COMMAND.format(frame_filename, 304, 176)

                                with open(frame_filename, "wb") as outfile:
                                    outfile.write(chunk)

                                os.system(cmd)
                                os.unlink(frame_filename)

                                shutil.move(output_filename, new_output_filename)

                            # Read raw image
                            frame = Image.open(new_output_filename)
                            raw_frames[filename].append(frame)

                            # os.unlink(output_filename)

                req_frames += raw_frames[filename]

            return req_frames

        empty_frame = Image.new('RGB', (304, 176))

        output_clips = []

        from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
        from moviepy.editor import concatenate_videoclips, VideoClip, AudioFileClip
        import numpy as np

        def get_clip(frames, duration):
            return ImageSequenceClip([np.array(x) for x in frames], fps=len(frames)/(duration/1000))

        output_clips.append(get_clip([empty_frame], events[0]['timestamp']))

        # Calculate all offsets for all events
        offset_fixed = {}

        for idx, event in enumerate(events[:-1]):
            output_frames = []

            max_frames = 80
            speed = event.get('speed', None)
            if speed is None:
                speed = 8 # ?

            highest_frame = 0
            for x in range(0, events[idx+1]['offset'] - event['offset']):
                frame = ((x * max_frames) / (speed * 1024)) % max_frames
                frame_idx = int(frame)

                if frame_idx > highest_frame:
                    highest_frame = frame_idx + 1

            clip_frames = []
            for clip in event['clips']:
                print(clip)

                frames = get_raw_frames([clip['filename']], ".sbs")

                frame_start = clip['frame_start']

                if event['direction'] == PlaybackDirection.Reverse:
                    frames = frames[::-1]

                frames = frames[frame_start:]

                while len(frames) < max_frames:
                    frames += frames

                frames = frames[:max_frames]

                clip_frames.append(frames)

            frame_idx_list = []
            output_frames = []
            cur_dir = event['direction']
            start_frame = None
            clip_idx = 0
            for x in range(0, events[idx+1]['offset'] - event['offset']):
                # Kind of lazy
                # Calculate the value based on the whole number offset, then floor that value to get the "wanted" value.
                # Then take the "wanted" value and caculate backward to find the fractional offset.
                # This can get you the exact timestamp that the frame should occur on in an easy way.
                frame = ((x * max_frames) / (speed * 1024))
                frame_idx = int(frame)

                if frame_idx in frame_idx_list:
                    continue

                frame_idx_list.append(frame_idx)

                offset_frame = ((event['offset'] + x) * max_frames) / (speed * 1024)
                new_offset = (int(offset_frame) * (speed * 1024)) / max_frames
                new_timestamp = self.calculate_timestamp(new_offset)

                frame_idx %= max_frames

                print(frame_idx, new_timestamp, new_offset, len(clip_frames[clip_idx]), highest_frame, frame_start, speed)

                if frame_idx == 0 and start_frame is not None:
                    clip_idx = (clip_idx + 1) % len(clip_frames)

                    if event['method'] == PlaybackMethod.PingPong and cur_dir != PlaybackDirection.Freeze:
                        cur_dir = PlaybackDirection.Reverse if cur_dir == PlaybackDirection.Forward else PlaybackDirection.Forward

                if start_frame is None:
                    start_frame = frame_idx

                if cur_dir == PlaybackDirection.Forward:
                    output_frames.append(clip_frames[clip_idx][frame_idx])

                elif cur_dir == PlaybackDirection.Reverse:
                    output_frames.append(clip_frames[clip_idx][len(clip_frames[clip_idx]) - frame_idx - 1])

                else:
                    output_frames.append(clip_frames[clip_idx][start_frame])

            output_clips.append(get_clip(output_frames, events[idx+1]['timestamp'] - event['timestamp']))

        output_clips.append(get_clip([empty_frame], 1000))

        clip = concatenate_videoclips(output_clips)
        clip.audio = AudioFileClip(mp3_filename)

        clip.write_videofile("output.avi", codec="png", fps=60)


class CmsReader:
    def __init__(self, data):
        self.data = self.convert(data)


    def export_json(self, filename=None):
        # This is code from another tool I had sitting around.
        # I took the lazy way out and just convert it to a SSQ and then using CsqReader
        # instead of writing another chart reader.
        return CsqReader(self.data).export_json(filename)


    def convert(self, chart):
        chunks = []
        while len(chart) > 0:
            chunk_size = int.from_bytes(chart[:4], 'little')

            if chunk_size == 0:
                chunks.append([])
                chart = chart[4:]

            else:
                chunks.append(chart[4:chunk_size])
                chart = chart[chunk_size:]

        new_chunks = []
        for idx, chunk in enumerate(chunks):
            if not chunk:
                continue

            if idx == 0:
                # Tempo change chunk
                count = len(chunk) // 8

                l = bytearray()
                r = bytearray()

                diff = 1
                timing = 0x4b * diff

                for x in range(0, count * 2, 2):
                    idx = x * 4
                    point1 = int.from_bytes(chunk[idx:idx+4], 'little') * diff

                    idx = (x + 1) * 4
                    point2 = int.from_bytes(chunk[idx:idx+4], 'little') * diff

                    l += int.to_bytes(point1, 4, 'little')
                    r += int.to_bytes(point2, 4, 'little')

                chunk = bytearray()
                chunk += int.to_bytes(1, 2, 'little') # Chunk ID
                chunk += int.to_bytes(timing, 2, 'little') # Timing
                chunk += int.to_bytes(count, 4, 'little') # Entry count
                chunk += l
                chunk += r

            else:
                if int.from_bytes(chunk[0x08:0x0c], 'little') != 0xffffffff:
                    print("Didn't find expected header for chart")
                    exit(1)

                chart_type = chunk[0] # 0 = single, 1 = solo??, 2 = double
                is_solo = chart_type == 1 # ??
                is_double = chart_type == 2
                diff = chunk[1]

                events = [(int.from_bytes(chunk[0x0c+i:0x0c+i+4], 'little'), chunk[0x0c+i+4:0x0c+i+8]) for i in range(0, len(chunk) - 0x0c, 8)]
                event_chunks = []
                end_timestamp = None

                for event in events:
                    if int.from_bytes(event[1], 'little') == 0xffffffff:
                        end_timestamp = event[0]
                        break

                    note = 0

                    p1_down = (event[1][0] & 0x10) != 0
                    p1_left = (event[1][0] & 0x01) != 0
                    p1_right = (event[1][1] & 0x10) != 0
                    p1_up = (event[1][1] & 0x01) != 0

                    p2_down = (event[1][2] & 0x10) != 0
                    p2_left = (event[1][2] & 0x01) != 0
                    p2_right = (event[1][3] & 0x10) != 0
                    p2_up = (event[1][3] & 0x01) != 0

                    note = (p1_right << 3) | (p1_up << 2) | (p1_down << 1) | p1_left

                    if is_double:
                        note |= ((p2_right << 3) | (p2_up << 2) | (p2_down << 1) | p2_left) << 4

                    event_chunks.append((event[0], note))

                print("%d %d %d" % (chart_type, diff, len(event_chunks)))

                chunk = bytearray()
                chunk += int.to_bytes(3, 2, 'little')
                chunk += int.to_bytes(0x14 + (chart_type * 2), 1, 'little')
                chunk += int.to_bytes(diff + 1, 1, 'little')
                chunk += int.to_bytes(len(event_chunks), 4, 'little')

                for event in event_chunks:
                    chunk += int.to_bytes(event[0], 4, 'little')

                for event in event_chunks:
                    chunk += int.to_bytes(event[1], 1, 'little')

                if len(chunk) % 4 != 0:
                    chunk += bytearray([0] * (4 - (len(chunk) % 4))) # Padding which this section seems to require

            new_chunks.append(chunk)

        # Generate chart event timing chunk
        chunk = bytearray()
        chunk += int.to_bytes(2, 2, 'little')
        chunk += int.to_bytes(1, 2, 'little')
        chunk += int.to_bytes(5, 4, 'little')

        for x in [0xfffff000, 0xfffff000, 0, end_timestamp - 4096, end_timestamp]:
            chunk += int.to_bytes(x, 4, 'little')

        for x in [0x0104, 0x0201, 0x0202, 0x0203, 0x0204]:
            chunk += int.to_bytes(x, 2, 'big')

        if len(chunk) % 4 != 0:
            chunk += bytearray([0] * (4 - (len(chunk) % 4))) # Padding which this section seems to require

        # Lamp data (filler)
        lamp_chunk = bytearray()
        lamp_chunk += int.to_bytes(4, 2, 'little')
        lamp_chunk += int.to_bytes(1, 2, 'little')
        lamp_chunk += int.to_bytes(1, 4, 'little')
        lamp_chunk += int.to_bytes(0, 4, 'little') # Timestamp
        lamp_chunk += int.to_bytes(0x80, 1, 'little') # Set lamps to "off"

        if len(lamp_chunk) % 4 != 0:
            lamp_chunk += bytearray([0] * (4 - (len(lamp_chunk) % 4))) # Padding which this section seems to require

        # Video data (filler)
        video_chunk = bytearray()
        video_chunk += int.to_bytes(5, 2, 'little')
        video_chunk += int.to_bytes(0, 2, 'little')
        video_chunk += int.to_bytes(2, 4, 'little')
        video_chunk += int.to_bytes(0, 4, 'little') # Start Timestamp
        video_chunk += int.to_bytes(end_timestamp, 4, 'little') # End Timestamp
        video_chunk += int.to_bytes(0x00061d45, 4, 'little') # Video command
        video_chunk += int.to_bytes(0x00061d45, 4, 'little') # Video command
        video_chunk += int.to_bytes(0x00000001, 4, 'little') # Video file reference count
        video_chunk += int.to_bytes(0x00b52649, 4, 'little') # Some kind of video file reference

        if len(video_chunk) % 4 != 0:
            video_chunk += bytearray([0] * (4 - (len(video_chunk) % 4))) # Padding which this section seems to require

        new_chunks = [new_chunks[0]] + [chunk] + new_chunks[1:] #+ [lamp_chunk, video_chunk]
        new_chunks.append([])

        output = bytearray()

        for chunk in new_chunks:
            output += int.to_bytes(len(chunk) + 4 if chunk else 0, 4, 'little')

            if chunk:
                output += chunk

        return output


class SmReader:
    last_measure = [0, 0]
    last_measure_pad = [1, 0.25]

    def __init__(self, filename, tick_rate=150):
        self.tick_rate = tick_rate
        self.sections = self.parse(filename)


    def parse(self, filename):
        sections = []

        chart = open(filename, "r").read()

        # Remove all comments
        chart_cleaned = []
        i = 0
        while i < len(chart):
            if i + 1 < len(chart) and chart[i:i+2] == '//':
                x = i
                i = chart.index('\n', i)

            chart_cleaned += chart[i]
            i += 1

        chart = "".join(chart_cleaned)

        time_events = {
            'bpms': "",
            'stops': "",
        }

        i = 0
        while i < len(chart):
            section = []

            while i < len(chart) and chart[i] != '#':
                i += 1

            if i >= len(chart):
                break

            section = chart[i+1:chart.index(';', i)]

            command = section[:section.index(':')].upper()
            data = section[section.index(':')+1:]

            i += len(section)

            if command == "NOTES":
                sections.append(self.parse_steps(data))

            elif command in ["BPMS", "STOPS"]:
                if data.strip():
                    time_events[command.lower()] = data

        sections.append(self.parse_tempos(time_events))
        sections.append(self.generate_events())

        return sections


    def generate_events(self):
        events = []

        events.append({
            'event': 0x0401,
            'measure': (0, 0),
        })

        events.append({
            'event': 0x0102,
            'measure': (0, 0),
        })

        events.append({
            'event': "start",
            'measure': (1, 0),
        })

        events.append({
            'event': 0x0502,
            'measure': (1, 0),
        })

        # When the chart ends
        events.append({
            'event': "end",
            'measure': (self.last_measure[0] + self.last_measure_pad[0], self.last_measure[1]),
        })

        # When the chart should be cleared
        events.append({
            'event': "clear",
            'measure': (self.last_measure[0] + self.last_measure_pad[0], self.last_measure[1] + self.last_measure_pad[1]),
        })

        return {
            'type': "events",
            'events': events,
        }


    def parse_tempos(self, time_events):
        # TODO: Negative BPMs
        from collections import OrderedDict
        bpm_changes = OrderedDict()

        for k in time_events:
            for a, b in [list(map(float, x.strip().split('='))) for x in time_events[k].split(',') if time_events[k]]:
                if a not in bpm_changes:
                    bpm_changes[a] = []

                bpm_changes[a].append((k, b))

        events = []

        last_timestamp = 0
        last_beat = 0
        last_bpm = 0

        for beat in bpm_changes:
            measure = int(beat * 1024)
            m = int(measure / 4096)
            n = (measure - (m * 4096)) / 4096

            for event_type, value in sorted(bpm_changes[beat], key=lambda x:x[0]):
                event = {
                    'measure': (m, n),
                }

                if event_type == "bpms":
                    timestamp = (((1 / (last_bpm / 60000)) * (beat - last_beat)) / 1000) + last_timestamp if beat != 0 else 0
                    event['bpm'] = value
                    last_bpm = value

                elif event_type == "stops":
                    timestamp = last_timestamp + (((beat - last_beat) / last_bpm) * 60) + value

                last_timestamp = timestamp
                last_beat = beat

                event['timestamp'] = timestamp
                events.append(event)


        if self.last_measure:
            event = {
                'measure': (self.last_measure[0] + self.last_measure_pad[0], self.last_measure[1] + self.last_measure_pad[1]),
            }

            beat = int(sum(event['measure']) * 4096) / 1024
            event['timestamp'] = (((1 / (last_bpm / 60000)) * (beat - last_beat)) / 1000) + last_timestamp

            events.append(event)

        return {
            'type': "tempo",
            'events': {
                'tick_rate': self.tick_rate,
                'events': events,
            }
        }


    def parse_steps(self, data):
        chart_type, desc, difficulty, meter, radar, notes = [x.strip() for x in data.split(':')]

        measures = [x.strip() for x in notes.split(',')]

        events = []
        for measure_idx, measure in enumerate(measures):
            measure_offset = measure_idx * 4096
            beats = measure.split('\n')

            for beat_idx, beat in enumerate(beats):
                beat = beat.strip()

                if not beat.replace("0", ""):
                    continue

                beat_offset = measure_offset + (beat_idx * 1024)
                event = {
                    "measure": [measure_idx, beat_idx / len(beats)],
                    "notes": []
                }

                release_events = []

                for i, c in enumerate(beat):
                    if c in ["1", "2", "3"]:
                        if "solo" in chart_type:
                            n = {
                                0x00: 'solo_l',
                                0x01: 'solo_ul',
                                0x02: 'solo_d',
                                0x03: 'solo_u',
                                0x04: 'solo_ur',
                                0x05: 'solo_r',
                            }[i]

                        else:
                            n = {
                                0x00: 'p1_l',
                                0x01: 'p1_d',
                                0x02: 'p1_u',
                                0x03: 'p1_r',

                                0x04: 'p2_l',
                                0x05: 'p2_d',
                                0x06: 'p2_u',
                                0x07: 'p2_r',
                            }[i]

                        if c in ["2", "3"]:
                            release_events.append({
                                "measure": [measure_idx, beat_idx / len(beats)],
                                "notes": [n],
                                "extra": ['freeze_end' if c == "3" else "freeze_start"],
                            })

                        else:
                            event['notes'].append(n)

                if event['notes']:
                    events.append(event)

                events += release_events

                if release_events or event['notes']:
                    if sum(events[-1]['measure']) > sum(self.last_measure):
                        self.last_measure = events[-1]['measure']


        chart_type_lookup = {
            "dance-single": "single",
            "dance-double": "double",
            "dance-solo": "solo",
        }

        difficulty_lookup = {
            "beginner": "beginner",
            "easy": "basic",
            "medium": "standard",
            "hard": "heavy",
            "challenge": "challenge",
            "edit": "battle",
        }

        if chart_type.lower() not in chart_type_lookup:
            print("Unknown chart type!", chart_type)
            return None

        elif difficulty.lower() not in difficulty_lookup:
            print("Unknown difficulty!", difficulty)
            return None

        return {
            'type': "notes",
            'events': {
                'chart_type': "-".join([chart_type_lookup[chart_type.lower()], difficulty_lookup[difficulty.lower()]]),
                'events': events,
            }
        }


class SmWriter:
    def __init__(self, events):
        self.events = events


    def export(self, filename):
        # Calculate BPMs from tempo timestamps

        bpms = {}
        stops = {}
        for top_event in self.events:
            if top_event['type'] != "tempo":
                continue

            for event in top_event['events']['events']:
                beat = sum(event['measure']) * 4

                if event['_bpm'] == 0:
                    if beat not in stops:
                        stops[beat] = []

                else:
                    bpms[beat] = event['_bpm']

                if beat in stops:
                    stops[beat].append(event['timestamp'])

        for k in stops:
            assert(len(stops[k]) == 2)
            timestamps = sorted(stops[k])
            stops[k] = timestamps[1] - timestamps[0]

        chart = """#TITLE:Untitled;
#MUSIC:song.mp3;
#OFFSET:0;
#BPMS:%s;
#STOPS:%s;
""" % (",".join(["%f=%f" % (k, bpms[k]) for k in bpms]), ",".join(["%f=%f" % (k, stops[k]) for k in stops]))

        last_measure = None
        for top_event in self.events:
            if top_event['type'] != "events":
                continue

            for event in top_event['events']:
                if event['event'] == "end":
                    last_measure = int(sum(event['measure']) + 1)

        for top_event in self.events:
            if top_event['type'] != "notes":
                continue

            chart_type, chart_diff = {
                "single-beginner": ("dance-single", "Beginner"),
                "single-basic": ("dance-single", "Easy"),
                "single-standard": ("dance-single", "Medium"),
                "single-heavy": ("dance-single", "Hard"),
                "single-challenge": ("dance-single", "Challenge"),
                "solo-beginner": ("dance-solo", "Beginner"),
                "solo-basic": ("dance-solo", "Easy"),
                "solo-standard": ("dance-solo", "Medium"),
                "solo-heavy": ("dance-solo", "Hard"),
                "solo-challenge": ("dance-solo", "Challenge"),
                "double-beginner": ("dance-double", "Beginner"),
                "double-basic": ("dance-double", "Easy"),
                "double-standard": ("dance-double", "Medium"),
                "double-heavy": ("dance-double", "Hard"),
                "double-challenge": ("dance-double", "Challenge"),
                "double-battle": ("dance-double", "Edit"),
            }[top_event['events']['chart_type']]

            diff_rating = 1

            measure_data = {}
            for i in range(last_measure):
                measure_data[i] = []

            measure_data = {}
            for event in top_event['events']['events']:
                # print(event)

                measaure = event['measure'][0]
                beat = round(event['measure'][1] * 192)

                if measaure not in measure_data:
                    d = "0000"

                    if "double" in chart_type:
                        d += "0000"
                    elif "solo" in chart_type:
                        d += "00"

                    measure_data[measaure] = [d] * 192

                # print(event['beat'], len(measure_data[event['measure'][0]]))

                note_data = measure_data[measaure][beat]

                for note in event['notes']:
                    note_idx = {
                        "p1_l": 0,
                        "p1_d": 1,
                        "p1_u": 2,
                        "p1_r": 3,
                        "p2_l": 4,
                        "p2_d": 5,
                        "p2_u": 6,
                        "p2_r": 7,

                        "solo_l": 0,
                        "solo_ul": 1,
                        "solo_d": 2,
                        "solo_u": 3,
                        "solo_ur": 4,
                        "solo_r": 5,
                    }[note]

                    note_type = "1"

                    if 'freeze_start' in event.get('extra', []):
                        note_type = "2"

                    elif 'freeze_end' in event.get('extra', []):
                        note_type = "3"

                    note_data = note_data[:note_idx] + note_type + note_data[note_idx+1:]

                measure_data[measaure][beat] = note_data

            for i in range(last_measure):
                if i not in measure_data:
                    d = "0000"

                    if "double" in chart_type:
                        d += "0000"
                    elif "solo" in chart_type:
                        d += "00"

                    measure_data[i] = [d]

            arrow_data = "\n,\n".join(["\n".join(measure_data[k]) for k in sorted(list(measure_data.keys()))])

            if len(top_event['events']['events']) > 0:
                chart +="""
#NOTES:
%s:
:
%s:
%d:
0,0,0,0,0:
%s
;""" % (chart_type, chart_diff, diff_rating, arrow_data)

        open(filename, "w").write(chart)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', help='Input folder', default=None, required=True)
    parser.add_argument('-if', '--input-format', help='Input format', required=True, choices=["ssq", "csq", "cms", "json", "sm"])
    parser.add_argument('-o', '--output', help='Output folder', default=None, required=True)
    parser.add_argument('-of', '--output-format', help='Output format', required=True, choices=["ssq", "csq", "json", "sm"])

    args = parser.parse_args()

    if args.input_format.lower() in ["ssq", "csq"]:
        reader = CsqReader(bytearray(open(args.input, "rb").read()))
        data = reader.export_json()

    elif args.input_format.lower() in ["cms"]:
        reader = CmsReader(bytearray(open(args.input, "rb").read()))
        data = reader.export_json()

    elif args.input_format.lower() == "json":
        import json
        data = json.load(open(args.input))

    elif args.input_format.lower() == "sm":
        reader = SmReader(args.input)
        data = reader.sections

    if args.output_format.lower() == "json":
        json.dump(data, open(args.output, "w"), indent=4, ensure_ascii=False)

    elif args.output_format.lower() in ["ssq", "csq"]:
        csq_writer = CsqWriter(data)
        csq_writer.export(args.output)

    elif args.output_format.lower() == "sm":
        sm_writer = SmWriter(data)
        sm_writer.export(args.output)
