import logging
import os
import shutil
import tempfile

from PIL import Image

import numpy as np

logger = logging.getLogger("ddranimtool." + __name__)


class FrameManager:
    def __init__(self, cache_folder, raw_video_folders=[], jpsxdec_jar_path=None):
        self.video_cache = {}
        self.frame_cache = {}
        self.cache_folder = os.path.abspath(cache_folder)
        self.raw_video_folders = raw_video_folders
        self.jpsxdec_jar_path = os.path.abspath(jpsxdec_jar_path) if jpsxdec_jar_path is not None else None

        self.temp_dir = os.path.abspath(tempfile._get_default_tempdir())
        os.makedirs(self.temp_dir, exist_ok=True)

    def dump_raw_frame(self, chunk, output_filename):
        JPSXDEC_COMMAND = "java -jar \"%s\" -f \"{0}\" -static bs -dim {1}x{2} -fmt png -quality psx" % self.jpsxdec_jar_path

        # This is stupid but jPSXdec doesn't actually have a way to save to a specific directory from command line,
        # so change directories to the temporary folder until the end of the function and then restore the old directory
        cwd = os.getcwd()

        # Windows doesn't like
        temp_filename = os.path.join(self.temp_dir, next(tempfile._get_candidate_names())) + ".bin"
        with open(temp_filename, "wb") as raw_frame_file:
            raw_frame_file.write(chunk)

        os.chdir(os.path.dirname(temp_filename))

        converted_frame_path = os.path.splitext(temp_filename)[0] + ".png"

        cmd = JPSXDEC_COMMAND.format(os.path.basename(temp_filename), 304, 176)
        os.system(cmd)

        shutil.move(converted_frame_path, output_filename)

        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

        os.chdir(cwd)

    def get_cached_frames(self, filename):
        self.video_cache[filename] = []

        basename = os.path.basename(os.path.splitext(filename)[0])
        frame_idx = 0

        while True:
            output_filename = os.path.join(self.cache_folder, "%s_%04d.png" % (basename, frame_idx))

            if not os.path.exists(output_filename):
                break

            with Image.open(output_filename) as inframe:
                self.frame_cache[output_filename] = (inframe.tobytes(), inframe.size, inframe.mode)

                self.video_cache[filename].append(
                    np.asarray(Image.frombytes(
                        mode=self.frame_cache[output_filename][2],
                        size=self.frame_cache[output_filename][1],
                        data=self.frame_cache[output_filename][0]
                    ))
                )

            frame_idx += 1


    def get_raw_frames(self, filename, ext):
        req_frames = []

        os.makedirs(self.cache_folder, exist_ok=True)

        if not filename in self.video_cache:
            self.get_cached_frames(filename)

        if not self.video_cache.get(filename, []):
            # Only deal with jPSXdec if we need to dump a video
            assert (self.jpsxdec_jar_path is not None)

            self.video_cache[filename] = []

            input_filename = None
            for raw_video_folder in self.raw_video_folders:
                for xt in [ext.lower(), ext.upper()]:
                    input_filename = os.path.join(raw_video_folder, filename + "." + xt)

                    if os.path.exists(input_filename):
                        break

                if os.path.exists(input_filename):
                    break

            if input_filename is None or not os.path.exists(input_filename):
                logger.error("Could not find video file for %s.%s" % (filename, ext))
            assert (os.path.exists(input_filename) == True)

            logger.debug("Loading frames for %s" % input_filename)

            with open(input_filename, "rb") as infile:
                data = bytearray(infile.read())
                chunks = [data[i:i+0x2000] for i in range(0, len(data), 0x2000)]

                for frame_idx in range(len(chunks)):
                    output_filename = os.path.join(self.cache_folder, "%s_%04d.png" % (
                        os.path.basename(os.path.splitext(filename)[0]), frame_idx))

                    if output_filename not in self.frame_cache:
                        if not os.path.exists(output_filename):
                            self.dump_raw_frame(chunks[frame_idx], output_filename)

                        with Image.open(output_filename) as inframe:
                            self.frame_cache[output_filename] = (inframe.tobytes(), inframe.size, inframe.mode)

                    self.video_cache[filename].append(
                        np.asarray(Image.frombytes(
                            mode=self.frame_cache[output_filename][2],
                            size=self.frame_cache[output_filename][1],
                            data=self.frame_cache[output_filename][0]
                        ))
                    )

        req_frames += self.video_cache[filename]

        return req_frames
