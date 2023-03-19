import argparse
import os


def parse_pmc(data, expected_read_len, expected_output_len):
    assert(data[:3] == b"PMC")

    method = data[3]
    length = int.from_bytes(data[4:8], 'big')

    # Only ever seen method 1, but 2 and 3 also exist
    # Method 2 is ??? (located @ 0x464f80)
    # Method 3 appears to be LZSS-based (located @ 0x465060)
    assert(method == 1)

    if expected_read_len <= 0 or expected_output_len <= 0:
        return []

    output = [0] * expected_output_len
    output_idx = 0

    data_idx = 8

    while data_idx - 8 < expected_read_len or output_idx > expected_output_len:
        temp_buf = list(range(0, 0x100))
        temp_buf2 = [0] * 0x100
        temp_buf3 = [0] * 0x100

        idx = 0

        while True:
            cur = data[data_idx]
            data_idx += 1

            if cur > 0x7f:
                idx = idx + cur - 0x7f
                cur = 0

            if idx == 0x100:
                break

            for _ in range(cur + 1):
                c = data[data_idx]
                data_idx += 1

                temp_buf[idx] = c

                if idx != c:
                    temp_buf2[idx] = data[data_idx]
                    data_idx += 1

                idx += 1

            if idx == 0x100:
                break

        idx = data[data_idx] * 0x100 + data[data_idx+1]
        data_idx += 2

        idx3 = 0
        while True:
            if idx3 == 0:
                if idx == 0:
                    break

                cur = data[data_idx]
                data_idx += 1
                idx -= 1

            else:
                idx3 -= 1
                cur = temp_buf3[idx3]

            c2 = temp_buf[cur]
            if cur == c2:
                output[output_idx] = cur ^ 0xbd
                output_idx += 1

            else:
                temp_buf3[idx3] = temp_buf2[cur]
                temp_buf3[idx3 + 1] = c2
                idx3 += 2

    if len(output) > length:
        output = output[:length]

    return output

def parse_pmca(input_filename, output_folder):
    data = bytearray(open(input_filename, "rb").read())

    assert(data[0:4] == b"PMCA")
    assert(data[4:8] == b"\1\0\0\0")  # Version maybe?

    filetable_chunk_offset = int.from_bytes(data[8:12], 'little')
    file_count = int.from_bytes(data[12:16], 'little')
    # data_chunk_offset = int.from_bytes(data[16:20], 'little')
    # data_chunk_len = int.from_bytes(data[20:24], 'little')

    filenames_chunk = data[24:24+filetable_chunk_offset]

    for i in range(file_count):
        offset = 24 + filetable_chunk_offset + (i * 0x18)
        chunk = data[offset:offset+0x18]
        filename_offset = int.from_bytes(chunk[0:4], 'little')
        filename = filenames_chunk[filename_offset:filenames_chunk.find(b'\0', filename_offset)].decode('ascii')

        data_offset = int.from_bytes(chunk[4:8], 'little')
        data_decompress_len = int.from_bytes(chunk[8:12], 'little')
        # data_flags = int.from_bytes(chunk[12:16], 'little')
        data_compressed_len = int.from_bytes(chunk[16:20], 'little')
        # data_unk = int.from_bytes(chunk[20:24], 'little')

        output_filename = os.path.join(output_folder, os.path.basename(os.path.splitext(input_filename)[0]), filename.replace("/", os.sep))
        output_dir = os.path.dirname(output_filename)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        print("Extracting %s..." % output_filename, input_filename)
        # import hexdump
        # hexdump.hexdump(chunk)
        # print()

        file_data = data[data_offset:data_offset+data_compressed_len]
        if file_data[:3] == b"PMC":
            file_data = parse_pmc(file_data, data_compressed_len - 8, data_decompress_len)

        assert(len(file_data) == data_decompress_len)

        open(output_filename, "wb").write(bytearray(file_data))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs="+", help='Input PGZ file')
    args = parser.parse_args()

    for filename in args.input:
        parse_pmca(filename, "output")
