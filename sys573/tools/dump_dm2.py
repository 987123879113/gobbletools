import argparse
import os
import struct

import hexdump


def decode_lz(input_data):
    # Based on decompression code from IIDX GOLD CS
    input_data = bytearray(input_data)
    idx = 0

    output = bytearray()

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


def parse_pathtab(filename):
    data = open(filename, "rb").read()

    count = int.from_bytes(data[:4], byteorder="little")

    entries = []
    for i in range(count):
        filename_hash, file_offset, file_size = struct.unpack("<III", data[4+i*0xc:4+(i+1)*0xc])

        entries.append({
            'filename_hash': filename_hash,
            'offset': file_offset,
            'size': file_size,
        })

    return entries


def dump_charts(input_path, output_folder):
    exe_data = open(os.path.join(input_path, "GAME.DAT"), "rb").read()
    table_offset = exe_data.find(b"\x01seq124norm.dsq\x00")
    print("table_offset: %08x" % table_offset)

    if table_offset == -1:
        print("Couldn't find file table")
        exit(1)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    entries = []
    while table_offset < len(exe_data):
        if exe_data[table_offset] == 0xff:
            break

        if exe_data[table_offset] != 0x01:
            table_offset += 0x40
            continue

        filename = exe_data[table_offset+1:table_offset+0x10].decode('ascii').strip('\0')
        offset = (int.from_bytes(exe_data[table_offset+0x38:table_offset+0x3c], byteorder="little") + 1) * 0x800
        size = int.from_bytes(exe_data[table_offset+0x3c:table_offset+0x40], byteorder="little")
        table_offset += 0x40

        output_filename = os.path.join(output_folder, filename)
        print("Extracting %s..." % output_filename)

        with open(output_filename, "wb") as outfile:
            outfile.write(exe_data[offset:offset+size])


def dump_diskfile(input_path, output_folder):
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)

    entries = parse_pathtab(os.path.join(input_path, "PATHTAB.BIN"))

    with open(os.path.join(input_path, "DISKFILE.BIN"), "rb") as infile:
        for idx, entry in enumerate(entries):
            output_filename = "output_%04d.bin" % idx

            infile.seek(entry['offset'])

            print(entry)

            with open(os.path.join(output_folder, output_filename), "wb") as outfile:
                try:
                    outfile.write(decode_lz(infile.read(entry['size'])))

                except:
                    outfile.write(infile.read(entry['size']))




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input folder', required=True)
    parser.add_argument('-o', '--output', help='Output folder (optional)', default="")

    args = parser.parse_args()

    dump_charts(args.input, os.path.join(args.output, "charts"))
    dump_diskfile(args.input, args.output)


