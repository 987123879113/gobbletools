import argparse
import hashlib
import json
import os
import sys

DATABASE_FILENAME = "db.json"

def get_database(filename=DATABASE_FILENAME):
    db = json.load(open(filename))

    output = {}
    for sha1 in db:
        k = db[sha1]

        if len(k) == 1:
            output[sha1] = {
                'sha1': sha1,
                'key1': k[0],
            }

        else:
            output[sha1] = {
                'sha1': sha1,
                'key1': k[0],
                'key2': k[1],
                'key3': k[2]
            }

    return output



def get_key_information(sha1):
    db = get_database()
    sha1 = sha1.upper()

    song = db.get(sha1, None)

    if not song:
        return (None, None, None)

    if 'key1' in song and 'key2' not in song and 'key3' not in song:
        return (song['key1'], None, None)

    return (song['key1'], song['key2'], song['key3'])


def is_bit_set(value, n):
    return (value >> n) & 1


# Thanks SaxxonPike for helping with this one
def decrypt_ddrsbm(data, data_len, key):
    def rot(c):
        return ((c >> 7) & 1) | ((c << 1) & 0xff)

    key_state = is_bit_set(key, 0x0d) << 15 | \
        is_bit_set(key, 0x0b) << 14 | \
        is_bit_set(key, 0x09) << 13 | \
        is_bit_set(key, 0x07) << 12 | \
        is_bit_set(key, 0x05) << 11 | \
        is_bit_set(key, 0x03) << 10 | \
        is_bit_set(key, 0x01) << 9 | \
        is_bit_set(key, 0x0f) << 8 | \
        is_bit_set(key, 0x0e) << 7 | \
        is_bit_set(key, 0x0c) << 6 | \
        is_bit_set(key, 0x0a) << 5 | \
        is_bit_set(key, 0x08) << 4 | \
        is_bit_set(key, 0x06) << 3 | \
        is_bit_set(key, 0x04) << 2 | \
        is_bit_set(key, 0x02) << 1 | \
        is_bit_set(key, 0x00) << 0

    key_data = bytearray(16)
    for i in range(8):
        key_data[i * 2] = key_state & 0xff
        key_data[i * 2 + 1] = (key_state >> 8) & 0xff

        key_state = (rot(key_state >> 8) << 8) | rot(key_state & 0xff)

    scramble = bytearray([key_data[-1]]) + key_data[:-1]

    key_len = len(key_data)
    scramble_len = len(scramble)
    output_idx = 0

    output_data = bytearray(len(data))
    for idx in range(0, data_len):
        output_word = 0
        cur_data = (data[(idx * 2) + 1] << 8) | data[(idx * 2)]

        for cur_bit in range(0, 8):
            even_bit_shift = (cur_bit * 2) & 0xff
            odd_bit_shift = (cur_bit * 2 + 1) & 0xff

            is_even_bit_set = int((cur_data & (1 << even_bit_shift)) != 0)
            is_odd_bit_set = int((cur_data & (1 << odd_bit_shift)) != 0)
            is_key_bit_set = int((key_data[idx % key_len] & (1 << cur_bit)) != 0)
            is_scramble_bit_set = int((scramble[idx % scramble_len] & (1 << cur_bit)) != 0)

            if is_scramble_bit_set == 1:
                is_even_bit_set, is_odd_bit_set = is_odd_bit_set, is_even_bit_set

            if ((is_even_bit_set ^ is_key_bit_set)) == 1:
                output_word |= 1 << even_bit_shift

            if is_odd_bit_set == 1:
                output_word |= 1 << odd_bit_shift

        output_data[output_idx] = (output_word >> 8) & 0xff
        output_data[output_idx+1] = output_word & 0xff
        output_idx += 2

    return bytearray(output_data)


# You crazy for this one
# Thanks anon and RC
def decrypt(data, data_len, key1, key2, key3):
    def bit_swap(v, b15, b14, b13, b12, b11, b10, b9, b8, b7, b6, b5, b4, b3, b2, b1, b0):
        return (is_bit_set(v, b15) << 15) | (is_bit_set(v, b14) << 14) | (is_bit_set(v, b13) << 13) | (is_bit_set(v, b12) << 12) |\
               (is_bit_set(v, b11) << 11) | (is_bit_set(v, b10) << 10) | (is_bit_set(v, b9) << 9)   | (is_bit_set(v, b8) << 8)   |\
               (is_bit_set(v, b7) << 7)   | (is_bit_set(v, b6) << 6)   | (is_bit_set(v, b5) << 5)   | (is_bit_set(v, b4) << 4)   |\
               (is_bit_set(v, b3) << 3)   | (is_bit_set(v, b2) << 2)   | (is_bit_set(v, b1) << 1)   | (is_bit_set(v, b0) << 0)

    output_data = bytearray(len(data))

    for idx in range(0, data_len):
        v = (data[idx * 2 + 1] << 8) | data[idx * 2]

        m = key1 ^ key2

        v = bit_swap(
            v,
            15 - is_bit_set(m, 0xF),
            14 + is_bit_set(m, 0xF),
            13 - is_bit_set(m, 0xE),
            12 + is_bit_set(m, 0xE),
            11 - is_bit_set(m, 0xB),
            10 + is_bit_set(m, 0xB),
            9 - is_bit_set(m, 0x9),
            8 + is_bit_set(m, 0x9),
            7 - is_bit_set(m, 0x8),
            6 + is_bit_set(m, 0x8),
            5 - is_bit_set(m, 0x5),
            4 + is_bit_set(m, 0x5),
            3 - is_bit_set(m, 0x3),
            2 + is_bit_set(m, 0x3),
            1 - is_bit_set(m, 0x2),
            0 + is_bit_set(m, 0x2)
        )

        for p in [(0x0d, 14), (0x0c, 12), (0x0a, 10), (0x07, 8), (0x06, 6), (0x04, 4), (0x01, 2), (0x00, 0)]:
            v ^= is_bit_set(m, p[0]) << p[1]

        v &= 0xffff

        v ^= bit_swap(
            key3,
            7, 0, 6, 1,
            5, 2, 4, 3,
            3, 4, 2, 5,
            1, 6, 0, 7
        )

        output_data[idx * 2] = (v >> 8) & 0xff
        output_data[idx * 2 + 1] = v & 0xff

        key1 = ((key1 & 0x8000) | ((key1 << 1) & 0x7FFE) | ((key1 >> 14) & 1)) & 0xFFFF

        if (((key1 >> 15) ^ key1) & 1) != 0:
            key2 = ((key2 << 1) | (key2 >> 15)) & 0xFFFF

        key3 += 1

    return bytearray(output_data)


def encrypt(data, data_len, key1, key2, key3):
    def bit_swap(v, b15, b14, b13, b12, b11, b10, b9, b8, b7, b6, b5, b4, b3, b2, b1, b0):
        return (is_bit_set(v, b15) << 15) | (is_bit_set(v, b14) << 14) | (is_bit_set(v, b13) << 13) | (is_bit_set(v, b12) << 12) |\
               (is_bit_set(v, b11) << 11) | (is_bit_set(v, b10) << 10) | (is_bit_set(v, b9) << 9)   | (is_bit_set(v, b8) << 8)   |\
               (is_bit_set(v, b7) << 7)   | (is_bit_set(v, b6) << 6)   | (is_bit_set(v, b5) << 5)   | (is_bit_set(v, b4) << 4)   |\
               (is_bit_set(v, b3) << 3)   | (is_bit_set(v, b2) << 2)   | (is_bit_set(v, b1) << 1)   | (is_bit_set(v, b0) << 0)

    output_data = bytearray(len(data))

    for idx in range(0, data_len):
        v = (data[idx * 2 + 1] << 8) | data[idx * 2]

        m = key1 ^ key2

        v = bit_swap(
            v,
            15 - is_bit_set(m, 0xF),
            14 + is_bit_set(m, 0xF),
            13 - is_bit_set(m, 0xE),
            12 + is_bit_set(m, 0xE),
            11 - is_bit_set(m, 0xB),
            10 + is_bit_set(m, 0xB),
            9 - is_bit_set(m, 0x9),
            8 + is_bit_set(m, 0x9),
            7 - is_bit_set(m, 0x8),
            6 + is_bit_set(m, 0x8),
            5 - is_bit_set(m, 0x5),
            4 + is_bit_set(m, 0x5),
            3 - is_bit_set(m, 0x3),
            2 + is_bit_set(m, 0x3),
            1 - is_bit_set(m, 0x2),
            0 + is_bit_set(m, 0x2)
        )

        for p in [(0x0d, 14), (0x0c, 12), (0x0a, 10), (0x07, 8), (0x06, 6), (0x04, 4), (0x01, 2), (0x00, 0)]:
            v ^= is_bit_set(m, p[0]) << p[1]

        v &= 0xffff

        v ^= bit_swap(
            key3,
            3, 4, 2, 5,
            1, 6, 0, 7,
            7, 0, 6, 1,
            5, 2, 4, 3
        )

        output_data[idx * 2] = (v >> 8) & 0xff
        output_data[idx * 2 + 1] = v & 0xff

        key1 = ((key1 & 0x8000) | ((key1 << 1) & 0x7FFE) | ((key1 >> 14) & 1)) & 0xFFFF

        if (((key1 >> 15) ^ key1) & 1) != 0:
            key2 = ((key2 << 1) | (key2 >> 15)) & 0xFFFF

        key3 += 1

    return bytearray(output_data)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--input', help='Input file', default=None)
    parser.add_argument('--output', help='Output file', default=None)
    parser.add_argument('--sha1', help='Force usage of a specific SHA-1 for encryption keys (optional)', default=None)

    parser.add_argument('--key1', help='Key 1 (optional)', default=None, type=int)
    parser.add_argument('--key2', help='Key 2 (optional)', default=None, type=int)
    parser.add_argument('--key3', help='Key 3 (optional)', default=None, type=int)

    parser.add_argument('--native', help='Native decryption code only', default=False, action='store_true')
    parser.add_argument('--encrypt', help='Encrypt input instead of decrypt (uses 0,0,0 as key)', default=False, action='store_true')

    args = parser.parse_args()

    if not args.input:
        parser.print_help(sys.stderr)
        exit(-1)

    if not os.path.exists(args.input):
        print("Could not find file:", args.input)
        exit(-1)

    if args.output is None:
        args.output = os.path.splitext(args.input)[0] + '.MP3'

    if os.path.dirname(args.output) and not os.path.exists(os.path.dirname(args.output)):
        os.makedirs(os.path.dirname(args.output))

    with open(args.input, "rb") as infile:
        data = infile.read()

    if args.encrypt:
        key1 = 0
        key2 = 0
        key3 = 0

        if args.native:
            decrypt_func = encrypt

        else:
            import enc573
            decrypt_func = enc573.encrypt

    else:
        key1 = args.key1
        key2 = args.key2
        key3 = args.key3

        if key1 is None or key2 is None or key3 is None:
            sha1 = args.sha1
            if sha1 is None:
                m = hashlib.sha1()
                m.update(data)
                sha1 = m.hexdigest()

            if sha1 is None:
                raise Exception("A SHA-1 must be set to continue")

            print("Using SHA-1:", sha1)

            key1, key2, key3 = get_key_information(sha1)
            if key1 is None:
                raise Exception("Couldn't find key information for file with SHA-1 hash of %s" % (sha1))

        if args.native:
            decrypt_func, decrypt_ddrsbm_func = (decrypt, decrypt_ddrsbm)

        else:
            import enc573
            decrypt_func, decrypt_ddrsbm_func = (enc573.decrypt, enc573.decrypt_ddrsbm)

    if isinstance(key1, int) and isinstance(key2, int) and isinstance(key3, int):
        output_data = decrypt_func(data, len(data) // 2, key1, key2, key3)

    else:
        output_data = decrypt_ddrsbm_func(data, len(data) // 2, key1)

    with open(args.output, "wb") as outfile:
        outfile.write(output_data)

    print("Saved to", args.output)


if __name__ == "__main__":
    main()