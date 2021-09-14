import io
import json
import os
import re
import struct
import tempfile

from PIL import Image

import tim2png

def parse_obj(data, fcn_files):
    filenames = []

    filesize = len(data)
    entry_count = filesize // 0x30

    for i in range(entry_count):
        filename = data[i*0x30:i*0x30+0x1c].decode('shift-jis').strip().strip('\0')
        filenames.append(filename)

    return filenames


def parse_sprite_sheet(filename, fcn_files):
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


def get_images_from_fcn(filename, upscale_ratio=1, upscale_method="cudnn"):
    output_files = {}

    # Prase filetable in FCN file
    with open(filename, "rb") as infile:
        filesize, _, filetable_size, _ = struct.unpack("<IIII", infile.read(16))

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

    if upscale_ratio != 1:
        output_images = upscale_sprites(output_images, upscale_ratio, upscale_method)

    return output_images


def upscale_sprites(fcn_files, upscale_ratio, upscale_method):
    if upscale_ratio == 1:
        return fcn_files

    if not os.path.exists("video2x.json"):
        print("Couldn't find video2x.json, skipping upscaling...")
        return fcn_files

    video2x_config = json.load(open("video2x.json", "r"))

    if 'waifu2x_path' not in video2x_config:
        print("Couldn't find waifu2x_path in video2x.json, skipping upscaling...")
        return fcn_files

    with tempfile.TemporaryDirectory() as sprite_folder:
        with tempfile.TemporaryDirectory() as upscaled_sprite_folder:
            for k in fcn_files:
                if k.endswith(".obj") or k.endswith(".arr"):
                    continue

                for k2 in fcn_files[k]:
                    fcn_files[k][k2].save(os.path.join(sprite_folder, "%s_%d.png" % (k, k2)))

            print("Upscaling using waifu2x (this will take a while)")

            json.load

            # Call waifu2x
            import waifu2x_caffe
            waifu2x = waifu2x_caffe.Waifu2xCaffe(video2x_config['waifu2x_path'], upscale_method, "anime_style_art_rgb")
            waifu2x.upscale(sprite_folder, upscaled_sprite_folder, upscale_ratio)

            for k in fcn_files:
                if k.endswith(".obj") or k.endswith(".arr"):
                    continue

                for k2 in fcn_files[k]:
                    image = Image.open(os.path.join(upscaled_sprite_folder, "%s_%d.png" % (k, k2)))
                    fcn_files[k][k2] = image.copy()
                    image.close()

    return fcn_files


# Unused, but may be reused if I want to implement a method to
# export sprites and a metadata file and then use that folder
# instead of the FCN file (used if you want to clean upscaled images)
def export_fcn_files(fcn_files, output_json_filename):
    output_fcn_files = {}

    for k in fcn_files:
        if k.endswith(".obj") or k.endswith(".arr"):
            output_filename = os.path.join("sprites", k)
            open(output_filename, "wb").write(fcn_files[k])
            output_fcn_files[k] = output_filename
            continue

        output_fcn_files[k] = {}

        for k2 in fcn_files[k]:
            output_filename = os.path.join("sprites", "%s_%d.png" % (k, k2))
            fcn_files[k][k2].save(output_filename)
            output_fcn_files[k][k2] = output_filename

    import json
    json.dump(output_fcn_files, open(output_json_filename, "w"))
