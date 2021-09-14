import argparse
import os

def dump_gtdata(input_filename, output_folder):
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)

    with open("GTDATA.PAK", "rb") as infile:
        infile.read(4)

        count = int.from_bytes(infile.read(4), byteorder="little")

        entries = []
        for i in range(count):
            offset = int.from_bytes(infile.read(4), byteorder="little") * 0x800
            filesize = int.from_bytes(infile.read(4), byteorder="little")

            entries.append({
                'offset': offset,
                'filesize': filesize
            })

        for idx, entry in enumerate(entries):
            print(idx, entry)

            infile.seek(entry['offset'])

            output_filename = "output_%04d.bin" % idx
            with open(os.path.join(output_folder, output_filename), "wb") as outfile:
                outfile.write(infile.read(entry['filesize']))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input GTDATA file', required=True)
    parser.add_argument('-o', '--output', help='Output folder (optional)', default="")

    args = parser.parse_args()

    dump_gtdata(args.input, args.output)