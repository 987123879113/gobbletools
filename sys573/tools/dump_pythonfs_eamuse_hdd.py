import argparse
import hashlib
import json
import os

BASE_ADDRESS = 0x101200

def dump_file(infile, entry):
    if entry['is_folder']:
        return

    target_path = entry['_path'] if entry['is_folder'] else os.path.dirname(entry['_path'])
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    cur_offset = infile.tell()
    infile.seek(entry['offset'])

    data = infile.read(entry['filesize'])
    with open(entry['_path'], "wb") as outfile:
        outfile.write(data)

    infile.seek(cur_offset)

    return hashlib.sha1(data).hexdigest()


def read_folder(infile, target_offset, curpath):
    entries = []

    cur_offset = infile.tell()
    infile.seek(target_offset)

    while True:
        filename = infile.read(0x10).decode('ascii').strip('\0')
        infile.read(0x04)
        filesize = int.from_bytes(infile.read(4), byteorder='big')
        infile.read(0x04)
        entry_type = int.from_bytes(infile.read(1), byteorder='big')
        offset = int.from_bytes(infile.read(3), byteorder='big') * 0x4000

        if filename in ['.', '..']:
            continue

        if not filename:
            break

        entry = {
            'filename': filename,
            'offset': (BASE_ADDRESS - 0x4000) + offset,
            'filesize': filesize,
            'is_folder': entry_type == 1,
            '_path': os.path.join(curpath, filename),
        }

        entry['_checksum'] = dump_file(infile, entry)

        print(entry)

        entries.append(entry)

    print()

    for entry in entries:
        if entry['is_folder']:
            print("Diving into %s @ %08x" % (entry['filename'], entry['offset']))
            entries += read_folder(infile, entry['offset'], entry['_path'])

    infile.seek(cur_offset)

    return entries

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', help='Input folder', default=None, required=True)
    parser.add_argument('-o', '--output', help='Output folder', default=None)
    parser.add_argument('-s', '--save-metadata', help='Save JSON metadata', default=False, action='store_true')

    args = parser.parse_args()

    if not args.output:
        args.output = os.path.splitext(os.path.basename(args.input))[0]

    with open(args.input, "rb") as infile:
        entries = read_folder(infile, BASE_ADDRESS, args.output)

        if args.save_metadata:
            metadata_path = os.path.join(args.output, "_metadata.json")
            json.dump(entries, open(metadata_path, "w"), indent=4)

