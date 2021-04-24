import argparse
import hashlib
import os
import struct
import sys

def decrypt(data, key):
    # Pad key
    while len(key) % 2:
        key += b"\x00"

    # Prepare key as 16-bit words
    key = [int.from_bytes(key[i:i+2], byteorder="little") for i in range(0, len(key), 2)]

    # Generate extended key
    expanded_key = [ 0xb7e1, 0x5618, 0xf44f, 0x9286, 0x30bd, 0xcef4, 0x6d2b, 0x0b62,
                     0xa999, 0x47d0, 0xe607, 0x843e, 0x2275, 0xc0ac, 0x5ee3, 0xfd1a,
                     0x9b51, 0x3988, 0xd7bf, 0x75f6, 0x142d, 0xb264, 0x509b, 0xeed2,
                     0x8d09, 0x2b40, 0xc977, 0x67ae, 0x05e5, 0xa41c, 0x4253, 0xe08a ]

    # Mix key
    t0 = t1 = s1 = 0
    for x in range(32):
        a2 = expanded_key[x]
        a0 = key[x % len(key)]

        for k in range(3):
            v0 = a2 + t1 + t0
            v1 = (v0 & 0xffff) >> 3
            a2 = v1 | (v0 << 13)
            t1 = a2 & 0xffff

            a0 += t1 + t0
            v1 = a0 & 0xffff
            v0 = a0 & 0x0f
            a0 = (v1 << v0) | (v1 >> (0x10 - v0))
            t0 = a0 & 0xffff

        expanded_key[x] = t1
        key[x % len(key)] = t0

        v1 = (t1 & 0xff) & 0xff
        s1 = (s1 + v1) & 0xff

    v1 = ((s1 * 0x5AC056B1) >> 32) & 0xffffffff
    counter = ((s1 - (((v1 + ((s1 - v1) >> 1)) >> 7) * 0xbd) & 0xffffffff) + 0x43) & 0xff

    # If there's an extra byte at the end of the file, drop it because the data must be in 16-bit words to be decrypted.
    # This shouldn't affect any songs as far as I know since usually the last byte is a 00.
    # TODO: Determine if the MSU even decrypts or does anything with the last byte in the case of a non-even number of bytes.
    data = [int.from_bytes(data[i:i+2], byteorder="big") for i in range(0, len(data) // 2 * 2, 2)]

    # Decrypt data
    for i in range(len(data)):
        t0 = expanded_key[(counter + 3) % len(expanded_key)] & 0xffff
        t1 = expanded_key[(counter + 2) % len(expanded_key)] & 0xffff
        v1 = (data[i] - t0) & 0xffff
        v0 = ((t1 + t0) & 7) + 4
        v1 = (((v1 << (0x10 - v0)) | (v1 >> v0)) ^ t1) - (expanded_key[counter % len(expanded_key)] ^ expanded_key[(counter + 1) % len(expanded_key)])

        data[i] = v1 & 0xffff
        expanded_key[counter % len(expanded_key)] = (expanded_key[counter % len(expanded_key)] + expanded_key[(counter + 1) % len(expanded_key)]) & 0xffff
        counter = (counter + 1) & 0xff

    return bytearray(b"".join([c.to_bytes(2, byteorder="big") for c in data]))


def main(input_filename, output_filename=None):
    key = bytearray("!kAiNsYuu4NkAn3594NnAnbo9tyouzUi105DaisOugEnmIn4N", encoding="ascii")

    filename = os.path.splitext(os.path.basename(input_filename))[0]
    for idx, c in enumerate(filename.lower()):
        key[idx + len(filename)] = ord(c)

    md5hash = hashlib.md5()
    md5hash.update(key)
    md5key = bytearray(md5hash.digest())

    # Swap endianness of md5key array
    for i in range(0, len(md5key), 2):
        t = md5key[i]
        md5key[i] = md5key[i+1]
        md5key[i+1] = t

    data = bytearray(open(input_filename, "rb").read())
    data = decrypt(data, md5key)

    if not output_filename:
        output_filename = os.path.splitext(input_filename)[0] + ".mp3"

    with open(output_filename, "wb") as outfile:
        outfile.write(data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', help='Input file', required=True)
    parser.add_argument('--output', help='Output file', default=None)
    args = parser.parse_args()

    main(args.input, args.output)
