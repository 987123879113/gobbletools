import argparse
import glob
import multiprocessing
import os

from formats.dmx import FrameManager

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input path containing raw video files (can specify multiple times)', required=True, action='append', nargs='+')
    parser.add_argument('-o', '--output', help='Output path to store cached video frames', default="frame_cache")
    parser.add_argument('-t', '--tools-path', help='Tools path', default="tools")

    args = parser.parse_args()

    jpsxdec_path = os.path.join(args.tools_path, "jpsxdec", "jpsxdec.jar")
    if not os.path.exists(jpsxdec_path):
        print("ERROR: Could not find jPSXdec! %s" % (jpsxdec_path))
    assert(os.path.exists(jpsxdec_path) == True)

    os.makedirs(args.output, exist_ok=True)

    pool = multiprocessing.Pool()

    for input_foldername in args.input:
        filenames = [os.path.splitext(os.path.basename(filename))[0] for filename in glob.glob(os.path.join(input_foldername[0], "*.BS"))]
        filenames += [os.path.splitext(os.path.basename(filename))[0] for filename in glob.glob(os.path.join(input_foldername[0], "*.bs"))]
        filenames = list(set(filenames))  # Remove duplicates

        for filename in filenames:
            frame_manager = FrameManager(args.output, input_foldername, jpsxdec_path)
            pool.apply_async(frame_manager.get_raw_frames, args=(filename, "bs",))

    pool.close()
    pool.join()
