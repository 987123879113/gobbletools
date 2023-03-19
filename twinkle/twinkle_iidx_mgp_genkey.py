import argparse

def generate_key(filename):
    key = 0

    for c in filename[-6:][::-1]: # Not necessary to reverse the string, but the real game reads from the tail backward so recreate for accuracy
        key += ord(c)

        if ord(c) - 0x61 >= 0x1a:
            # I'm not sure of anything that hits this path so I can't verify, but it's in the ASM code
            key += 0xffe0

    return key & 0xffff


def decrypt_data(input_key, input_filename, output_filename):
    key = generate_key(input_key)

    print("Key: %s -> %04x" % (input_key, key))

    print("Decrypting %s..." % input_filename)

    with open(input_filename, "rb") as infile:
        data = bytearray(infile.read())

    for i in range(0, len(data), 2):
        curdata = ((data[i+1] << 8) | data[i]) ^ key

        data[i] = (((curdata & 0x1c00) >> 5) | (curdata & 0x1f)) & 0xff
        data[i+1] = (((curdata & 0xe000) >> 8) | ((curdata & 0x3e0) >> 5)) & 0xff

        key = (key + 0x71) & 0xffff

    with open(output_filename, "wb") as outfile:
        outfile.write(data)

    print("Saved to %s!" % output_filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', help='Input file', required=True)
    parser.add_argument('--output', help='Output file', required=True)
    parser.add_argument('--key', help='String to be used for key (usually the file path from root, such as "/DATA/511.MGP")', required=True)
    args = parser.parse_args()

    decrypt_data(args.key, args.input, args.output)
