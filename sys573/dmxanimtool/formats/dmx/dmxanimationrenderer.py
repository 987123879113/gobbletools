import logging

from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.editor import concatenate_videoclips, AudioFileClip

import numpy as np

from .constants import *

logger = logging.getLogger("dmxanimtool." + __name__)


class DmxAnimationRenderer:
    def __init__(self, chart_reader, frame_manager):
        self.chart_reader = chart_reader
        self.events = chart_reader.get_anim_events()
        self.frame_manager = frame_manager

    def _get_output_frames(self, bgm_audio):
        output_frames = []
        frames = []

        movie_start_frame = 0
        movie_update_frame_step = 1
        movie_step_val = 1
        movie_step_beats = 0

        event_idx = 0
        cur_frame_idx = 0
        cur_movie_idx = 0

        last_frame_counter_update = 0
        absolute_beat_position = 0
        absolute_beat_position_counter = 0
        cur_movie_idx_base_frame = 0
        cur_command = AnimationCommands.Uninitialized
        last_absolute_beat_position = 0

        movie_started = False
        movie_start_finished = False

        all_event_offsets = [x['offset'] for x in self.events if x['offset'] != 0]
        last_event_offset = max(all_event_offsets)

        if bgm_audio is not None:
            mp3_last_event_offset = round(bgm_audio.duration * 300)

            if mp3_last_event_offset > last_event_offset:
                last_event_offset = mp3_last_event_offset

        for cur_offset in range(0, last_event_offset):
            # Handle displaying frames at the beginning of the loop as that's what I *think* the game does.
            # The PlayBeat/PlayBeat2 commands store the absolute beat position in a memory location when it processes the event.
            # Every time PlayBeat/PlayBeat2 updates its counter, it calculates the absolute beat position again and takes the
            # difference to calculate frame index.
            # There will always be a difference (I've always seen it as a 1 timestamp difference) between when the event is
            # processed and when it starts calculating the frame index, so I think that means that the frame index calculations
            # are happening on the frame after the event has been processed.
            # This is extreme hair splitting because it's the difference of a frame showing 1/300th of a second sooner or not and
            # should not matter.

            # The counters will update but the actual frames won't be output until the counter reaches movie_update_frame_step
            # so just duplicate the last frame until we are allowed to write a new frame.
            cur = (60 * (1 / 300)) * cur_offset
            frame_counter = cur - last_frame_counter_update

            # Default to the last frame or a blank frame
            output_frame = None
            if frame_counter >= max(movie_update_frame_step, 1):
                if cur_command == AnimationCommands.MovieStart:
                    # MovieStart cannot be reversed
                    cur_frame_idx += abs(movie_step_val)

                    # MovieStart will loop only the last movie clip even with multiple MovieAppend commands
                    if cur_frame_idx < 0 or cur_frame_idx >= len(frames[cur_movie_idx]):
                        cur_movie_idx = len(frames) - 1
                        cur_frame_idx = 0
                        movie_start_finished = True

                elif cur_command in [AnimationCommands.PlayBeat, AnimationCommands.PlayBeat2]:
                    # Commands that work based on beat positions
                    absolute_beat_position = self.chart_reader.calculate_absolute_beat_from_timestamp(cur_offset)
                    absolute_beat_position_diff = absolute_beat_position - last_absolute_beat_position
                    last_absolute_beat_position = absolute_beat_position

                    if movie_step_beats < 0:
                        absolute_beat_position_diff = -absolute_beat_position_diff

                    absolute_beat_position_counter += absolute_beat_position_diff

                    cur_counter = ((absolute_beat_position_counter * 16) * (len(frames[cur_movie_idx]) - 1)) // (abs(movie_step_beats) * 0x600)
                    cur_frame_idx = (cur_counter >> 4) + ((cur_counter >> 3) & 1)

                    if movie_step_beats < 0:
                        cur_frame_idx = (len(frames[cur_movie_idx]) - 1) - abs(cur_frame_idx)

                        while cur_frame_idx < 0:
                            cur_movie_idx -= 1
                            if cur_movie_idx < 0:
                                cur_movie_idx = len(frames) - 1

                            cur_frame_idx += len(frames[cur_movie_idx])

                    if cur_frame_idx - cur_movie_idx_base_frame > len(frames[cur_movie_idx]):
                        cur_movie_idx = (cur_movie_idx + 1) % len(frames)
                        cur_movie_idx_base_frame = cur_frame_idx

                elif cur_command != AnimationCommands.Uninitialized:
                    cur_frame_idx += movie_step_val

                    if cur_frame_idx < 0:
                        while cur_frame_idx < 0:
                            cur_movie_idx -= 1
                            if cur_movie_idx < 0:
                                cur_movie_idx = len(frames) - 1

                            cur_frame_idx += len(frames[cur_movie_idx])

                    elif cur_frame_idx >= len(frames[cur_movie_idx]):
                        # Movies loop on the last video in a set
                        # Easy to see on iwil's intro where it loops the title scroll multiple times
                        if cur_movie_idx + 1 < len(frames):
                            cur_movie_idx = (cur_movie_idx + 1) % len(frames)
                        cur_frame_idx = 0

                last_frame_counter_update = cur

                if cur_command != AnimationCommands.Uninitialized:
                    # If the movie start command is not called then the background video texture isn't properly initialized
                    # and the graphics will become very glitchy in-game. So this is a hard requirement for actually rendering
                    # video.
                    assert(movie_started == True)
                    cur_frame_idx %= len(frames[cur_movie_idx])
                    output_frame = frames[cur_movie_idx][cur_frame_idx]

            else:
                output_frame = output_frames[-1] if output_frames else None

            output_frames.append(output_frame)

            # Event processor
            # Events will be processed in order based on the event's given timestamp value
            # Events can be chained together by setting the timestamp value to a smaller value than the previous event's timestamp (timestamp 0 is used officially)
            # The only exception is MovieStart must finish before any other events (besides MovieAppend) can be processed
            # Note: There's a +0x4b offset (0.25 sec) to the timestamp when processing the events in-game
            can_accept_events = cur_command != AnimationCommands.MovieStart or (cur_command == AnimationCommands.MovieStart and movie_start_finished)
            if can_accept_events and event_idx < len(self.events) and (cur_offset >= self.events[event_idx]['offset']):
                cur_event = self.events[event_idx]
                event_idx += 1

                logger.debug(cur_event)

                if cur_event['command'] == AnimationCommands.PlayNormal:
                    # Loop clip at 1x speed
                    movie_start_frame = cur_event['start_frame']
                    movie_step_val = cur_event['step']
                    movie_update_frame_step = 3
                    cur_command = AnimationCommands.PlayNormal

                elif cur_event['command'] == AnimationCommands.MovieStart:
                    # This video clip is guaranteed to play in full at least once (no other commands can be processed until this finishes playing once)
                    # If an additional clip is appended using MovieAppend then the LAST appended movie is looped until another command can be processed
                    # If no additional clips are appended then the clip specified by MovieStart will loop until another command can be processed
                    movie_start_frame = 0
                    movie_update_frame_step = 3
                    movie_step_val = 1
                    cur_command = AnimationCommands.MovieStart
                    movie_start_finished = False
                    movie_started = True

                elif cur_event['command'] == AnimationCommands.PlayBeat:
                    # Loop clip, speed is based on the specified number of beats
                    # Can be reversed
                    movie_step_beats = cur_event['beats']
                    movie_start_frame = cur_event['start_frame']
                    movie_update_frame_step = 1
                    cur_command = AnimationCommands.PlayBeat

                    # This causes it to update the counter that uses movie_step_val every frame
                    # but that isn't used in this renderer when movie_step_beats is in use
                    movie_step_val = 0

                    # Game will throw an exception if the beat value is 0
                    assert (movie_step_beats != 0)

                elif cur_event['command'] == AnimationCommands.ReverseDirection:
                    # Invert direction of current clip

                    # PlayBeat2 *CANNOT* be reversed with this function (confirmed by modifying a script in-game)
                    # PlayBeat2 ends up inverting movie_step_val which does nothing because it's not used
                    if cur_command == AnimationCommands.PlayNormal or cur_command != AnimationCommands.PlayBeat:
                        movie_step_val = -movie_step_val

                    else:
                        movie_step_beats = -movie_step_beats

                elif cur_event['command'] == AnimationCommands.PlayBeat2:
                    # Loop clip, speed is based on the specified number of beats
                    # CANNOT be reversed (only difference from PlayBeat?)
                    movie_step_beats = cur_event['beats']
                    movie_start_frame = cur_event['start_frame']
                    movie_update_frame_step = 1
                    movie_step_val = 1
                    cur_command = AnimationCommands.PlayBeat2

                    # Game will throw an exception if the beat value is 0
                    assert (movie_step_beats != 0)

                elif cur_event['command'] == AnimationCommands.PlayFast:
                    # Loop clip at 1.5x speed
                    movie_start_frame = cur_event['start_frame']
                    movie_step_val = cur_event['step']
                    movie_update_frame_step = 2
                    cur_command = AnimationCommands.PlayFast

                else:
                    logger.error("Unknown command! %d" % cur_event['command'])
                    exit(-1)

                # All commands that load a movie (everything except 2 and 5) will try to look for up to 10 appendable movies
                if cur_event['command'] not in [AnimationCommands.MovieAppend, AnimationCommands.ReverseDirection]:
                    last_frame_counter_update = ((60 * (1 / 300)) * cur_offset)
                    frames = [self.frame_manager.get_raw_frames(cur_event['filename'], "bs")[movie_start_frame:]]
                    cur_movie_idx_base_frame = 0
                    cur_movie_idx = 0
                    cur_frame_idx = 0

                    c = event_idx
                    while event_idx - c < 10 and event_idx < len(self.events) and self.events[event_idx]['command'] == AnimationCommands.MovieAppend:
                        logger.debug(self.events[event_idx])
                        frames.append(self.frame_manager.get_raw_frames(self.events[event_idx]['filename'], "bs"))
                        event_idx += 1

                logger.debug("")

                if cur_event['command'] in [AnimationCommands.PlayNormal, AnimationCommands.PlayFast, AnimationCommands.PlayBeat, AnimationCommands.PlayBeat2]:
                    last_absolute_beat_position = self.chart_reader.calculate_absolute_beat_from_timestamp(cur_offset)

                    if event_idx < len(self.events) and self.events[event_idx]['beats'] < 0:
                        # Why would it want to know what direction the *next* video clip is supposed to go?
                        # Without this the swirling cloud clips in sanc won't render properly
                        # I suspect this is a bug in the game's animation player that became a feature
                        absolute_beat_position_counter = len(frames[cur_movie_idx]) * len(frames) * 0x600

                    else:
                        absolute_beat_position_counter = 0

        blank_image = np.zeros(output_frames[-1].shape)
        for i in range(len(output_frames)):
            if output_frames[i] is None:
                output_frames[i] = blank_image

        return output_frames

    def export(self, output_filename, mp3_filename, raw_video_render_only=False, fps=60):
        bgm_audio = AudioFileClip(mp3_filename) if mp3_filename else None
        frames = self._get_output_frames(bgm_audio)
        clip = concatenate_videoclips([ImageSequenceClip(frames, fps=300)])

        if not raw_video_render_only and bgm_audio is not None:
            clip = clip.set_audio(bgm_audio)

        logger.info("Saving %s as %d fps" % (output_filename, fps))
        clip.write_videofile(output_filename, audio_codec="aac", preset="ultrafast",
                             fps=fps, bitrate="50000k")
