import argparse
import glob
import multiprocessing
import os

from formats.csq import FrameManager

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input path containing raw video files', required=True)
    parser.add_argument('-o', '--output', help='Output path to store cached video frames', default="frame_cache")
    parser.add_argument('-t', '--tools-path', help='Tools path', default="tools")

    args = parser.parse_args()

    jpsxdec_path = os.path.join(args.tools_path, "jpsxdec", "jpsxdec.jar")
    if not os.path.exists(jpsxdec_path):
        print("ERROR: Could not find jPSXdec! %s" % (jpsxdec_path))
    assert(os.path.exists(jpsxdec_path) == True)

    filenames = [os.path.basename(filename) for filename in glob.glob(os.path.join(args.input, "*"))]

    os.makedirs(args.output, exist_ok=True)

    pool = multiprocessing.Pool()

    for filename in filenames:
        frame_manager = FrameManager(args.output, args.input, jpsxdec_path)
        pool.apply_async(frame_manager.get_raw_frames, args=(filename,))

    pool.close()
    pool.join()
