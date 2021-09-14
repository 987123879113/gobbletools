import argparse
import os

import animation
import sprites

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-fcn', help='Input FCN image archive', required=True)
    parser.add_argument('--input-dat', help='Input DAT animation file', required=True)
    parser.add_argument('--output', help='Output filename')
    parser.add_argument('--upscale-ratio', help='Upscale ratio', type=int, default=1)
    parser.add_argument('--upscale-method', help='Upscale method: cpu|gpu|cudnn', default="cpu")
    parser.add_argument('--start-frame', help='Frame to start rendering', type=int, default=-1)
    parser.add_argument('--end-frame', help='Frame to end rendering', type=int, default=-1)
    #parser.add_argument('--threads', help='Number of threads to use for rendering', type=int, default=8)
    args = parser.parse_args()

    if args.upscale_method not in ['cpu', 'gpu', 'cudnn']:
        print("Invalid upscale method:", args.upscale_method)
        exit(-1)

    if not args.output:
        args.output = os.path.splitext(os.path.basename(args.input_fcn))[0] + ".mp4"

    fcn_files = sprites.get_images_from_fcn(args.input_fcn, args.upscale_ratio, args.upscale_method)

    obj_filename = [x for x in fcn_files if x.endswith('.obj')][0]
    sprite_filenames = sprites.parse_obj(fcn_files[obj_filename], fcn_files)

    animation.parse_dat(args.input_dat, args.output, sprite_filenames, fcn_files, args.upscale_ratio, args.start_frame, args.end_frame, 1)
