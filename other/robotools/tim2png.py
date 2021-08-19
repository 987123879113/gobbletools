#!/usr/bin/python

#
# tim2png - Convert PlayStation TIM image to PNG format
#
# Copyright (C) 2014 Christian Bauer <www.cebix.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#

__version__ = "1.0"

import sys
import os
import struct

from PIL import Image
from PIL import ImagePalette


# Convert 16-bit little-endian ABGR format to ARGB (PIL's "BGR;15" format).
def convertABGR(data, first_alpha=False):
    output = bytearray()
    output2 = []

    has_transparency = False
    for i in range(0, len(data), 2):
        pixel = struct.unpack_from("<H", data, i)[0]

        r = pixel & 0x1f
        g = (pixel >> 5) & 0x1f
        b = (pixel >> 10) & 0x1f
        a = pixel & 0x8000
        pixel = a | (r << 10) | (g << 5) | b

        # first_alpha is a hacky parameter to detect 4bpp stuff used for name plates
        if (r, g, b) in [(0, 0, 0)] or (first_alpha and pixel in [0xffff, 0x8000]):
            a = 0
            has_transparency = True

        else:
            a = 255

        output.extend(struct.pack("<H", pixel))

        r = int((255 / 31) * r)
        g = int((255 / 31) * g)
        b = int((255 / 31) * b)

        output2.append((r, g, b, a))

    return output, output2, has_transparency


# Read TIM image from file
def readTimImage(f, clut_idx=0, disable_transparency=False):
    # Check header
    header = f.read(8)
    if header[:4] != b"\x10\x00\x00\x00":
        raise SyntaxError("Not a TIM file")

    flags = struct.unpack_from("<I", header, 4)[0]
    if flags & 0xfffffff0:
        raise SyntaxError("Not a TIM file")

    pMode = flags & 7
    if pMode > 4:
        raise SyntaxError("Not a TIM file")
    elif pMode == 4:
        raise ValueError("Mixed mode images not yet supported")

    # Read CLUT, if present
    palette = None

    haveClut = flags & 8
    transparency_idx = None
    has_transparency = False
    clut_count = 0
    if haveClut:
        # Check CLUT header
        clutSize = struct.unpack("<I", f.read(4))[0]
        if clutSize < 12:
            raise ValueError("Size of CLUT data too small")

        numEntries = (clutSize - 12) // 2

        f.read(8)  # skip DX/DY/H/W (frame buffer location and size)

        # Read CLUT data and convert to BGR;15
        clut = f.read(numEntries * 2)

        palette_size = 0x10

        if pMode == 1:
            palette_size = 0x100

        if clut_idx < numEntries // palette_size:
            clut = clut[clut_idx*(palette_size*2):]

        clut_count = numEntries // palette_size

        if pMode == 0:
            clut += b'\xff' * 32 * 16  # extend to 256 entries

        clut = clut[:0x200]
        clut, clut2, has_transparency = convertABGR(clut, pMode == 0)

        for i in range(0, len(clut), 2):
            if clut[i] == 0 and clut[i+1] == 0:
                transparency_idx = i // 2
                break

        palette = ImagePalette.raw("BGR;15", bytes(clut))

    has_transparency = False if disable_transparency else has_transparency

    # Read pixel data
    dataSize = struct.unpack("<I", f.read(4))[0]
    if dataSize < 12:
        raise ValueError("Size of pixel data too small")

    f.read(4)  # skip DX/DY (frame buffer location)

    width, height = struct.unpack("<HH", f.read(4))
    expectedSize = width * height * 2  # width is in 16-bit units

    pixelData = f.read(expectedSize)

    # Create image, converting pixel data if necessary
    if pMode in [0, 1]:
        # 4-bit indexed mode, 4 pixels in each 16-bit unit
        width *= 2

        if pMode == 0:
            width *= 2

            # Expand 4-bit pixel data to 8-bit
            output = bytearray()
            for x in pixelData:
                pix0 = x & 0x0f
                pix1 = x >> 4

                output.append(pix0)
                output.append(pix1)

        else:
            output = pixelData

        # image = Image.frombytes("P", (width, height), bytes(output), "raw", "P", 0, 1)
        # image.palette = palette

        if has_transparency:
            image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            pixels = image.load()

            i = 0
            for y in range(height):
                for x in range(width):
                    pixels[x, y] = clut2[output[i]]
                    i += 1

        else:
            image = Image.frombytes("P", (width, height), bytes(output), "raw", "P", 0, 1)
            image.palette = palette

            if transparency_idx != None:
                import io
                image_data = io.BytesIO()
                image.save(image_data, "PNG", transparency=transparency_idx)

                image.close()
                del image

                image = Image.open(image_data)

    elif pMode == 2:
        # 16-bit direct mode, convert from ABGR to ARGB
        output = convertABGR(pixelData)

        image = Image.frombytes("RGB", (width, height), bytes(output), "raw", "BGR;15", 0, 1)

    elif pMode == 3:
        # 24-bit direct mode, 2 pixels in three 16-bit units
        width = width * 2 / 3

        image = Image.frombytes("RGB", (width, height), bytes(pixelData), "raw", "RGB", 0, 1)

    return image.convert("RGBA"), clut_count


if __name__ == "__main__":
    # Print usage information and exit.
    def usage(exitcode, error = None):
        print("Usage: %s [OPTION...] <input.tim> [<output.png>]" % os.path.basename(sys.argv[0]))
        print("  -V, --version                   Display version information and exit")
        print("  -?, --help                      Show this help message")

        if error is not None:
            print("\nError:", error, file=sys.stderr)

        sys.exit(exitcode)

    # Parse command line arguments
    inputFileName = None
    outputFileName = None

    for arg in sys.argv[1:]:
        if arg == "--version" or arg == "-V":
            print("tim2png", __version__)
            sys.exit(0)
        elif arg == "--help" or arg == "-?":
            usage(0)
        elif arg == "--list" or arg == "-l":
            listFiles = True
        elif arg[0] == "-":
            usage(64, "Invalid option '%s'" % arg)
        else:
            if inputFileName is None:
                inputFileName = arg
            elif outputFileName is None:
                outputFileName = arg
            else:
                usage(64, "Unexpected extra argument '%s'" % arg)

    if inputFileName is None:
        usage(64, "No input file specified")
    if outputFileName is None:
        outputFileName = os.path.splitext(inputFileName)[0] + ".png"

    # Read input image
    try:
        f = open(inputFileName, "rb")
    except IOError as e:
        print("Error opening file '%s': %s" % (inputFileName, e.strerror), file=sys.stderr)
        sys.exit(1)

    try:
        image = readTimImage(f)
    except Exception as e:
        print("Error reading TIM image '%s': %s" % (inputFileName, str(e)), file=sys.stderr)
        sys.exit(1)

    # Write output image
    if image:
        image[0].save(outputFileName, "PNG")
        print("Written '%s'" % outputFileName)
