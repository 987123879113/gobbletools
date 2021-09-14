import argparse
import io
import glob
import json
import os
import re
import struct
import tempfile

from PIL import Image


def parse_sprite_sheet(filename, fcn_files):
    import tim2png
    _, cluts = tim2png.readTimImage(io.BytesIO(fcn_files[filename]), 0)

    if '@' in filename:
        match = re.search(r'([^\@]*)@(\d+)_(\d+)(\..*)?', filename)

        base_filename = match.group(1)
        split_width = int(match.group(2))
        split_height = int(match.group(3))

    else:
        match = re.search(r'([^\.]*)(\..*)?$', filename)

        base_filename = match.group(1)
        split_width = 1
        split_height = 1

    # Find all related files
    related_files = []
    for fcn_filename in fcn_files:
        if fcn_filename.startswith(base_filename + '@') or fcn_filename.startswith(base_filename + '.'):
            related_files.append(fcn_filename)

    output = {}
    for clut in range(0, cluts + 1):
        # Load all files into memory to be stitched together into one large image
        related_images = []
        max_width = 0
        max_height = 0
        for related_file in related_files:
            image, _ = tim2png.readTimImage(io.BytesIO(fcn_files[related_file]), clut)
            related_images.append(image)

            if image.width > max_width:
                max_width = image.width

            max_height += image.height

        image = Image.new('RGBA', (max_width, max_height), (0, 0, 0, 0))

        # Stitch together all sprite images
        cur_y = 0
        for related_image in related_images:
            image.paste(related_image, (0, cur_y), related_image)
            cur_y += related_image.height

        # Split up sprite sheet into correct sprites
        cur_idx = 0
        for x in range(split_width):
            for y in range(split_height):
                sprite = image.crop((image.width // split_width * x, image.height // split_height * y, image.width // split_width * (x + 1), image.height // split_height * (y + 1)))

                if '@' in filename:
                    output_filename = "%s_%03d" % (base_filename, cur_idx)

                else:
                    output_filename = base_filename

                cur_idx += 1

                if output_filename not in output:
                    output[output_filename] = {}

                output[output_filename][clut] = sprite

    return output


def get_files_from_fcn(filename):
    output_files = {}

    # Parse filetable in FCN file
    with open(filename, "rb") as infile:
        filesize, _, filetable_size, data_size = struct.unpack("<IIII", infile.read(16))

        is_new_format = False
        if filesize & 0x08000000 != 0:
            is_new_format = True

        if is_new_format:
            file_count = filesize & 0xffff

        else:
            file_count = filetable_size // 0x28

        for i in range(file_count):
            infile.seek(0x10 + (i * 0x28))

            filename = infile.read(0x20).decode('shift-jis').strip()

            offset, datalen = struct.unpack("<II", infile.read(8))

            if is_new_format:
                infile.seek(0x10 + (file_count * 0x28) + offset)

            else:
                infile.seek(0x10 + filetable_size + offset)

            data = infile.read(datalen)

            if filename.endswith('tim'):
                filename = filename[:-4]
                output_files[filename] = data

            else:
                output_files[filename] = data

    return output_files


def get_images_from_fcn(filename):
    import tim2png
    output_files = get_files_from_fcn(filename)

    # Actually read in the images
    output_images = {}
    for filename in output_files:
        print("Extracting", filename)

        if filename.endswith('.arr') or filename.endswith('.obj'):
            output_images[filename] = output_files[filename]

        else:
            if '@' in filename or '.' in filename:
                output_images.update(parse_sprite_sheet(filename, output_files))

            else:
                image, cluts = tim2png.readTimImage(io.BytesIO(output_files[filename]), 0)

                output_images[filename] = { 0: image }

                for clut in range(1, cluts):
                    image, _ = tim2png.readTimImage(io.BytesIO(output_files[filename]), clut)
                    output_images[filename][clut] = image

    return output_images


def export_fcn_files(fcn_files, output_folder, output_json_filename=None):
    output_fcn_files = {}

    for k in fcn_files:
        if k.endswith(".obj") or k.endswith(".arr"):
            output_filename = os.path.join(output_folder, k)
            open(output_filename, "wb").write(fcn_files[k])
            output_fcn_files[k] = output_filename
            continue

        output_fcn_files[k] = {}

        for k2 in fcn_files[k]:
            output_filename = os.path.join(output_folder, "%s_%d.png" % (k, k2))
            fcn_files[k][k2].save(output_filename)
            output_fcn_files[k][k2] = output_filename

    if output_json_filename:
        json.dump(output_fcn_files, open(output_json_filename, "w"))


def main(args_input, args_output, args_convert):
    if os.path.isfile(args_input):
        if not args_output:
            args_output = os.path.splitext(os.path.basename())[0]

        if not os.path.exists(args_output):
            os.makedirs(args_output)

        if args_convert:
            export_fcn_files(get_images_from_fcn(args_input), args_output)

        else:
            output_files = get_files_from_fcn(args_input)

            for filename in output_files:
                with open(os.path.join(args_output, filename), "wb") as outfile:
                    outfile.write(output_files[filename])

    else:
        filenames = sorted(glob.glob(os.path.join(args_input, "**", "*"), recursive=True))

        filetable_data = bytearray()
        main_data = bytearray()

        cur_offset = 0
        for filename in filenames:
            base_filename = os.path.basename(filename)

            if not os.path.splitext(base_filename)[1]:
                base_filename += ".tim"

            base_filename += " " * (32 - len(base_filename))
            filesize = os.path.getsize(filename)

            filetable_data += base_filename.encode('ascii')
            filetable_data += int.to_bytes(cur_offset, length=4, byteorder="little")
            filetable_data += int.to_bytes(filesize, length=4, byteorder="little")

            main_data += open(filename, "rb").read()

            cur_offset += filesize

        with open(args_output, "wb") as outfile:
            # outfile.write(int.to_bytes(len(filetable_data) + len(main_data) + 0x10, length=4, byteorder="little"))
            # outfile.write(int.to_bytes(0x10, length=1, byteorder="little"))
            # outfile.write(int.to_bytes(len(filenames), length=1, byteorder="little"))
            # outfile.write(int.to_bytes(0x00, length=1, byteorder="little"))
            # outfile.write(int.to_bytes(0x00, length=1, byteorder="little"))
            # outfile.write(int.to_bytes(len(filetable_data), length=4, byteorder="little"))
            # outfile.write(int.to_bytes(len(main_data), length=4, byteorder="little"))
            # outfile.write(filetable_data)
            # outfile.write(main_data)

            outfile.write(int.to_bytes(len(filenames), length=3, byteorder="little"))
            outfile.write(int.to_bytes(0x08, length=1, byteorder="little"))
            outfile.write(int.to_bytes(len(filetable_data), length=3, byteorder="little"))
            outfile.write(int.to_bytes(0x10, length=1, byteorder="little"))
            outfile.write(int.to_bytes(len(main_data), length=4, byteorder="little"))
            outfile.write(int.to_bytes(len(filetable_data) + len(main_data) + 0x10, length=4, byteorder="little"))
            outfile.write(filetable_data)
            outfile.write(main_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input FCN/folder', required=True)
    parser.add_argument('-o', '--output', help='Output FCN/folder (optional)', default="")
    parser.add_argument('-c', '--convert', help='Convert images', default=False, action='store_true')

    args = parser.parse_args()

    main(args.input, args.output, args.convert)
