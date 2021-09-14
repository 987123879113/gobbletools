import ctypes
import struct

import hexdump
import imageio
import numpy
import tqdm

from PIL import Image, ImageChops

DEBUG_MODE = False

def read_filelist_from_dat(infile, entry_count):
    infile.seek(0x0c, 0)

    # Skip over actual data so we can get to the file list
    for _ in range(0, entry_count):
        infile.read(0x40)

        frame_count = struct.unpack("<I", infile.read(4))[0]
        for i in range(frame_count):
            infile.read(0x20)

    filename_count = struct.unpack("<I", infile.read(4))[0]

    filenames = []
    for _ in range(0, filename_count):
        filename = infile.read(0x20).decode('shift-jis').strip().strip('\0')
        filenames.append(filename)

    return filenames


def subcommand_0_animate_move(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp):
    # Position command
    start_x, end_x, start_y, end_y = struct.unpack("<HHHH", cur_block[16:24])
    start_x = ctypes.c_short(start_x).value
    end_x = ctypes.c_short(end_x).value
    start_y = ctypes.c_short(start_y).value
    end_y = ctypes.c_short(end_y).value

    for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
        cur_x = start_x + (idx - start_timestamp) * ((end_x - start_x) / ((end_timestamp - 1) - start_timestamp))
        cur_y = start_y + (idx - start_timestamp) * ((end_y - start_y) / ((end_timestamp - 1) - start_timestamp))

        render_by_timestamp[idx][entry_idx]['x'] = cur_x + render_by_timestamp[idx][entry_idx].get('x', 0)
        render_by_timestamp[idx][entry_idx]['y'] = cur_y + render_by_timestamp[idx][entry_idx].get('y', 0)

    if DEBUG_MODE:
        print("Move: (%d,%d) -> (%d,%d)" % (start_x, start_y, end_x, end_y))


def subcommand_0_animate_center(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp):
    # Image center
    start_x, end_x, start_y, end_y = struct.unpack("<HHHH", cur_block[16:24])
    start_x = ctypes.c_short(start_x).value
    end_x = ctypes.c_short(end_x).value
    start_y = ctypes.c_short(start_y).value
    end_y = ctypes.c_short(end_y).value

    for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
        cur_x = start_x + (idx - start_timestamp) * ((end_x - start_x) / ((end_timestamp - 1) - start_timestamp))
        cur_y = start_y + (idx - start_timestamp) * ((end_y - start_y) / ((end_timestamp - 1) - start_timestamp))

        render_by_timestamp[idx][entry_idx]['center_x'] = int(cur_x)
        render_by_timestamp[idx][entry_idx]['center_y'] = int(cur_y)

    if DEBUG_MODE:
        print("Image center: (%d,%d) -> (%d,%d)" % (start_x, start_y, end_x, end_y))


def subcommand_0_animate_zoom(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp):
    start_x_zoom, end_x_zoom, start_y_zoom, end_y_zoom = struct.unpack("<HHHH", cur_block[16:24])

    start_x_zoom = ctypes.c_short(start_x_zoom).value
    start_y_zoom = ctypes.c_short(start_y_zoom).value
    end_x_zoom = ctypes.c_short(end_x_zoom).value
    end_y_zoom = ctypes.c_short(end_y_zoom).value

    start_x_zoom /= 4096
    start_y_zoom /= 4096
    end_x_zoom /= 4096
    end_y_zoom /= 4096

    for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
        cur_x_zoom = start_x_zoom + (idx - start_timestamp) * ((end_x_zoom - start_x_zoom) / ((end_timestamp - 1) - start_timestamp))
        cur_y_zoom = start_y_zoom + (idx - start_timestamp) * ((end_y_zoom - start_y_zoom) / ((end_timestamp - 1) - start_timestamp))

        render_by_timestamp[idx][entry_idx]['x_zoom'] = cur_x_zoom
        render_by_timestamp[idx][entry_idx]['y_zoom'] = cur_y_zoom

    if DEBUG_MODE:
        print("Zoom: (%f,%f) -> (%f,%f)" % (start_x_zoom, start_y_zoom, end_x_zoom, end_y_zoom))


def subcommand_0_animate_rotation(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp):
    # Rotation command
    start_rotate, end_rotate = struct.unpack("<HH", cur_block[16:20])
    start_rotate = ctypes.c_short(start_rotate).value
    end_rotate = ctypes.c_short(end_rotate).value

    start_rotate /= 12
    end_rotate /= 12

    for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
        cur_rotate = start_rotate + (idx - start_timestamp) * ((end_rotate - start_rotate) / ((end_timestamp - 1) - start_timestamp))
        render_by_timestamp[idx][entry_idx]['rotate'] = cur_rotate

    if DEBUG_MODE:
        print("Rotation: %d -> %d" % (start_rotate, end_rotate))


def subcommand_0_animate_transparency(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp):
    # Transparency command
    start_transparency, end_transparency = struct.unpack("<HH", cur_block[16:20])

    for idx in range(start_timestamp, end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp):
        cur_transparency = start_transparency + (idx - start_timestamp) * ((end_transparency - start_transparency) / ((end_timestamp - 1) - start_timestamp))
        render_by_timestamp[idx][entry_idx]['opacity'] = cur_transparency / 128

    if DEBUG_MODE:
        print("Transparency: %d -> %d" % (start_transparency, end_transparency))


def subcommand_0_animate_image(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp, sprite_filenames, anim_idx):
    # Animate image transitions
    start_image_idx, end_image_idx = struct.unpack("<HH", cur_block[16:20])
    anim_diff = abs(end_image_idx - start_image_idx)

    if anim_diff == 0:
        anim_diff = 1

    step = -1 if start_image_idx > end_image_idx else 1
    end_timestamp2 = end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp
    time_step = (end_timestamp2 - start_timestamp) / anim_diff

    cur_timestamp = start_timestamp
    cur_anim_idx = start_image_idx
    while cur_timestamp < end_timestamp:
        for j in range(0, int(cur_timestamp + time_step) - int(cur_timestamp)):
            if int(cur_timestamp) + j >= end_timestamp:
                break

            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['filename'] = sprite_filenames[anim_idx + cur_anim_idx]
            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['anim_idx'] = cur_anim_idx

        cur_timestamp += time_step
        cur_anim_idx += step

    if DEBUG_MODE:
        print("Image transition: %d -> %d" % (start_image_idx, end_image_idx))


def subcommand_0_animate_palette(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp):
    # Palette transition
    start_palette, end_palette = struct.unpack("<HH", cur_block[16:20])
    palette_diff = abs(end_palette - start_palette)

    if palette_diff == 0:
        palette_diff = 1

    step = -1 if start_palette > end_palette else 1
    end_timestamp2 = end_timestamp if end_timestamp <= frame_end_timestamp else frame_end_timestamp
    time_step = (end_timestamp2 - start_timestamp) / palette_diff

    cur_timestamp = start_timestamp
    cur_palette = start_palette
    while cur_timestamp < end_timestamp:
        for j in range(0, int(cur_timestamp + time_step) - int(cur_timestamp)):
            if int(cur_timestamp) + j >= end_timestamp:
                break

            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['clut'] = cur_palette

        cur_timestamp += time_step
        cur_palette += step

    # render_by_timestamp[end_timestamp2][entry_idx]['clut'] = end_palette

    if DEBUG_MODE:
        print("Clut transition: %d -> %d" % (start_palette, end_palette))


def animate_sprite_raw(cur_block, render_by_timestamp, sprite_filenames, anim_idx, anim_frame_idx, start_timestamp, end_timestamp, entry_idx):
    # Sprite command, no frame speed calculation
    anim_image_count, time_per_image, flip_mode = struct.unpack("<HHI", cur_block[16:24])

    # Image-based animation
    if DEBUG_MODE:
        print("Sprite (image type 0): %d images, %d frames per image, flip mode %d" % (anim_image_count, time_per_image, flip_mode))

    for idx in range(anim_idx, anim_idx + anim_image_count):
        print(sprite_filenames[idx])

    flip_val = 0
    for idx in range(start_timestamp, end_timestamp, time_per_image):
        for j in range(0, time_per_image):
            if idx + j >= end_timestamp:
                break

            afi = anim_frame_idx + render_by_timestamp[idx + j][entry_idx].get('anim_idx', 0)

            render_by_timestamp[idx + j][entry_idx]['filename'] = sprite_filenames[anim_idx + afi]

        if flip_mode == 0:
            anim_frame_idx = (anim_frame_idx + 1)

            if anim_frame_idx >= anim_image_count:
                anim_frame_idx = anim_image_count - 1

        elif flip_mode == 1:
            anim_frame_idx = (anim_frame_idx + 1) % anim_image_count

        elif flip_mode == 2:
            if anim_frame_idx - 1 < 0:
                flip_val = 1

            elif anim_frame_idx + 1 >= anim_image_count:
                flip_val = -1

            anim_frame_idx += flip_val

        else:
            print("Unknown flip mode", flip_mode)
            exit(1)


def animate_palette_raw(cur_block, render_by_timestamp, sprite_filenames, anim_idx, anim_frame_idx, start_timestamp, end_timestamp, entry_idx):
    # Sprite command, palette flip, no frame speed calculation
    palette_colors, time_per_image, flip_mode = struct.unpack("<HHI", cur_block[16:24])

    # Image-based animation
    if DEBUG_MODE:
        print("Sprite (palette type 1): %d frames per palette, %d palettes, flip mode %d" % (time_per_image, palette_colors, flip_mode))
        print(sprite_filenames[anim_idx])

    flip_val = 0
    cur_timestamp = start_timestamp
    while cur_timestamp < end_timestamp:
        for j in range(0, int(cur_timestamp + time_per_image) - int(cur_timestamp)):
            if int(cur_timestamp) + j >= end_timestamp:
                break

            if 'filename' not in render_by_timestamp[int(cur_timestamp) + j][entry_idx]:
                render_by_timestamp[int(cur_timestamp) + j][entry_idx]['filename'] = sprite_filenames[anim_idx]

            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['clut'] = anim_frame_idx

        cur_timestamp += time_per_image

        if flip_mode == 1:
            anim_frame_idx = (anim_frame_idx + 1) % palette_colors

        else:
            print("Unknown flip mode", flip_mode)
            exit(1)


def animate_sprite_scroll(cur_block, render_by_timestamp, sprite_filenames, anim_idx, anim_frame_idx, start_timestamp, end_timestamp, entry_idx):
    # Scroll sprite command
    time_per_image, offset_x, offset_y = struct.unpack("<HHH", cur_block[0x10:0x16])
    offset_x = ctypes.c_short(offset_x).value / 16
    offset_y = ctypes.c_short(offset_y).value / 16

    if DEBUG_MODE:
        print("Sprite (tiled image type 2): %d frames per image, (%d, %d) offset" % (time_per_image, offset_x, offset_y))

    cur_offset_x = 0
    cur_offset_y = 0

    for idx in range(start_timestamp, end_timestamp, 1):
        for j in range(0, 1):
            if idx + j >= end_timestamp:
                break

            if 'filename' not in render_by_timestamp[idx + j][entry_idx]:
                render_by_timestamp[idx + j][entry_idx]['filename'] = sprite_filenames[anim_idx + anim_frame_idx]

            render_by_timestamp[idx + j][entry_idx]['offset_x'] = int(cur_offset_x) + render_by_timestamp[idx + j][entry_idx].get('offset_x', 0)
            render_by_timestamp[idx + j][entry_idx]['offset_y'] = int(cur_offset_y) + render_by_timestamp[idx + j][entry_idx].get('offset_y', 0)
            render_by_timestamp[idx + j][entry_idx]['tile'] = time_per_image

            cur_offset_x += offset_x
            cur_offset_y += offset_y


def animate_sprite(cur_block, render_by_timestamp, sprite_filenames, anim_idx, anim_frame_idx, start_timestamp, end_timestamp, entry_idx):
    # Sprite command, image based, frame calculation
    anim_image_count, time_per_image, flip_mode = struct.unpack("<HHI", cur_block[16:24])

    # Image-based animation
    if DEBUG_MODE:
        print("Sprite (image type 4): %d images, %d frames per image, flip mode %d" % (anim_image_count, time_per_image, flip_mode))

        for idx in range(anim_idx, anim_idx + anim_image_count):
            print(sprite_filenames[idx])

    if time_per_image == 1:
        time_per_image = 45

    else:
        time_per_image = 60 / time_per_image

    flip_val = 0
    cur_timestamp = start_timestamp
    while cur_timestamp < end_timestamp:
        for j in range(0, int(cur_timestamp + time_per_image) - int(cur_timestamp)):
            if int(cur_timestamp) + j >= end_timestamp:
                break

            afi = anim_frame_idx + render_by_timestamp[int(cur_timestamp) + j][entry_idx].get('anim_idx', 0)

            if flip_mode in [4, 5, 6]:
                afi = anim_image_count - afi - 1

            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['filename'] = sprite_filenames[anim_idx + afi]

        cur_timestamp += time_per_image

        if time_per_image == 0:
            cur_timestamp += 1
            continue

        if flip_mode in [0, 1, 4]:
            anim_frame_idx = (anim_frame_idx + 1)

            if anim_frame_idx >= anim_image_count:
                anim_frame_idx = anim_image_count - 1

        elif flip_mode in [2, 5]:
            anim_frame_idx = (anim_frame_idx + 1) % anim_image_count

        elif flip_mode in [3, 6]:
            if anim_frame_idx - 1 < 0:
                flip_val = 1

            elif anim_frame_idx + 1 >= anim_image_count:
                flip_val = -1

            anim_frame_idx += flip_val

        else:
            print("Unknown flip mode", flip_mode)
            exit(1)


def animate_palette(cur_block, render_by_timestamp, sprite_filenames, anim_idx, anim_frame_idx, start_timestamp, end_timestamp, entry_idx):
    # Sprite command, palette flip, frame speed calculation
    palette_colors, time_per_image, flip_mode = struct.unpack("<HHI", cur_block[16:24])

    # Image-based animation
    if DEBUG_MODE:
        print("Sprite (palette type 5): %d frames per palette, %d palettes, flip mode %d" % (time_per_image, palette_colors, flip_mode))
        print(sprite_filenames[anim_idx])

    if time_per_image == 1:
        time_per_image = 45

    else:
        time_per_image = 60 / time_per_image

    flip_val = 0
    cur_timestamp = start_timestamp
    while cur_timestamp < end_timestamp:
        for j in range(0, int(cur_timestamp + time_per_image) - int(cur_timestamp)):
            if int(cur_timestamp) + j >= end_timestamp:
                break

            afi = anim_frame_idx + render_by_timestamp[int(cur_timestamp) + j][entry_idx].get('clut', 0)

            if flip_mode in [4, 5, 6]:
                afi = palette_colors - afi - 1

            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['filename'] = sprite_filenames[anim_idx]
            render_by_timestamp[int(cur_timestamp) + j][entry_idx]['clut'] = afi

        cur_timestamp += time_per_image

        if time_per_image == 0:
            cur_timestamp += 1
            continue

        if flip_mode in [0, 1, 4]:
            anim_frame_idx = (anim_frame_idx + 1)

            if anim_frame_idx >= palette_colors:
                anim_frame_idx = palette_colors - 1

        elif flip_mode in [2, 5]:
            anim_frame_idx = (anim_frame_idx + 1) % palette_colors

        elif flip_mode in [3, 6]:
            if anim_frame_idx - 1 < 0:
                flip_val = 1

            elif anim_frame_idx + 1 >= palette_colors:
                flip_val = -1

            anim_frame_idx += flip_val

        else:
            print("Unknown flip mode", flip_mode)
            exit(1)


def fill_last_values(render_by_timestamp, entry_idx, frame_start_timestamp, frame_end_timestamp, last_filename, last_alpha, last_x, last_y, last_clut, last_zoom_x, last_zoom_y, last_rotate, last_center_x, last_center_y, blend_mode, entry_id):
    last_alpha /= 0x80

    for idx in range(0, frame_start_timestamp):
        if idx not in render_by_timestamp or entry_idx not in render_by_timestamp[idx]:
            continue

        # Find last used values
        if 'filename' in render_by_timestamp[idx][entry_idx]:
            last_filename = render_by_timestamp[idx][entry_idx]['filename']

        if 'opacity' in render_by_timestamp[idx][entry_idx]:
            last_alpha = render_by_timestamp[idx][entry_idx]['opacity']

        if 'x' in render_by_timestamp[idx][entry_idx]:
            last_x = render_by_timestamp[idx][entry_idx]['x']

        if 'y' in render_by_timestamp[idx][entry_idx]:
            last_y = render_by_timestamp[idx][entry_idx]['y']

        if 'clut' in render_by_timestamp[idx][entry_idx]:
            last_clut = render_by_timestamp[idx][entry_idx]['clut']

        if 'x_zoom' in render_by_timestamp[idx][entry_idx]:
            last_zoom_x = render_by_timestamp[idx][entry_idx]['x_zoom']

        if 'y_zoom' in render_by_timestamp[idx][entry_idx]:
            last_zoom_y = render_by_timestamp[idx][entry_idx]['y_zoom']

        if 'rotate' in render_by_timestamp[idx][entry_idx]:
            last_rotate = render_by_timestamp[idx][entry_idx]['rotate']

        if 'center_x' in render_by_timestamp[idx][entry_idx]:
            last_center_x = render_by_timestamp[idx][entry_idx]['center_x']

        if 'center_y' in render_by_timestamp[idx][entry_idx]:
            last_center_y = render_by_timestamp[idx][entry_idx]['center_y']

    for idx in range(frame_start_timestamp, frame_end_timestamp):
        if idx not in render_by_timestamp:
            render_by_timestamp[idx] = {}

        if entry_idx not in render_by_timestamp[idx]:
            render_by_timestamp[idx][entry_idx] = {}

        if 'filename' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['filename'] = last_filename
        else:
            last_filename = render_by_timestamp[idx][entry_idx]['filename']

        if 'blend_mode' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['blend_mode'] = blend_mode

        if 'opacity' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['opacity'] = last_alpha
        else:
            last_alpha = render_by_timestamp[idx][entry_idx]['opacity']

        if 'x' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['x'] = last_x
        else:
            last_x = render_by_timestamp[idx][entry_idx]['x']

        if 'y' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['y'] = last_y
        else:
            last_y = render_by_timestamp[idx][entry_idx]['y']

        if 'clut' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['clut'] = last_clut
        else:
            last_clut = render_by_timestamp[idx][entry_idx]['clut']

        if 'x_zoom' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['x_zoom'] = last_zoom_x
        else:
            last_zoom_x = render_by_timestamp[idx][entry_idx]['x_zoom']

        if 'y_zoom' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['y_zoom'] = last_zoom_y
        else:
            last_zoom_y = render_by_timestamp[idx][entry_idx]['y_zoom']

        if 'rotate' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['rotate'] = last_rotate
        else:
            last_rotate = render_by_timestamp[idx][entry_idx]['rotate']

        if 'center_x' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['center_x'] = last_center_x
        else:
            last_center_x = render_by_timestamp[idx][entry_idx]['center_x']

        if 'center_y' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['center_y'] = last_center_y
        else:
            last_center_y = render_by_timestamp[idx][entry_idx]['center_y']

        if 'entry_id' not in render_by_timestamp[idx][entry_idx]:
            render_by_timestamp[idx][entry_idx]['entry_id'] = entry_id


def read_animation_from_dat(infile, entry_count, animation_filenames, sprite_filenames, upscale_ratio):
    base_images = []

    render_by_timestamp = {}
    frame_width = 0
    frame_height = 0

    infile.seek(0x0c)
    for _ in range(0, entry_count):
        cur_offset = infile.tell()

        first_block = infile.read(0x40)

        frame_start_timestamp, frame_end_timestamp, entry_id, entry_type, anim_id, initial_x, initial_y = struct.unpack("<IIHHHHH", first_block[:0x12])

        blend_mode = struct.unpack("<H", first_block[0x1a:0x1c])[0]
        initial_rotate = struct.unpack("<H", first_block[0x1c:0x1e])[0]
        initial_x_zoom, initial_y_zoom = struct.unpack("<HH", first_block[0x1e:0x22])
        initial_animation_idx, initial_clut = struct.unpack("<BB", first_block[0x28:0x2a])
        initial_center_x, initial_center_y = struct.unpack("<HH", first_block[0x22:0x26])

        blend_mode = ctypes.c_short(blend_mode).value

        initial_x = ctypes.c_short(initial_x).value
        initial_y = ctypes.c_short(initial_y).value

        initial_center_x = ctypes.c_short(initial_center_x).value
        initial_center_y = ctypes.c_short(initial_center_y).value

        initial_x_zoom = ctypes.c_short(initial_x_zoom).value
        initial_y_zoom = ctypes.c_short(initial_y_zoom).value
        initial_x_zoom /= 4096
        initial_y_zoom /= 4096

        initial_rotate = ctypes.c_short(initial_rotate).value
        initial_rotate /= 1024
        initial_rotate *= 90

        if DEBUG_MODE:
            print("[%08x] %d to %d: %08x %04x" % (cur_offset, frame_start_timestamp, frame_end_timestamp, entry_id, anim_id))

            hexdump.hexdump(first_block)
            print()

        frame_count = struct.unpack("<I", infile.read(4))[0]
        frames = []

        initial_alpha = struct.unpack("<B", first_block[0x16:0x17])[0]

        w, h, blend_a, blend_r, blend_g, blend_b = struct.unpack("<HHBBBB", first_block[0x12:0x1a])

        if anim_id > len(animation_filenames):
            infile.seek(frame_count * 0x20)
            continue

        if entry_type == 0:
            if DEBUG_MODE:
                if anim_id < len(animation_filenames):
                    print(animation_filenames[anim_id])

            base_images.append(animation_filenames[anim_id])

        elif entry_type == 1:
            base_images.append(Image.new("RGBA", (w * upscale_ratio, h * upscale_ratio), (blend_r, blend_g, blend_b, 255)))

        elif entry_type == 2:
            # Frame information
            frame_width, frame_height = struct.unpack("<HH", first_block[0x12:0x16])
            continue

        for i in range(frame_count):
            cur_block = infile.read(0x20)
            frames.append(cur_block)


            if DEBUG_MODE:
                hexdump.hexdump(cur_block)

            start_timestamp, end_timestamp, command, _, entry_idx, subcommand = struct.unpack("<IIHHHH", cur_block[:16])

            if command in [4096]:
                continue

            for idx in range(start_timestamp, end_timestamp + 1):
                if idx not in render_by_timestamp:
                    render_by_timestamp[idx] = {}

                if entry_idx not in render_by_timestamp[idx]:
                    render_by_timestamp[idx][entry_idx] = {}

            if command == 0:
                if subcommand == 0:
                    subcommand_0_animate_move(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp)

                elif subcommand == 1:
                    subcommand_0_animate_center(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp)

                elif subcommand == 2:
                    subcommand_0_animate_zoom(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp)

                elif subcommand == 3:
                    subcommand_0_animate_rotation(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp)

                elif subcommand == 4:
                    subcommand_0_animate_transparency(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp)

                elif subcommand in [6, 8]:
                    anim_idx = sprite_filenames.index(animation_filenames[anim_id])
                    subcommand_0_animate_image(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp, sprite_filenames, anim_idx)

                elif subcommand in [7, 9]:
                    subcommand_0_animate_palette(cur_block, render_by_timestamp, entry_idx, start_timestamp, end_timestamp, frame_end_timestamp)

                else:
                    print("Unknown effect subcommand", subcommand)
                    exit(1)

            elif command == 1 and subcommand == 0:
                anim_idx = sprite_filenames.index(animation_filenames[anim_id])
                animate_sprite_raw(cur_block, render_by_timestamp, sprite_filenames, anim_idx, initial_animation_idx, start_timestamp, end_timestamp, entry_idx)

            elif command == 1 and subcommand == 1:
                anim_idx = sprite_filenames.index(animation_filenames[anim_id])
                animate_palette_raw(cur_block, render_by_timestamp, sprite_filenames, anim_idx, initial_animation_idx, start_timestamp, end_timestamp, entry_idx)

            elif command == 1 and subcommand == 2:
                anim_idx = sprite_filenames.index(animation_filenames[anim_id])
                animate_sprite_scroll(cur_block, render_by_timestamp, sprite_filenames, anim_idx, initial_animation_idx, start_timestamp, end_timestamp, entry_idx)

            elif command == 1 and subcommand == 4:
                anim_idx = sprite_filenames.index(animation_filenames[anim_id])
                animate_sprite(cur_block, render_by_timestamp, sprite_filenames, anim_idx, initial_animation_idx, start_timestamp, end_timestamp, entry_idx)

            elif command == 1 and subcommand == 5:
                anim_idx = sprite_filenames.index(animation_filenames[anim_id])
                animate_palette(cur_block, render_by_timestamp, sprite_filenames, anim_idx, initial_animation_idx, start_timestamp, end_timestamp, entry_idx)

            else:
                print("Unknown command block %04x" % command)
                exit(1)

            if DEBUG_MODE:
                print()

        if DEBUG_MODE:
            print()

        fill_last_values(render_by_timestamp, entry_idx, frame_start_timestamp, frame_end_timestamp, base_images[-1], initial_alpha, initial_x, initial_y, initial_clut, initial_x_zoom, initial_y_zoom, initial_rotate, initial_center_x, initial_center_y, blend_mode, entry_id)

    return render_by_timestamp, (frame_width, frame_height)


def do_render_frame(render_by_timestamp, frame_width, frame_height, upscale_ratio, k, fcn_sprites):
    if DEBUG_MODE:
        print()

    render_frame = Image.new("RGBA", (frame_width * upscale_ratio, frame_height * upscale_ratio), (0, 0, 0, 0))
    for k2 in sorted(render_by_timestamp[k].keys())[::-1]:
        if not render_by_timestamp[k][k2] or 'filename' not in render_by_timestamp[k][k2]:
            continue

        if DEBUG_MODE:
            print(k, k2, render_by_timestamp[k][k2])

        if isinstance(render_by_timestamp[k][k2]['filename'], Image.Image):
            image = render_by_timestamp[k][k2]['filename'].copy()

        else:
            if render_by_timestamp[k][k2]['filename'] not in fcn_sprites:
                print("Couldn't find", render_by_timestamp[k][k2]['filename'])
                continue

            image = fcn_sprites[render_by_timestamp[k][k2]['filename']][render_by_timestamp[k][k2]['clut']].copy()

        center_x = render_by_timestamp[k][k2].get('center_x', image.width // 2) * upscale_ratio
        center_y = render_by_timestamp[k][k2].get('center_y', image.height // 2) * upscale_ratio

        if center_x != image.width // 2 or center_y != image.height // 2:
            image3 = Image.new(image.mode, (image.width * 2, image.height * 2), (0, 0, 0, 0))
            image3.paste(image, ((image3.width // 2) - center_x, (image3.height // 2) - center_y), image)

            image.close()
            del image

            image = image3

        if render_by_timestamp[k][k2].get('opacity', 1.0) != 1.0:
            pixels = image.load()
            for y in range(image.height):
                for x in range(image.width):
                    pixels[x, y] = (pixels[x, y][0], pixels[x, y][1], pixels[x, y][2], int(pixels[x, y][3] * render_by_timestamp[k][k2].get('opacity', 1.0)))

        new_w = image.width * render_by_timestamp[k][k2]['x_zoom']
        new_h = image.height * render_by_timestamp[k][k2]['y_zoom']

        if new_w < 0:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
            new_w = abs(new_w)

        if new_h < 0:
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            new_h = abs(new_h)

        new_w = round(new_w)
        new_h = round(new_h)

        if (new_w, new_h) != image.size:
            if new_w <= 0 or new_h <= 0:
                image = Image.new(image.mode, image.size, (0, 0, 0, 0))
            else:
                image = image.resize((new_w, new_h))

        if 'offset_x' in render_by_timestamp[k][k2]:
            image = ImageChops.offset(image, render_by_timestamp[k][k2]['offset_x'] * upscale_ratio, 0)

        if 'offset_y' in render_by_timestamp[k][k2]:
            image = ImageChops.offset(image, 0, render_by_timestamp[k][k2]['offset_y'] * upscale_ratio)

        if 'rotate' in render_by_timestamp[k][k2]:
            image = image.rotate(-render_by_timestamp[k][k2]['rotate'], expand=True)

        image2 = Image.new(render_frame.mode, render_frame.size, (0, 0, 0, 0))

        new_x = render_by_timestamp[k][k2]['x'] * upscale_ratio - (frame_width // 2)
        new_x = int(new_x + ((frame_width - image.width) // 2))

        new_y = render_by_timestamp[k][k2]['y'] * upscale_ratio - (frame_height // 2)
        new_y = int(new_y + ((frame_height - image.height) // 2))

        if render_by_timestamp[k][k2].get('tile', 0) == 1:
            for i in range(0, image2.width, image.width):
                for j in range(0, image2.height, image.height):
                    image2.paste(image, (i, j))

        elif render_by_timestamp[k][k2].get('tile', 0) == 2:
            for i in range(0, image2.width, image.width):
                image2.paste(image, (i, new_y))

        elif render_by_timestamp[k][k2].get('tile', 0) == 3:
            for j in range(0, image2.height, image.height):
                image2.paste(image, (new_x, j))

        else:
            image2.paste(image, (new_x, new_y), image)

        if 'blend_mode' in render_by_timestamp[k][k2]:
            if render_by_timestamp[k][k2]['blend_mode'] == 1:
                render_frame = ImageChops.add(render_frame, image2)

            elif render_by_timestamp[k][k2]['blend_mode'] == 2:
                render_frame = ImageChops.subtract(render_frame, image2)

            else:
                render_frame.paste(image2, (0, 0), image2)

        else:
            render_frame = Image.alpha_composite(render_frame, image2)

    return render_frame


def parse_dat_inner_single(render_by_timestamp, output_filename, fcn_sprites, frame_width, frame_height, upscale_ratio=1, render_start_frame=-1, render_end_frame=-1):
    rendered_frames = {}

    with imageio.get_writer(output_filename, mode='I', fps=60, quality=10, format='FFMPEG') as writer:
        for k in tqdm.tqdm(sorted(render_by_timestamp.keys())):
            rendered_frame = do_render_frame(render_by_timestamp, frame_width, frame_height, upscale_ratio, k, fcn_sprites)

            npdata = numpy.asarray(rendered_frame, dtype='uint8')
            writer.append_data(npdata)


def parse_dat_inner_multi(render_by_timestamp, output_filename, fcn_sprites, frame_width, frame_height, upscale_ratio=1, render_start_frame=-1, render_end_frame=-1, max_threads=8):
    rendered_frames = {}

    import queue
    import threading
    def thread_worker():
        while True:
            k = queue_data.get()

            if k is None:
                break

            rendered_frames[k] = do_render_frame(render_by_timestamp, frame_width, frame_height, upscale_ratio, k, fcn_sprites)

            queue_data.task_done()

    queue_data = queue.Queue()
    threads = []
    for _ in range(max_threads):
        thread = threading.Thread(target=thread_worker)
        thread.start()
        threads.append(thread)

    for k in render_by_timestamp:
        # Only render frames within the specified range
        if render_start_frame >= 0 and k < render_start_frame:
            continue

        if render_end_frame >= 0 and k > render_end_frame:
            continue

        queue_data.put((k))

    queue_data.join()

    for _ in range(max_threads):
        queue_data.put(None)

    for thread in threads:
        thread.join()

    with imageio.get_writer(output_filename, mode='I', fps=60, quality=10, format='FFMPEG') as writer:
        for k in sorted(rendered_frames, key=lambda x:int(x)):
            render_frame = rendered_frames[k]
            npdata = numpy.asarray(render_frame, dtype='uint8')
            writer.append_data(npdata)

            render_frame.close()


def parse_dat(dat_filename, output_filename, sprite_filenames, fcn_sprites, upscale_ratio=1, render_start_frame=-1, render_end_frame=-1, max_threads=8):
    with open(dat_filename, "rb") as infile:
        if infile.read(4) != b"AEBG":
            print("Not a AEBG animation file")
            exit(1)

        _, entry_count = struct.unpack("<II", infile.read(8))

        animation_filenames = read_filelist_from_dat(infile, entry_count)
        render_by_timestamp, (frame_width, frame_height) = read_animation_from_dat(infile, entry_count, animation_filenames, sprite_filenames, upscale_ratio)

    import time
    start_time = time.time()

    if max_threads == 1:
        parse_dat_inner_single(render_by_timestamp, output_filename, fcn_sprites, frame_width, frame_height, upscale_ratio, render_start_frame, render_end_frame)

    else:
        parse_dat_inner_multi(render_by_timestamp, output_filename, fcn_sprites, frame_width, frame_height, upscale_ratio, render_start_frame, render_end_frame, max_threads)

    print(time.time() - start_time, "elapsed")

