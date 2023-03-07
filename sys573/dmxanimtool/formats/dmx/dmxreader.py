import logging

from .constants import *

logger = logging.getLogger("dmxanimtool." + __name__)


class DmxReader:
    def __init__(self, chart_data, mbk_data):
        self.timestamp_vals_by_chunk_id = self._calculate_timestamp_vals_from_chart(chart_data)
        self.movie_events = self._parse_mbk(mbk_data)

    def calculate_absolute_beat_from_timestamp(self, requested_timestamp):
        bpm_events = self.timestamp_vals_by_chunk_id[list(self.timestamp_vals_by_chunk_id.keys())[0]]

        # Pick the last BPM event that starts at or before the requested timestamp
        bpm_event = [x for x in bpm_events if requested_timestamp >= x[0][0]][-1]

        base_timestamp, base_beat_offset = bpm_event[0]
        next_timestamp, next_beat_offset = bpm_event[1]

        # Around 80053d50 in dmx2majp's aout.exe
        while next_beat_offset - base_beat_offset >= 0xffff:
            base_timestamp = (next_timestamp + base_timestamp) // 2
            base_beat_offset = (next_beat_offset + base_beat_offset) // 2

        return base_beat_offset + int(((next_beat_offset - base_beat_offset) * (requested_timestamp - base_timestamp)) / (next_timestamp - base_timestamp))

    def get_anim_events(self):
        return self.movie_events

    def _calculate_timestamp_vals_from_chart(self, data):
        chunk_count = int.from_bytes(data[4:8], 'little')
        chunk_offset = (chunk_count + 2) * 0x14

        timestamp_vals_by_chunk_id = {}
        for i in range(1, chunk_count+1):
            chunk_size = int.from_bytes(data[(i*0x14):(i*0x14)+4], 'little')
            chunk_id = int.from_bytes(data[(i*0x14)+8:(i*0x14)+12], 'little')

            bpm_events = []

            chunk_offset_end = chunk_offset + chunk_size
            for j in range(chunk_offset, chunk_offset_end, 0x14):
                timestamp = int.from_bytes(data[j:j+4], 'little')
                beat_offset = int.from_bytes(data[j+4:j+8], 'little')
                end_bpm_event_idx = int.from_bytes(data[j+8:j+10], 'little')

                if end_bpm_event_idx != 0:
                    next_j = chunk_offset + (end_bpm_event_idx * 0x14)
                    next_timestamp = int.from_bytes(data[next_j:next_j+4], 'little')
                    next_beat_offset = int.from_bytes(data[next_j+4:next_j+8], 'little')
                    bpm_events.append(((timestamp, beat_offset), (next_timestamp, next_beat_offset)))

            bpm_events.insert(0, ((0, 0), bpm_events[0][0]))  # ?

            timestamp_vals_by_chunk_id[chunk_id] = bpm_events

            chunk_offset += chunk_size

        return timestamp_vals_by_chunk_id

    def _parse_mbk(self, data):
        # mbk format:
        # struct mbk_entry {
        # /* 0x00 */ uint16_t type;
        # /* 0x02 */ uint16_t time_offset;
        # /* 0x04 */ char filename[16];
        # /* 0x14 */ uint8_t beats;
        # /* 0x15 */ uint8_t start_frame;
        # /* 0x16 */ int8_t step;
        # /* 0x17-0x1b */ uint8_t unused[5]; // ?
        # /* 0x1c */ int32_t _internal_idx; // An index into an internal struct array containing info about all of the videos on the disc, can ignore
        # }

        event_count = int.from_bytes(data[0:4], 'little')

        events = []
        for event_offset in range(0x20, 0x20 + event_count * 0x20, 0x20):
            chunk = data[event_offset:event_offset+0x20]

            command = int.from_bytes(chunk[0:2], 'little')
            offset = int.from_bytes(chunk[2:4], 'little')
            timestamp = offset / 300
            filename = chunk[4:20].strip(b'\0').decode('ascii')
            param1 = int.from_bytes([chunk[20]], byteorder='little', signed=True)
            param2 = chunk[21]
            param3 = int.from_bytes([chunk[22]], byteorder='little', signed=True)

            events.append({
                'command': AnimationCommands(command),
                'offset': offset,
                'timestamp': timestamp,
                'filename': filename,
                'params': [param1, param2, param3],
            })

        return events
