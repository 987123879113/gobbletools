import argparse
import ctypes
import os
import struct

class DecodeGfdm:
    def __init__(self, data):
        self.data = data

        self.unk = int.from_bytes(data[:4], 'little')
        self.cur_offset = 4
        self.cur_bit = -1

        self.tree = self.build_tree()
        self.build_starts()
        self.build_lookups()

    def get_bit(self):
        def rshift(val, n): return val>>n if val >= 0 else (val+0x100000000)>>n

        if self.cur_bit < 0:
            self.cur_bit = 7
            self.orig_flag = self.data[self.cur_offset]
            self.flag = ctypes.c_byte(self.data[self.cur_offset]).value
            self.cur_offset += 1

        ret = rshift(self.flag, self.cur_bit) & 1
        self.cur_bit -= 1

        return ret

    def get_byte(self):
        cur_idx = 0x100

        while True:
            bit = self.get_bit()
            cur_idx = [self.lookup_l, self.lookup_r][bit][cur_idx]

            if cur_idx < 0x100:
                break

        return cur_idx


    def build_tree(self):
        tree = bytearray(0x100)
        tree_idx = 0
        s3 = 0

        if self.data[self.cur_offset] == 0:
            return self.data

        while tree_idx < 0x100:
            if self.get_bit() == 0:
                tree[tree_idx] = s3
                tree_idx += 1

            else:
                s1 = 1

                cnt = 0
                while self.get_bit() == 0:
                    cnt += 1

                while cnt > 0:
                    s1 = (s1 << 1) | self.get_bit()
                    cnt -= 1

                s3 ^= s1
                tree[tree_idx] = s3
                tree_idx += 1

        return tree

    def build_starts(self):
        self.statistics = [0] * 16
        for c in self.tree:
            if c >= 0x11:
                raise Exception("Invalid code")

            else:
                self.statistics[c] += 1

        self.starts = [0] * 16
        for i in range(1, 16-1):
            self.starts[i+1] = (self.starts[i] + self.statistics[i]) * 2

        self.offsets = [0] * len(self.tree)
        for idx in range(len(self.starts)):
            for i, c in enumerate(self.tree):
                if c == idx:
                    self.offsets[i] += self.starts[idx]
                    self.starts[idx] += 1

    def build_lookups(self):
        lookup_r = [0] * 0x10000
        lookup_l = [0] * 0x10000

        cur_idx = len(self.tree)
        next_idx = len(self.tree) + 1
        lookup_r[cur_idx] = lookup_l[cur_idx] = -1
        lookup_r[next_idx] = lookup_l[next_idx] = -1

        for i, c in enumerate(self.tree):
            if c == 0:
                continue

            cur_idx = len(self.tree)

            is_right = False
            for j in range(0, c):
                is_right = (self.offsets[i] >> (c - j - 1)) & 1

                if j + 1 == c:
                    break

                if is_right:
                    a1 = lookup_r[cur_idx]
                    if a1 == -1:
                        lookup_r[cur_idx] = next_idx

                    else:
                        cur_idx = a1

                else:
                    a1 = lookup_l[cur_idx]
                    if a1 == -1:
                        lookup_l[cur_idx] = next_idx

                    else:
                        cur_idx = a1

                if a1 == -1:
                    lookup_l[next_idx] = -1
                    lookup_r[next_idx] = -1
                    cur_idx = next_idx
                    next_idx += 1

            if is_right:
                lookup_r[cur_idx] = i

            else:
                lookup_l[cur_idx] = i

        self.lookup_r = lookup_r
        self.lookup_l = lookup_l

    def decode(self):
        output = []

        decomp_size = int.from_bytes(self.data[:4], 'little')
        for i in range(decomp_size):
            output.append(self.get_byte() & 0xff)

        return bytearray(output)


def decode_lz(input_data):
    output = bytearray()
    input_data = bytearray(input_data)
    idx = 0
    distance = 0
    control = 0

    while True:
        control >>= 1

        if (control & 0x100) == 0:
            control = input_data[idx] | 0xff00
            idx += 1

        data = input_data[idx]
        idx += 1

        if (control & 1) == 0:
            output.append(data)
            continue

        length = None
        if (data & 0x80) == 0:
            distance = ((data & 0x03) << 8) | input_data[idx]
            length = (data >> 2) + 2
            idx += 1

        elif (data & 0x40) == 0:
            distance = (data & 0x0f) + 1
            length = (data >> 4) - 7

        if length is not None:
            start_offset = len(output)
            idx2 = 0

            while idx2 <= length:
                output.append(output[(start_offset - distance) + idx2])
                idx2 += 1

            continue

        if data == 0xff:
            break

        length = data - 0xb9
        while length >= 0:
            output.append(input_data[idx])
            idx += 1
            length -= 1

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input file', required=True)
    parser.add_argument('-o', '--output', help='Output folder (optional)', default="output")

    args = parser.parse_args()

    key = bytearray([ 0x97, 0x47, 0x56, 0x37, 0xE4, 0xAB, 0xE4, 0xAB, 0x60, 0x61, 0x75, 0x11, 0x26, 0x41, 0xBE, 0x81, 0x97, 0x97, 0x22, 0x39, 0xE4, 0x1B, 0x84, 0xA0, 0x60, 0x61, 0x75, 0x14, 0x26, 0x41, 0xBE, 0x8A, 0x97, 0x27, 0x99, 0x32, 0xE4, 0x8B, 0x10, 0xA4, 0x60, 0x92, 0x29, 0x14, 0x26, 0x08, 0x41, 0x8A ])

    with open(args.input, "rb") as infile:
        data = bytearray(infile.read())
        file_count = int.from_bytes(data[:4], 'little')

        cur_offset = 0x10
        for i in range(file_count):
            for i in range(0x30):
                data[cur_offset+i] ^= key[i % len(key)]

            filename = data[cur_offset:cur_offset+0x20].decode('ascii').strip('\0')
            flag = data[cur_offset+0x2b]
            chunk_size = int.from_bytes(data[cur_offset+0x2c:cur_offset+0x30], 'little')

            # import hexdump
            # hexdump.hexdump(data[cur_offset:cur_offset+0x30])
            # print()

            cur_offset += 0x30

            print("%-32s: offset[%08x] size[%08x] flag[%d]" % (filename, cur_offset, chunk_size, flag))

            output_filename = os.path.join(args.output, filename)
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)

            chunk_data = data[cur_offset:cur_offset+chunk_size]
            with open(output_filename, "wb") as outfile:
                if flag == 1 and chunk_size > 0x10:
                    # Konami standard lzss compression
                    chunk_count = int.from_bytes(data[cur_offset:cur_offset+4], 'little')

                    chunk_offsets = [int.from_bytes(data[cur_offset+0x10+idx*4:cur_offset+0x10+idx*4+4], 'little') for idx in range(chunk_count)] + [chunk_size]

                    for idx, offset in enumerate(chunk_offsets[:-1]):
                        chunk = chunk_data[offset & 0x7fffffff:chunk_offsets[idx+1] & 0x7fffffff]

                        # print("%d: %08x -> %08x | %d" % (idx, offset, chunk_offsets[idx+1], len(chunk)))

                        # import hexdump
                        # hexdump.hexdump(chunk)

                        if offset & 0x80000000 == 0:
                            chunk = decode_lz(chunk)

                        else:
                            decoder = DecodeGfdm(chunk)
                            chunk = decoder.decode()

                            import hexdump
                            hexdump.hexdump(chunk[:0x20])
                            print()

                            chunk = decode_lz(chunk)

                        outfile.write(chunk)

                else:
                    # No compression
                    outfile.write(chunk_data)

            cur_offset += chunk_size

            if cur_offset & 0x0f != 0:
                cur_offset = (cur_offset + 0x10) & ~0x0f

