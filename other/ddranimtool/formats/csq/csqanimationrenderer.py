import logging

from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.editor import concatenate_videoclips, AudioFileClip, CompositeVideoClip

import numpy as np

from .constants import *
from .timekeeper import TimeKeeper

logger = logging.getLogger("ddranimtool." + __name__)

TARGET_FRAME_RATE = 60


class CsqAnimationRenderer:
    def __init__(self, events, frame_manager, timekeeper=None):
        self.events = events
        self.frame_manager = frame_manager
        self.timekeeper = timekeeper if timekeeper else TimeKeeper()

    def get_clip(self, frames, fps):
        return concatenate_videoclips([ImageSequenceClip(frames, fps=fps)])

    def get_frames(self, event):
        clip_frames = []
        frames = []
        frame_start = int(event['frame_start'])

        for clip in event['clips']:
            frames = self.frame_manager.get_raw_frames(clip['filename'], "sbs")

            if event['direction'] == PlaybackDirection.Freeze:
                frames = [frames[frame_start]]

            elif event['direction'] == PlaybackDirection.Reverse:
                if frame_start > 0:
                    frames = frames[:frame_start+1]

            else:
                frames = frames[frame_start:]

            clip_frames.append(frames)
            frame_start = 0

        if event['direction'] == PlaybackDirection.Reverse:
            event['frame_start'] = len(frames) - 1

        else:
            event['frame_start'] = 0

        if event['frame_start'] < 0:
            event['frame_start'] = 0

        return clip_frames

    def get_output_frames(self):
        output_clips = []

        last_event_is_clear = self.events[-1].get('clear', False)
        if not last_event_is_clear:
            logger.error("ERROR: Last animation event is not a clear!")
        assert (last_event_is_clear == True)

        last_event_is_clear = self.events[-1].get('clear', False)
        for event in self.events:
            is_valid_clear = True
            if event.get('clear', False) and event['timestamp'] != self.events[-1]['timestamp']:
                is_valid_clear = False
                logger.error("ERROR: Found clear command that isn't at the end of the animation!")
            assert (is_valid_clear == True)

        for idx, event in enumerate(self.events[:-1]):
            if event.get('clear', False):
                logger.error("ERROR: Handle clear event mid-song!")
                exit(1)

            clip_frames = self.get_frames(event)
            output_frames = []

            clip_idx = 0
            frame_idx = int(event['frame_start'])
            cur_dir = event['direction']

            # DDR Extreme useful breakpoints for debugging
            # bpset 80068850,1,{ printf "timer[%08x]",a2; g }
            # bpset 80071624,1,{ printf "new_offset[%08x]",v0; g }
            # bpset 80069168,1,{ printf "non-stretch frame[%02x] offset[%08x]",s0,s2; g }
            # bpset 80068eac,1,{ printf "stretch frame[%02x] offset[%08x]",s0,s2; s }

            event['offset'] -= 0x100

            clip_idx = 0
            start_offset = event['offset']
            end_offset = self.events[idx+1]['offset']

            t1 = self.timekeeper.calculate_timestamp_from_offset(start_offset)
            t2 = self.timekeeper.calculate_timestamp_from_offset(end_offset)
            tcur = t1
            tstep = (1 / 60) * 1000
            cnt = 0
            next_clip_wrap = len(clip_frames[0])
            while tcur < t2:
                if event['method'] == PlaybackMethod.Freeze or cur_dir == PlaybackDirection.Freeze:
                    event['frame_length'] = 1
                    frame_idx = int(event['frame_start'])
                    clip_idx = 0

                elif event.get('stretch', False):
                    x = (self.timekeeper.calculate_offset_from_timestamp(tcur) - start_offset)
                    frame_idx = int((x * len(clip_frames[clip_idx])) / (event.get('frame_speed', 2) * 1024))

                    if frame_idx >= next_clip_wrap:
                        clip_idx = (clip_idx + 1) % len(clip_frames)
                        next_clip_wrap += len(clip_frames[clip_idx])

                        if event['method'] == PlaybackMethod.PingPong:
                            cur_dir = PlaybackDirection.Reverse if cur_dir == PlaybackDirection.Forward else PlaybackDirection.Forward

                    frame_idx %= len(clip_frames[clip_idx])

                    if cur_dir == PlaybackDirection.Reverse:
                        frame_idx = len(clip_frames[clip_idx]) - (frame_idx + 1)

                    if frame_idx < 0:
                        frame_idx = 0

                    if len(clip_frames[clip_idx]) <= frame_idx:
                        frame_idx = len(clip_frames[clip_idx]) - 1

                else:
                    if (cnt % event['frame_length']) == 0:
                        if cur_dir == PlaybackDirection.Reverse:
                            frame_idx = frame_idx - 1

                        elif cur_dir != PlaybackDirection.Freeze:
                            frame_idx = frame_idx + 1

                        if frame_idx < 0 or frame_idx >= len(clip_frames[clip_idx]):
                            if cur_dir == PlaybackDirection.Reverse:
                                clip_idx = clip_idx - 1
                                if clip_idx < 0:
                                    clip_idx = len(clip_frames) - 1

                            else:
                                clip_idx = (clip_idx + 1) % len(clip_frames)

                            if event['method'] == PlaybackMethod.PingPong:
                                cur_dir = PlaybackDirection.Reverse if cur_dir == PlaybackDirection.Forward else PlaybackDirection.Forward

                            if cur_dir == PlaybackDirection.Reverse:
                                frame_idx = len(clip_frames[cur_dir]) - 1

                            elif cur_dir != PlaybackDirection.Freeze:
                                frame_idx = 0

                            # Don't play the last frame that was already played
                            if event['method'] == PlaybackMethod.PingPong:
                                if cur_dir == PlaybackDirection.Reverse:
                                    frame_idx -= 1

                                elif cur_dir != PlaybackDirection.Freeze:
                                    frame_idx += 1

                output_frames.append(clip_frames[clip_idx][int(frame_idx)])

                cnt += 1
                tcur += tstep

            expected_duration = (self.timekeeper.calculate_timestamp_from_offset(self.events[idx+1]['offset'] - 0x100) - self.timekeeper.calculate_timestamp_from_offset(event['offset'])) / 1000
            expected_frame_count = round(expected_duration * 60)
            if len(output_frames) > expected_frame_count:
                output_frames = output_frames[:expected_frame_count]
            assert(len(output_frames) == expected_frame_count)

            clip = self.get_clip(output_frames, len(output_frames) / ((self.events[idx+1]['timestamp'] - event['timestamp'])/1000))
            assert(round(clip.duration * clip.fps) == expected_frame_count)

            output_clips.append({
                'timestamp_start': event['timestamp'],
                'timestamp_end': self.events[idx+1]['timestamp'],
                'clip': clip
            })

        return output_clips

    def export(self, output_filename, mp3_filename, background_image, raw_video_render_only=False):
        output_clips = self.get_output_frames()

        clear_events = [x['timestamp'] for x in self.events if x.get('clear', False)]
        if len(clear_events) > 1:
            logger.error("ERROR: Found multiple clear events!")
        assert (len(clear_events) <= 1)

        bgm_audio = AudioFileClip(mp3_filename) if mp3_filename else None

        # Combine all clips into one composite clip
        earliest_timestamp = min([c['timestamp_start'] for c in output_clips])
        clip = concatenate_videoclips([c['clip'] for c in output_clips])

        if clear_events:
            clear_event_timestamp = (clear_events[0] - earliest_timestamp) / 1000

            if clear_event_timestamp < clip.duration:
                clip = clip.subclip(0, clear_event_timestamp)

        if not raw_video_render_only:
            video_timestamp_end = output_clips[-1]['timestamp_end'] + 1000

            if bgm_audio is not None and bgm_audio.duration > video_timestamp_end / 1000:
                video_timestamp_end = bgm_audio.duration * 1000

            crossfade_time = 0.5

            # Write the background image from the very beginning to the very end of the video
            clip = CompositeVideoClip([
                self.get_clip([np.asarray(background_image)] * int((video_timestamp_end/1000)*60), 60),
                clip.set_start(earliest_timestamp / 1000).crossfadein(crossfade_time)
            ])

        # Just some quick checks to make sure there are no unexpected gaps in the video frames
        # If this ever asserts then there's probably an issue with the parser somewhere
        timestamps = sorted([(c['timestamp_start'] - earliest_timestamp, c['timestamp_end'] -
                            earliest_timestamp) for c in output_clips], key=lambda x: x[0])
        for i, timestamp in enumerate(timestamps[2:]):
            if timestamp[0] > timestamps[i+1][1]:
                logger.error("ERROR: Found gap in video clips! %f to %f" % (timestamps[i+1][1], timestamp[0]))
            assert (timestamp[0] <= timestamps[i+1][1])

        if not raw_video_render_only and bgm_audio is not None:
            clip = clip.set_audio(bgm_audio)

        clip.write_videofile(output_filename, audio_codec="aac", preset="ultrafast",
                             fps=TARGET_FRAME_RATE, bitrate="50000k")
