import argparse
import copy
import ctypes
import glob
import hashlib
import json
import os
import pathlib
import struct
import string

import comp573
import sum573


def rebuild_checksum_table(cards):
    card_sizes = [len(x) // 0x8000 for x in cards]

    CHUNK_SIZE = 0x20000
    LAST_CHUNK_OFFSET = len(cards[0]) - CHUNK_SIZE
    LAST_CHUNK_CHECKSUM_OFFSET = LAST_CHUNK_OFFSET + 0x10

    # Set entire checksum.dat section to zero
    cards[0] = cards[0][:LAST_CHUNK_CHECKSUM_OFFSET] + bytearray([0] * 0x1ff0) + cards[0][LAST_CHUNK_OFFSET + 0x2000:]

    # Calculate checksums for GAME.DAT
    cards = sum573.add_checksums(cards, card_sizes, CHUNK_SIZE, LAST_CHUNK_CHECKSUM_OFFSET, 0, 1)

    # Balance out the sums at this point because otherwise the chunk checksum won't match
    cards = sum573.balance_sums(cards, card_sizes, LAST_CHUNK_OFFSET)

    # Set the real checksum of the last section finally
    table_checksum_idx = len(cards[0]) // CHUNK_SIZE
    table_checksum_offset = LAST_CHUNK_CHECKSUM_OFFSET + ((table_checksum_idx - 1) * 4)
    cards[0][table_checksum_offset:table_checksum_offset+4] = sum573.checksum_chunk(cards[0], LAST_CHUNK_OFFSET, CHUNK_SIZE)

    # Add checksums for other DATs now
    cards = sum573.add_checksums(cards, card_sizes, CHUNK_SIZE, LAST_CHUNK_CHECKSUM_OFFSET, 1, len(cards) - 1)

    sum573.balance_sums(cards, card_sizes, LAST_CHUNK_OFFSET)


def get_filename_hash(filename, entry):
    hash = 0

    if 'filename_hash' in entry:
        return entry['filename_hash']

    if filename.startswith("_output_") and filename.endswith(".bin"):
        hash = int(filename.replace("_output_", "").replace(".bin", ""), 16)
        return hash

    for cidx, c in enumerate(filename):
        for i in range(6):
            hash = ctypes.c_int(((hash >> 31) & 0x4c11db7) ^ ((hash << 1) | ((ord(c) >> i) & 1))).value

    hash &= 0xffffffff

    return hash


def encrypt_data(data, input_key):
    def calculate_key(input):
        key = 0

        for c in input.upper():
            if c in string.ascii_uppercase:
                key -= 0x37

            elif c in string.ascii_lowercase:
                key -= 0x57

            elif c in string.digits:
                key -= 0x30

            key += ord(c)

        return key & 0xff

    val = 0x41C64E6D
    key1 = (val * calculate_key(input_key)) & 0xffffffff
    counter = 0

    for idx, c in enumerate(data):
        val = ((key1 + counter) >> 5) ^ c
        data[idx] = val & 0xff
        counter += 0x3039

    return data


def get_filetable(input_folder, input_modified_list, patch_dir=""):
    entries = []
    new_entries = []

    if input_modified_list and os.path.exists(input_modified_list):
        new_entries += json.load(open(input_modified_list))

    metadata_path = os.path.join(input_folder, "_metadata.json")
    if os.path.exists(metadata_path):
        entries = json.load(open(metadata_path)).get('files', [])

        for entry in json.load(open(metadata_path)).get('modified', []):
            exists = False
            for new_entry in new_entries:
                if entry['filename'] == new_entry['filename']:
                    exists = True

            if not exists:
                new_entries.append(entry)

    new_entry_filenames = []
    if new_entries:
        for entry in new_entries:
            entry['_path'] = os.path.join(input_folder, entry['filename'])
            entry['filename_hash'] = get_filename_hash(entry['filename'], entry)
            entry['_modified'] = True

            if entry.get('patch', None) is not None:
                entry['patch'] = os.path.join(patch_dir, entry['patch'])

            new_entry_filenames.append(entry['filename'])

    if entries:
        for entry in entries:
            entry['_path'] = os.path.join(input_folder, entry['filename'])
            entry['filename_hash'] = get_filename_hash(entry['filename'], entry)

            if entry.get('patch', None) is not None:
                entry['patch'] = os.path.join(patch_dir, entry['patch'])

            # # Free some space by removing any MP3s actually inside the flash card by default
            # if entry['filename'].startswith("data/mp3/enc"):
            #     entry['_free'] = True

            # # Free even more space by removing all of the data in the mdb folder besides the mdb.bin
            # if entry['filename'].startswith("data/mdb/") and entry['filename'] not in ['data/mdb/mdb.bin']:
            #     entry['_free'] = True

            # Free up the space used by files that will be overwritten
            if entry['filename'] in new_entry_filenames:
                for entry2 in new_entries:
                    if entry2['filename'] == entry['filename']:
                        size = entry['filesize']

                        if (size % 0x800) != 0:
                            padding = 0x800 - (size % 0x800)

                        else:
                            padding = 0x800

                        entry2['_orig_filesize'] = entry['filesize'] + padding

                        break

                entry['_free'] = True

    return sorted(entries + new_entries, key=lambda x: x['filename_hash'])


def get_data_from_entry(entry):
    data = open(os.path.normpath(entry['_path']), "rb").read()

    if entry.get('patch', None) is not None:
        if entry.get('patch_format') == "bsdiff4":
            import bsdiff4
            data = bsdiff4.patch(data, open(entry['patch'], "rb").read())

    return bytearray(data)


def create_gamedata(entries, base_offset, memory, enc_key, override_edit_section):
    # You can modify this to default to unused and you can probably squeeze a little bit more data
    # into the cards, but you will almost surely run over some data you shouldn't touch so be careful.
    memory_map = [bytearray([1] * len(mem)) for mem in memory] # 0 = unused, 1 = used
    memory_map[0][:0x200000] = [1] * 0x200000 # Reserve this section for the program code
    memory_map[1][0x18c0000:0x1b66800] = [1] * (0x1b66800 - 0x18c0000) # Reserve this section because it's where system sounds reside (not in actual file table)

    if override_edit_section:
        memory_map[1][0x1b66800:0x2000000] = [0] * (0x2000000 - 0x1b66800) # Unreserve the space where edit data is normally stored

    # Find the data
    entries_work = entries[::]

    # Mark unmodified data as used and freed data as unused
    for entry in entries_work[::]:
        if entry.get('_modified', False):
            continue

        cur_memory = entry['offset']

        size = entry['filesize']
        if (size % 0x800) != 0:
            size += 0x800 - (size % 0x800)

        if entry.get('_free', False):
            memory_map[entry.get('flag_loc', 0)][cur_memory:cur_memory + size] = [0] * size

        else:
            memory_map[entry.get('flag_loc', 0)][cur_memory:cur_memory + size] = [1] * size

        entries_work.remove(entry)

    entries_work = [x for x in entries_work if not x.get('_free', False)]
    entries = [x for x in entries if not x.get('_free', False)]

    entries_work_priority = [x for x in entries_work if x['filename'] in ['data/mp3/mp3_tab.bin', 'data/mdb/mdb.bin'] or x['filename'].startswith("boot/") or x['filename'].startswith("soft/")]
    entries_work = entries_work_priority + [x for x in entries_work if x not in entries_work_priority]

    data_hashes = {}
    used_addresses = []
    cur_memory = 0

    # Certain files need to be at specific offsets or else they won't work properly (seemingly, maybe it's a bug with my code somewhere)
    # so put any "important" files where they should be for the most part
    for entry in entries_work[::]:
        if not entry.get('_modified', False):
            continue

        if not entry['filename'].startswith('boot/') and not entry['filename'].startswith('soft/') and not entry['filename'].startswith('data/fpga/'):
            continue

        if 'offset' in entry:
            cur_memory = entry['offset']

            data = get_data_from_entry(entry)

            if entry.get('flag_comp', 0) == 1:
                data = comp573.encode_lz(data, len(data))

            if entry.get('flag_enc', 0) == 1:
                data = encrypt_data(data, enc_key)

            entry['filesize'] = len(data)

            datahash = hashlib.sha1(data).hexdigest()
            data_hashes[datahash] = {
                'offset': cur_memory,
                'filesize': entry['filesize'],
                'loc': entry.get('flag_loc', 0),
            }

            if len(data) > entry['filesize']:
                print("Filesize is too large: %08x vs %08x" % (len(data), entry['filesize']))

            elif len(data) < entry['filesize']:
                entry['filesize'] = len(data)

                # Pad with 0xff
                data += b'\xff' * (entry['filesize'] - len(data))

            size = entry['filesize']
            padding = 0
            if (size % 0x800) != 0:
                padding = 0x800 - (size % 0x800)

            else:
                padding = 0x800

            size += padding

            memory[entry.get('flag_loc', 0)][cur_memory + entry['filesize']:cur_memory + entry['filesize'] + padding] = bytearray([0xff] * padding)
            memory[entry.get('flag_loc', 0)][cur_memory:cur_memory + entry['filesize']] = data
            memory_map[entry.get('flag_loc', 0)][cur_memory:cur_memory + entry['filesize']] = [1] * size

            entries_work.remove(entry)
            used_addresses.append((entry.get('flag_loc', 0), cur_memory))

    # For everything else, just try to find a fitting space in the available areas
    entries_len = len(entries_work[::])
    for entry_idx, entry in enumerate(entries_work[::]):
        if not entry.get('_modified', False):
            continue

        data = get_data_from_entry(entry)
        orig_len = len(data)

        if entry.get('flag_comp', 0) == 1:
            data = comp573.encode_lz(data, len(data))

        if entry.get('flag_enc', 0) == 1:
            data = encrypt_data(data, enc_key)

        datahash = hashlib.sha1(data).hexdigest()

        size = len(data)
        padding = 0
        if (size % 0x800) != 0:
            padding = 0x800 - (size % 0x800)

        else:
            padding = 0x800

        is_dupe = False
        if datahash in data_hashes:
            cur_memory = data_hashes[datahash]['offset']
            loc = data_hashes[datahash]['loc']
            is_dupe = True

        else:
            # This code is not optimized. It sucks but it works.
            # The general idea I was trying to implement is to find the first
            # string of 0s in the memory map that could fit the size of the data
            # padded to the nearest sector (0x800).
            # The padding is key because if you can't clear out the sector properly
            # then the game has a higher chance of crashing for some reason.
            # Possibly due to decompression reading in garbage data as compressed data.
            for loc in range(0, len(memory_map)):
                loc = entry.get('flag_loc', 1)

                cur_memory = 0

                while cur_memory < len(memory_map[loc]):
                    if (cur_memory % 0x800) != 0:
                        cur_memory += (0x800 - (cur_memory % 0x800))

                    idx = memory_map[loc].find(0, cur_memory)

                    if idx == -1:
                        cur_memory = -1
                        break

                    if (idx % 0x800) != 0:
                        cur_memory = idx + 1
                        continue

                    cur_memory = idx
                    idx = memory_map[loc].find(1, cur_memory, cur_memory + len(data) + padding)

                    if idx != -1:
                        cur_memory = idx

                        if (idx % 0x800) != 0:
                            cur_memory += 0x800 - (idx % 0x800)

                        continue

                    else:
                        break

                    if cur_memory > len(memory_map[loc]):
                        cur_memory = -1
                        break

                if cur_memory > len(memory_map[loc]):
                    cur_memory = - 1
                    continue

                if loc == 0 and cur_memory + len(data) + padding >= base_offset:
                    continue

                if cur_memory > 0:
                    break

            if cur_memory == -1 or (loc == 0 and cur_memory + len(data) + padding >= base_offset):
                print("Couldn't find position for %08x" % len(data), entry)
                exit(1)


        print("%d / %d: Placing %08x @ %08x in card %d for %s" % (entry_idx, entries_len, len(data), cur_memory, loc, entry['filename']))

        if not is_dupe and (loc, cur_memory) in used_addresses:
            print("Can't reuse address!")
            exit(1)

        size += padding
        memory[loc][cur_memory:cur_memory + len(data)] = data
        memory[loc][cur_memory + len(data):cur_memory + len(data) + padding] = bytearray([0xff] * padding)
        memory_map[loc][cur_memory:cur_memory + len(data) + padding] = [1] * size

        entry['filesize'] = len(data)
        used_addresses.append((loc, cur_memory))

        data_hashes[datahash] = {
            'offset': cur_memory,
            'filesize': entry['filesize'],
            'loc': loc,
        }

        # Update master entries for the file table lazily
        for e in entries:
            if e == entry:
                e['offset'] = cur_memory

        entries_work.remove(entry)

    entries = sorted(entries, key=lambda x: x['filename_hash'])

    for idx, entry in enumerate(entries):
        print("%08x" % entry['filename_hash'], entry)
        memory[0][base_offset + 0x4000 + (idx * 0x10):base_offset + 0x4000 + ((idx + 1) * 0x10)] = struct.pack("<IHHBBHI", entry['filename_hash'], entry['offset'] // 0x800, entry.get('flag_loc', 0), entry.get('flag_comp', 0), entry.get('flag_enc', 0), entry.get('unk', 0), entry['filesize'])

    idx = len(entries)
    memory[0][base_offset + 0x4000 + (idx * 0x10):base_offset + 0x4000 + ((idx + 1) * 0x10)] = struct.pack("<IIII", 0, 0, 0, 0)

    return memory


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--input', help='Input folder', default=None, required=True)
    parser.add_argument('--input-modified-list', help='Input modified list', default=None)
    parser.add_argument('--base', help='Base file folder', default=None, required=True)
    parser.add_argument('--output', help='Output file', default="output")
    parser.add_argument('--key', help='Encryption key', choices=['EXTREME', 'EURO2', 'MAX2', 'DDR5', 'MAMBO'], required=True)
    parser.add_argument('--override-edit-section', help='Allows use of end of CARD 2 which would otherwise be used for edit data saved to flash card. REQUIRED ENABLE_EDIT_SECTOR_OVERRIDE ENABLED IN ASM PATCHES!', default=False, action='store_true')
    parser.add_argument('--patch-dir', help='Path to use for patch files', default="")

    args, _ = parser.parse_known_args()

    os.makedirs(args.output, exist_ok=True)

    # Settings are specific to DDR Extreme for now
    basefileinfo = [("GAME.DAT", 16), ("CARD.DAT", 32)]
    base_offset = 0xFE0000
    filetable = get_filetable(args.input, args.input_modified_list, args.patch_dir)

    card_datas = create_gamedata(filetable, base_offset, [bytearray(open(os.path.join(args.base, info[0]), "rb").read()) for info in basefileinfo], args.key, args.override_edit_section)
    card_datas = [bytearray(data)[:basefileinfo[i][1] * 1024 * 1024] for i, data in enumerate(card_datas)]

    rebuild_checksum_table(card_datas)

    for i, data in enumerate(card_datas):
        open(os.path.join(args.output, basefileinfo[i][0]), "wb").write(data)


if __name__ == "__main__":
    main()
