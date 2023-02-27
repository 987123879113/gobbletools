import logging

from .constants import *
from .timekeeper import TimeKeeper

logger = logging.getLogger("ddranimtool." + __name__)


class CsqReader:
    def __init__(self, data):
        self.timekeeper = TimeKeeper()
        self.raw_frames = {}
        self.frame_cache = {}

        self.chunks = self.parse_chunks(data)
        self.timekeeper.bpm_list = self.get_tempo_events()

    def parse_chunks(self, data):
        chunks = {}
        data_idx = 0

        while data_idx < len(data):
            chunk_len = int.from_bytes(data[data_idx:data_idx+4], 'little')

            if data_idx + 4 >= len(data):
                break

            chunk_type = int.from_bytes(data[data_idx+4:data_idx+6], 'little')
            chunk_raw = data[data_idx+6:data_idx+chunk_len]
            data_idx += chunk_len

            chunk_type = {
                0x01: 'tempo',
                0x02: 'events',
                0x03: 'notes',
                0x04: 'lamps',
                0x05: 'anim',
            }[chunk_type]
            chunks[chunk_type] = chunk_raw

        return chunks

    def get_tempo_events(self):
        assert ('tempo' in self.chunks)
        data = self.chunks['tempo']

        self.timekeeper.tick_rate = int.from_bytes(data[:2], 'little')
        count = int.from_bytes(data[2:4], 'little')
        assert (int.from_bytes(data[4:6], 'little') == 0)

        time_offsets = [int.from_bytes(data[6+x*4:6+(x+1)*4], 'little', signed=True) for x in range(count)]
        time_data = [int.from_bytes(data[6+x*4:6+(x+1)*4], 'little', signed=True) for x in range(count, count * 2)]

        bpm_changes = []
        for i in range(1, count):
            timestamp_start = time_data[i-1] / self.timekeeper.tick_rate
            timestamp_end = time_data[i] / self.timekeeper.tick_rate
            time_delta = (timestamp_end - timestamp_start) * 1000
            offset_delta = (time_offsets[i] - time_offsets[i-1])
            bpm = 60000 / (time_delta / (offset_delta / 1024)) if offset_delta != 0 else 0

            bpm_changes.append({
                'beat_start': time_offsets[i-1],
                'beat_end': time_offsets[i],
                'music_start': time_data[i-1],
                'music_end': time_data[i],
                'timestamp_start': timestamp_start,
                'timestamp_end': timestamp_end,
                'bpm': bpm
            })

        return bpm_changes

    def get_anim_events(self):
        assert ('anim' in self.chunks)
        data = self.chunks['anim']

        # Ref: 80068224 in DDR Extreme AC
        assert (int.from_bytes(data[:2], 'little') == 0)
        count = int.from_bytes(data[2:4], 'little')
        assert (int.from_bytes(data[4:6], 'little') == 0)

        event_offsets = [int.from_bytes(data[6+x*4:6+(x+1)*4], 'little', signed=True) for x in range(count)]
        event_data = [data[6+(count*4)+x*4:6+(count*4)+(x+1)*4] for x in range(count)]

        filename_chunk_count = int.from_bytes(data[6+(count*8):6+(count*8)+4], 'little')
        filename_chunks = [int.from_bytes(data[6+(count*8)+4+x*4:6+(count*8)+4+(x+1)*4], 'little')
                           for x in range(filename_chunk_count)]

        clip_filenames = []

        for chunk in filename_chunks:
            # Around 80067e90 in DDR Extreme AC
            clip_filename = ""

            for i in range(6):
                c = (chunk >> (5 * i)) & 0x1f
                if c < 0x1b:
                    clip_filename += chr(c + 0x61)

            clip_filenames.append(clip_filename)

        events = []
        for i in range(count):
            import hexdump
            logger.debug(hexdump.dump(event_data[i]))

            cmd = event_data[i][0]
            cmd_upper = (cmd >> 4) & 0x0f

            clip_idx = event_data[i][1]
            clip_offset = event_data[i][2]

            if event_data[i][3] != 0:
                logger.error("ERROR: event_data[i][3] was %02x" % event_data[i][3])
                exit(1)
            assert (event_data[i][3] == 0)

            # TODO: There's a special clip ID, 0x28. What is it?
            # TODO: There's also a case when the clip ID is >= 0x64. What does that do?
            common_clip_filenames = {
                0x14: "ccclca",
                0x15: "ccclma",
                0x16: "cccuba",
                0x17: "ccddra",
                0x18: "ccdrga",
                0x19: "ccheaa",
                0x1a: "ccitaa",
                0x1b: "ccltaa",
                0x1c: "ccrgca",
                0x1d: "ccsaca",
            }

            clip_filename = common_clip_filenames[clip_idx] if clip_idx in common_clip_filenames else clip_filenames[clip_idx]

            event = {
                'offset': event_offsets[i],
                'timestamp': self.timekeeper.calculate_timestamp_from_offset(event_offsets[i]),
                'method': PlaybackMethod.Normal,
                'direction': PlaybackDirection.Freeze,
                'frame_length': 2,
                'frame_start': 0,
                'clips': [],
            }

            clip = {
                'filename': clip_filename,
                'loop': True,
            }

            # Defaults to 1 (normal) if cmd & 3 is not 1, 2, or 3
            event['method'] = {
                AnimationFlags.PlaybackMethodNormal: PlaybackMethod.Normal,
                AnimationFlags.PlaybackMethodPingPong: PlaybackMethod.PingPong,
                AnimationFlags.PlaybackMethodFreeze: PlaybackMethod.Freeze,  # TODO: Verify
            }.get(cmd & 3, PlaybackMethod.Normal)

            # Defaults to 1 (forward) if (cmd >> 2) & 3 is not 0, 1, or 2
            event['direction'] = {
                AnimationFlags.PlaybackDirectionFreeze: PlaybackDirection.Freeze,
                AnimationFlags.PlaybackDirectionForward: PlaybackDirection.Forward,
                AnimationFlags.PlaybackDirectionReverse: PlaybackDirection.Reverse,
            }.get((cmd >> 2) & 3, PlaybackDirection.Forward)

            # Set other params
            max_frames = 80
            if cmd_upper in [AnimationCommands.Play1, AnimationCommands.Play2, AnimationCommands.Play3, AnimationCommands.Play4]:
                # 0x12e4c8 in PS2 DDR Extreme JP
                event['frame_start'] = clip_offset
                event['frame_length'] = {
                    AnimationCommands.Play1: 1,
                    AnimationCommands.Play2: 2,
                    AnimationCommands.Play3: 3,
                    AnimationCommands.Play4: 4,
                }[cmd_upper]

                if event['frame_start'] == 0 and event['direction'] == PlaybackDirection.Reverse:
                    event['frame_start'] = max_frames - 1

            elif cmd_upper == AnimationCommands.PlayStretch:
                event['frame_start'] = 0
                event['frame_length'] = 2
                event['stretch'] = True
                event['frame_speed'] = 4 if clip_offset == 0 else clip_offset

                if event['direction'] == PlaybackDirection.Reverse:
                    event['frame_start'] = max_frames - \
                        (event['frame_start'] + 1)

            elif cmd_upper == AnimationCommands.AppendLoopAll:
                last_val = events[-1].get('frame_speed', 2)
                if clip_offset != 0 and clip_offset != last_val:
                    logger.error("ERROR: append loop all has non-zero parameter!")
                assert (clip_offset == 0 or clip_offset == last_val)
                event['frame_start'] = 0

            elif cmd_upper == AnimationCommands.FreezeFrame:
                # Freeze frame
                event['frame_start'] = clip_offset
                event['frame_length'] = 0

            elif cmd_upper == AnimationCommands.AppendLoopLast:
                if clip_offset != 0:
                    logger.error("ERROR: append loop last has non-zero parameter!")
                assert (clip_offset == 0)

                # Freeze just turns into -0 which is still freeze
                event['direction'] = PlaybackDirection.Reverse if events[-1]['direction'] == PlaybackDirection.Forward else PlaybackDirection.Forward

                # Append, only loop last clip
                # Plays the first clip normally, then repeats the 2nd clip for the remainder of the time
                # An offset can be specified?
                # 0x speed, from frame 0
                events[-1]['clips'][-1]['loop'] = False
                events[-1]['clips'].append(clip)

            elif cmd_upper in [AnimationCommands.Clear, AnimationCommands.Clear2]:
                # Display nothing
                event['clear'] = True
                assert (clip_offset == 0)

            else:
                logger.error("ERROR: Unknown upper command: %d", cmd_upper)
                exit(1)

            event['frame_length'] = event.get('frame_length', 2)

            assert (event['frame_length'] >= 0)

            is_anim_wrapped = event['frame_start'] >= max_frames
            if event['frame_start'] < 0:
                event['frame_start'] = 0
                is_anim_wrapped = 0 >= max_frames

            if is_anim_wrapped:
                event['frame_start'] = max_frames - 1

            if event['direction'] == PlaybackDirection.Freeze:
                event['frame_length'] = 1

            if cmd_upper == AnimationCommands.AppendLoopAll:
                # Append to previous event, the two will loop continuous as one
                # Make sure the two events are the same before trying to merge 1
                if events[-1]['offset'] != event['offset']:
                    logger.error("ERROR: The append command data is not the same offset!")
                    exit(1)

                if events[-1]['direction'] == PlaybackDirection.Reverse:
                    event['frame_start'] = max_frames - 1

                events[-1]['clips'].append(clip)
                event = events[-1]

            else:
                event['clips'].append(clip)
                events.append(event)

            logger.debug("Playing %8s from frame %2d @ %8f... %02x speed[%s]" % (
                clip_filename, clip_offset, event['timestamp'] / 1000, cmd, str(event['frame_length'])))
            logger.debug(event)
            logger.debug("")

            if cmd_upper in [AnimationCommands.AppendLoopLast]:
                logger.error(
                    "ERROR: Found command that needs to be tested! Check if this actually loops just the last clip or not")
                exit(1)

        return events
