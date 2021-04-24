    # GFDM MP3 encryption key generator
# Point this tool at DA_LIST.BIN

import argparse
import struct
import sys

def generate_key(filename):
    enc_table = [
        0x006f3a5d, 0x0065f710, 0x0072a6cf, 0x0049cbfb, 0x004c77f8, 0x00778885, 0x007ae64a, 0x0015990a,
        0x002c2e6b, 0x00385225, 0x0061de2d, 0x003002e3, 0x00674ca7, 0x00362403, 0x00456126, 0x00109449,
        0x00453c03, 0x005c61a4, 0x001e3f73, 0x004716f5, 0x0040f1a4, 0x004df73c, 0x0096137b, 0x0052a72f,
        0x00667a2a, 0x007bf27e, 0x000a7036, 0x00165ab6, 0x0032bb75, 0x003e2961, 0x00792923, 0x001f101f
    ]

    hashsum = [sum(filename[::2]), sum(filename[1::2])]

    v0 = ((hashsum[0] << 8) | hashsum[1]) ^ 0xaaaaaaaa
    enc_key = enc_table[v0 & 0x1f]
    v0 = (v0 * enc_key)
    a0 = v0 & 0xffff0000
    v0 = ((v0 * enc_key) >> 15) & 0xffff
    a0 |= v0

    output = [
        ((hashsum[1] ^ a0) >> 16) & 0xffff,
        (hashsum[0] ^ a0) & 0xffff,
    ]

    output.append((((output[1] & 0x3c0) >> 6) | ((output[0] & 0x3c) << 2)) & 0xff)

    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--input', help='Input dump binary file', required=True)

    args = parser.parse_args()

    with open(args.input, "rb") as infile:
        infile.seek(0, 2)
        filelen = infile.tell()
        infile.seek(0)

        while infile.tell() < filelen:
            file_type, filename = struct.unpack("<H10s", infile.read(12))
            filename = filename.decode('shift-jis').strip('\0').strip()

            output = generate_key(filename.encode('shift-jis'))

            print("%04x %04x %02x %s" % (output[0], output[1], output[2], filename))
