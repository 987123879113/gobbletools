import argparse
import ctypes
import json
import os
import pickle
import string

import enc573
from comp573 import decode_lz, decode_lz0


hash_list = {}
used_hash_list = {}
unknown_hash_list = {}


def get_filename_hash(filename):
    return enc573.get_filename_hash(filename.encode('shift-jis'), len(filename))


def decrypt_data_internal(data, key):
    def calculate_crc32(input):
        crc = -1

        for c in bytearray(input, encoding='ascii'):
            crc ^= c << 24

            for _ in range(8):
                if crc & 0x80000000:
                    crc = (crc << 1) ^ 0x4C11DB7
                else:
                    crc <<= 1

        return crc


    decryption_key = calculate_crc32(key)

    for i in range(len(data)):
        data[i] ^= (decryption_key >> 8) & 0xff # This 8 can be variable it seems, but it usually is 8?

    return data


def decrypt_data(data, input_key):
    def calculate_key(input_str):
        key = 0

        for cur in input_str.upper():
            if cur in string.ascii_uppercase:
                key -= 0x37

            elif cur in string.ascii_lowercase:
                key -= 0x57

            elif cur in string.digits:
                key -= 0x30

            key += ord(cur)

        return key & 0xff

    val = 0x41C64E6D
    key1 = (val * calculate_key(input_key)) & 0xffffffff
    counter = 0

    for idx, c in enumerate(data):
        val = ((key1 + counter) >> 5) ^ c
        data[idx] = val & 0xff
        counter += 0x3039

    return data


common_extensions = [
    'bin', 'exe', 'dat', 'rom', 'o'
]

mambo_common_extensions = [
    'bin.new', 'cmp', 'vas', 'olb', 'pup', 'cpr'
]

ddr_common_extensions = [
    'cmt', 'tim', 'cms', 'lmp', 'per', 'csq', 'ssq', 'cmm',
    'pos', 'ctx', 'lst', 'tmd', 'vab', 'sbs', 'can', 'anm',
    'lpe', 'mbk', 'lz', 'bs', 'txt', 'tan', 'cmd'
]

gfdm_common_extensions = [
    'pak', 'fcn', 'vas', 'sq2', 'sq3', 'gsq', 'dsq', 'bin', 'dat'
]

dmx_common_extensions = [
    'tex', 'lst', 'mdt', 'nmd', 'lmp', 'tng', 'bke', 'lz', 'seq'
]

common_extensions += mambo_common_extensions + ddr_common_extensions + gfdm_common_extensions + dmx_common_extensions

ddr_common_regions = [
    'span', 'ital', 'germ', 'fren', 'engl', 'japa', 'kore'
]

ddr_common_parts = [
    'cd', 'nm', 'in', 'ta', 'th', 'bk', 'fr', '25'
]


def generate_ddr_song_paths(songlist=[], hash_list={}):
    for song_id in songlist:
        for ext in common_extensions:
            for part in ddr_common_parts:
                filename = "data/mdb/%s/%s_%s.%s" % (song_id, song_id, part, ext)
                hash_list[get_filename_hash(filename)] = filename

            filename = "data/mdb/%s/all.%s" % (song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "data/mdb/%s/%s.%s" % (song_id, song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "data/ja/music/%s/%s.%s" % (song_id, song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "ja/music/%s/%s.%s" % (song_id, song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "music/%s/%s.%s" % (song_id, song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "%s/%s.%s" % (song_id, song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "%s.%s" % (song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "mus_%s.%s" % (song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "mus_%s/mus_%s.%s" % (song_id, song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "%s_rec.%s" % (song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            filename = "rec/%s_rec.%s" % (song_id, ext)
            hash_list[get_filename_hash(filename)] = filename

            for a in 'sdab':
                for b in 'sdab':
                    filename = "%s_%c%c.%s" % (song_id, a, b, ext)
                    hash_list[get_filename_hash(filename)] = filename

    return hash_list


# Functions used to parse DDR data
def parse_rembind_filenames(data, hash_list={}):
    entries = len(data) // 0x30

    for i in range(entries):
        filename_len = 0

        while filename_len + 0x10 < 0x30 and data[i*0x30+0x10+filename_len] != 0:
            filename_len += 1

        orig_filename = data[i*0x30+0x10:i*0x30+0x10+filename_len].decode('ascii').strip('\0')
        hash_list[get_filename_hash(orig_filename)] = orig_filename

        langs = ["japa", "span", "ital", "germ", "fren", "engl"]
        for lang in langs:
            lang = "/" + lang + "/"

            for lang2 in langs:
                lang2 = "/" + lang2 + "/"

                if lang in orig_filename:
                    f = orig_filename.replace(lang, lang2)
                    hash_list[get_filename_hash(f)] = f

        for ext in common_extensions:
            filename = "data/%s.%s" % (orig_filename, ext)
            hash_list[get_filename_hash(filename)] = filename

            for region in ddr_common_regions:
                for region2 in ddr_common_regions:
                    if region2 == region:
                        continue

                    needle = "%s/" % region

                    if needle not in orig_filename:
                        continue

                    filename = "data/%s.%s" % (orig_filename, ext)
                    filename = filename.replace(needle, "%s/" % region2)
                    hash_list[get_filename_hash(filename)] = filename

    return hash_list


# Functions used to parse GFDM data
def parse_group_list_filenames(data, hash_list={}):
    for i in range(len(data) // 0x30):
        filename_len = 0

        while filename_len < 0x30 and data[i*0x30+filename_len] != 0:
            filename_len += 1

        filename = data[i*0x30:i*0x30+filename_len].decode('ascii').strip('\0')

        for ext in common_extensions:
            path = "%s.%s" % (filename, ext)
            hash_list[get_filename_hash(path)] = path

        filename = os.path.splitext(filename)[0]
        for ext in common_extensions:
            path = "%s.%s" % (filename, ext)
            hash_list[get_filename_hash(path)] = path

    return hash_list


# Functions used to parse Dancemaniax data
def parse_group_list_filenames_dmx(data, hash_list={}, skip_data=False):
    entry_size = 0x20
    cnt = int.from_bytes(data[:4], byteorder="little")

    if skip_data:
        data = data[0x10:]

    for i in range(cnt):
        filename_len = 0

        while filename_len < entry_size and data[i*entry_size+filename_len] != 0:
            filename_len += 1

        filename = data[i*entry_size:i*entry_size+filename_len].decode('ascii').strip('\0')

        hash_list[get_filename_hash(filename)] = filename

        for ext in common_extensions:
            path = "%s.%s" % (filename, ext)
            hash_list[get_filename_hash(path)] = path

        for ext in common_extensions:
            path = "tex_group_%s.%s" % (filename, ext)
            hash_list[get_filename_hash(path)] = path

        filename = os.path.splitext(filename)[0]
        for ext in common_extensions:
            path = "%s.%s" % (filename, ext)
            hash_list[get_filename_hash(path)] = path

    if skip_data:
        data = data[0x20*cnt:]
    else:
        data = data[0x10+0x20*cnt:]

    entry_size = 0x30
    for i in range(len(data) // entry_size):
        filename_len = 0

        while filename_len < entry_size and data[i*entry_size+filename_len] != 0:
            filename_len += 1

        filename = data[i*entry_size:i*entry_size+filename_len].decode('ascii').strip('\0')
        hash_list[get_filename_hash(filename)] = filename

        for ext in common_extensions:
            path = "%s.%s" % (filename, ext)
            hash_list[get_filename_hash(path)] = path

        filename = os.path.splitext(filename)[0]
        for ext in common_extensions:
            path = "%s.%s" % (filename, ext)
            hash_list[get_filename_hash(path)] = path

    return hash_list


# Common readers
def parse_mdb_filenames(data, entry_size, hash_list={}, return_raw=False):
    songlist = []

    try:
        for i in range(len(data) // entry_size):
            if data[i*entry_size] == 0:
                break

            songlist.append(data[i*entry_size:i*entry_size+6].decode('ascii').strip('\0').strip())

    except:
        pass

    if return_raw:
        return songlist

    return generate_ddr_song_paths(songlist, hash_list)


# File table readers
def parse_db_filenames(data, hash_list={}, return_raw=False):
    entry_size = 0x80

    try:
        for i in range(len(data) // entry_size):
            filename = data[i*entry_size+0x5c:i*entry_size+0x7c].decode('ascii').strip('\0').strip()
            hash_list[get_filename_hash(filename)] = filename
            print(filename)

            filename = filename.replace(".bin", ".cmt")
            hash_list[get_filename_hash(filename)] = filename

            filename = "%s/%s" % (os.path.splitext(os.path.basename(filename))[0], filename)
            hash_list[get_filename_hash(filename)] = filename

    except:
        pass

    return hash_list


def read_file_table_ddr(filename, table_offset, forced_secondary=False):
    files = []

    with open(filename, "rb") as infile:
        infile.seek(0, 2)
        dat_size = infile.tell()

        infile.seek(table_offset, 0)

        while True:
            filename_hash = int.from_bytes(infile.read(4), byteorder="little")
            offset = int.from_bytes(infile.read(2), byteorder="little")
            flag_loc = int.from_bytes(infile.read(2), byteorder="little")
            flag_comp = int.from_bytes(infile.read(1), byteorder="little")
            flag_enc = int.from_bytes(infile.read(1), byteorder="little")
            unk = int.from_bytes(infile.read(2), byteorder="little")
            filesize = int.from_bytes(infile.read(4), byteorder="little")

            if filename_hash == 0xffffffff and offset == 0xffff:
                break

            if filename_hash == 0 and offset == 0 and filesize == 0:
                break

            assert(flag_loc >= 0 and flag_loc <= 1)
            assert(flag_comp >= 0 and flag_comp <= 2)
            assert(flag_enc >= 0 and flag_enc <= 1)
            assert(offset < dat_size)
            assert(filesize < dat_size)

            files.append({
                'idx': len(files),
                'filename_hash': filename_hash,
                'offset': offset,
                'filesize': filesize,
                'flag_loc': flag_loc,
                'flag_comp': flag_comp,
                'flag_enc': flag_enc,
                'unk': unk,
            })

    # Verify offsets to make sure this isn't actually a gfdm2 table
    is_ddr = True
    for idx, fileinfo in enumerate(files):
        if fileinfo['offset'] >= 0x8000:
            is_ddr = False
            break

    assert(is_ddr == True)

    for idx in range(len(files)):
        files[idx]['offset'] *= 0x800

    return files


def read_file_table_gfdm4(filename, table_offset, forced_secondary=False, is_gfdm=False):
    return read_file_table_ddr_dancingstage(filename, table_offset, forced_secondary, True)


def read_file_table_ddr_dancingstage(filename, table_offset, forced_secondary=False, is_gfdm=False):
    global hash_list

    files = []
    offset_diff = 0x1f000000 - 0x400000
    offset_data_diff = 0

    with open(filename, "rb") as infile:
        # Check if this has the extra header or not
        infile.seek(0, 0)
        header_check = infile.read(0x20)
        infile.seek(0x100, 0)

        for _ in range(8):
            header_check += infile.read(2)[::-1]

        infile.seek(-0x30, 2)
        header_check_bottom = infile.read(0x30)

        if header_check == header_check_bottom:
            offset_data_diff = 0x800

        infile.seek(table_offset, 0)

        next_offset = table_offset + offset_data_diff
        while True:
            infile.seek(next_offset)
            next_offset = infile.tell() + 0x100

            flag = int.from_bytes(infile.read(2), 'little')

            assert(flag in [0, 4, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e] or (flag & 0xff) == 1)

            if flag in [4, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e]:
                # Start of file table chunk
                continue

            elif flag == 0:
                # Reposition in file to next part of table
                m = int.from_bytes(infile.read(2), 'little')

                if m == 0:
                    break

                offset_diff = 0x1f000000 - (0x400000 * m)
                next_offset = int.from_bytes(infile.read(4), 'little') - offset_diff + offset_data_diff
                continue

            infile.seek(-1, 1)
            filename_bytes = []

            filename = bytearray(infile.read(0xf5)).decode('ascii').strip('\0')
            filename_hash = get_filename_hash(filename)
            hash_list[filename_hash] = filename

            m = int.from_bytes(infile.read(2), 'little')
            offset_diff = 0x1f000000 - (0x400000 * m)
            offset = int.from_bytes(infile.read(4), 'little')
            filesize = int.from_bytes(infile.read(4), 'little')

            files.append({
                'idx': len(files),
                'filename': filename,
                'filename_hash': filename_hash,
                'offset': offset - offset_diff + offset_data_diff,
                'filesize': filesize,
                'flag_loc': 0,
                'flag_comp': 1 if is_gfdm else 0,
                'flag_enc': 0,
                'unk': 0,
                '_is_dancingstage': True,
                '_data_offset': offset_data_diff,
                '_main_card_filename': os.path.basename(filename),
            })

    return files


def read_file_table_gfdm(filename, table_offset, forced_secondary=False):
    files = []

    with open(filename, "rb") as infile:
        infile.seek(table_offset, 0)

        while True:
            filename_hash = int.from_bytes(infile.read(4), byteorder="little")
            offset = int.from_bytes(infile.read(4), byteorder="little")
            filesize = int.from_bytes(infile.read(4), byteorder="little")
            flag = int.from_bytes(infile.read(4), byteorder="little")

            if filename_hash == 0 and offset == 0 and filesize == 0 and flag == 0:
                break

            if filename_hash == 0xffffffff and offset == 0xffffffff:
                break

            assert(flag <= 0x0f)

            files.append({
                'idx': len(files),
                'filename_hash': filename_hash,
                'offset': offset,
                'filesize': filesize,
                'flag_loc': 0 if not forced_secondary else 1,
                'flag_comp': 0,
                'flag_enc': 0,
                'unk': 0,
                '_flag': flag,
                '_main_card_filename': os.path.basename(filename),
            })

    return files


def read_file_table_gfdm2(filename, table_offset, forced_secondary=False):
    files = []

    with open(filename, "rb") as infile:
        infile.seek(table_offset, 0)

        while True:
            filename_hash = int.from_bytes(infile.read(4), byteorder="little")
            offset = int.from_bytes(infile.read(4), byteorder="little")
            flag = int.from_bytes(infile.read(4), byteorder="little")
            filesize = int.from_bytes(infile.read(4), byteorder="little")

            assert(flag == 0)

            if filename_hash == 0 and offset == 0 and filesize == 0 and flag == 0:
                break

            if filename_hash in [0, 0xffffffff] and offset in [0, 0xffffffff]:
                break

            files.append({
                'idx': len(files),
                'filename_hash': filename_hash,
                'offset': (offset << 11) & 0x3fffff if offset >= 0x8000 else offset * 0x800,
                'filesize': filesize,
                'flag_loc': 1 if offset >= 0x8000 or forced_secondary else 0,
                'flag_comp': 1,
                'flag_enc': 0,
                'unk': 0,
                '_flag': flag,
                '_main_card_filename': os.path.basename(filename),
            })

    return files


def read_file_table_gfdm3(card_filename, table_offset, forced_secondary=False):
    global hash_list

    files = []

    with open(card_filename, "rb") as infile:
        filetable_offsets = [table_offset]
        used_filetable_offsets = []
        read_offsets = []

        while filetable_offsets:
            table_offset = filetable_offsets.pop()
            used_filetable_offsets.append(table_offset)
            infile.seek(table_offset, 0)

            while True:
                if infile.tell() in read_offsets:
                    # Skip to avoid loops
                    infile.seek(0x40, 1)
                    continue

                read_offsets.append(infile.tell())

                flag = int.from_bytes(infile.read(1), 'little')

                if flag in [0, 0xff]:
                    break

                assert(flag in [0, 1, 2])

                if flag == 2:
                    # This is a pointer to another part of the file table
                    # Store the address and come back to it later
                    infile.seek(3, 1)
                    offset = int.from_bytes(infile.read(4), 'little') * 0x800
                    infile.seek(0x38, 1)

                    if offset not in filetable_offsets and offset not in used_filetable_offsets:
                        filetable_offsets.append(offset)
                        print("Found pointer! %08x" % offset)

                    continue

                filename_bytes = []
                bytes_left = 0x33
                while True:
                    filename_bytes += infile.read(1)
                    bytes_left -= 1

                    if filename_bytes[-1] == 0:
                        break

                infile.seek(bytes_left, 1)

                filename = bytearray(filename_bytes).decode('ascii').strip('\0')

                for c in filename:
                    assert(c in string.printable)

                filename_hash = get_filename_hash(filename)
                hash_list[filename_hash] = filename

                flag2 = int.from_bytes(infile.read(1), 'little')
                unk = infile.read(0x03)

                offset = int.from_bytes(infile.read(4), 'little')
                filesize = int.from_bytes(infile.read(4), 'little')

                files.append({
                    'idx': len(files),
                    'filename': filename,
                    'filename_hash': filename_hash,
                    'offset': (offset * 0x800) + (0x800 if flag2 == 2 else 0),
                    'filesize': filesize,
                    'flag_loc': 1 if offset >= 0x8000 or forced_secondary else 0,
                    'flag_comp': 1,
                    'flag_enc': 0,
                    'unk': 0,
                    '_flag': flag,
                    '_flag2': flag2,
                    '_main_card_filename': os.path.basename(card_filename),
                })

    return files


def get_card_filenames(input_folder, main_card_filename=None):
    game_filename = None
    card_filename = None

    if main_card_filename is not None and os.path.exists(os.path.join(input_folder, main_card_filename)):
        game_filename = os.path.join(input_folder, main_card_filename)

    else:
        card_filenames = [
            "GAME.DAT",
            "GC845.DAT",
            "GQ883JA.DAT",
            "GE929JA.DAT",
            "GC910JC.BIN",
            "GC910JA.BIN",
            "GN884JA.BIN",
            "GQ881JAD.DAT",
            "GQ881B.DAT",
            "GN845EAA.DAT",
            "GN845UAA.DAT",
            "GN845AAA.DAT",
            "GN895JAA.DAT",
            "GE885JAA.DAT",
            "GC845EBA.DAT",
            "GQ894JAA.DAT",
            "GQ886AA.DAT",
            "GQ886EA.DAT",
            "GQ886JA.DAT",
            "GQ886UA.DAT",
        ]
        for filename in card_filenames:
            game_path = os.path.join(input_folder, filename)

            if os.path.exists(game_path):
                game_filename = game_path
                break

    card_filenames = ["PCCARD.DAT", "PCCARD1.DAT", "CARD.DAT", "CARD1.DAT", "GQ883CAR.DAT", "GE929CAR.DAT"]
    for filename in card_filenames:
        pccard_path = os.path.join(input_folder, filename)

        if os.path.exists(pccard_path):
            card_filename = pccard_path
            break

    return game_filename, card_filename


def get_file_from_dancingstage(reader, fileinfo):
    data = bytearray()

    reader.seek(fileinfo['offset'], 0)
    cur_offset = reader.tell()

    while len(data) < fileinfo['filesize']:
        cur_offset = reader.tell()

        data += reader.read(0xf00)

        flag = int.from_bytes(reader.read(2), 'little')
        m = int.from_bytes(reader.read(2), 'little')
        offset = int.from_bytes(reader.read(4), 'little')

        offset_diff = 0x1f000000 - (0x400000 * m)
        reader.seek(offset - offset_diff + fileinfo.get('_data_offset', 0), 0)

        if reader.tell() == cur_offset:
            data += reader.read(0xf00)
            break

    data = data[:fileinfo['filesize']]

    if len(data) != fileinfo['filesize']:
        print("Filesizes don't match!", fileinfo['filename'])

    return data


def get_file_data(input_folder, fileinfo, enckey=None):
    game_filename, card_filename = get_card_filenames(input_folder, fileinfo.get('_main_card_filename', None))

    game = open(game_filename, "rb") if game_filename else None
    card = open(card_filename, "rb") if card_filename else None

    data = None
    if fileinfo['flag_loc'] == 1:
        if card:
            card.seek(fileinfo['offset'])

            if fileinfo.get('_is_dancingstage', False):
                data = get_file_from_dancingstage(card, fileinfo)

            else:
                data = bytearray(card.read(fileinfo['filesize']))

    else:
        if game:
            game.seek(fileinfo['offset'])

            if fileinfo.get('_is_dancingstage', False):
                data = get_file_from_dancingstage(game, fileinfo)

            else:
                data = bytearray(game.read(fileinfo['filesize']))

    if data and fileinfo['flag_enc'] != 0 and enckey:
        data = decrypt_data(data, enckey)

    if data and fileinfo['flag_comp'] == 1:
        try:
            data = decode_lz(data, len(data))

        except IndexError:
            pass

    return bytearray(data)


def dump_data(input_folder, output_folder, candidate_result, main_card_filename=None):
    global hash_list
    global used_hash_list
    global unknown_hash_list

    files = candidate_result[1]

    game_filename, card_filename = get_card_filenames(input_folder, main_card_filename)

    used_regions = {}

    if game_filename:
        used_regions[0] = {
            0: {
                'filename': game_filename,
                'data': [0] * os.path.getsize(game_filename),
            },
        }

    if card_filename:
        used_regions[1] = {
            'filename': card_filename,
            'data': [0] * os.path.getsize(card_filename),
        }

        # Try to parse secondary card
        has_secondary_files = False
        for f in files:
            if f['flag_loc'] != 0:
                has_secondary_files = True
                break

        if not has_secondary_files and candidate_result[0][0] not in [read_file_table_ddr]:
            for offset in [0, 0x766000, 0xf72800]:
                try:
                    new_files = candidate_result[0][0](card_filename, offset, True)
                    files += new_files
                except:
                    pass

    game_key = None
    has_enc_files = False

    for f in files:
        if f['flag_enc'] != 0:
            has_enc_files = True

            if f['filename_hash'] in hash_list:
                if hash_list[f['filename_hash']] == "data/mdb/mdb.bin":
                    candidate_key_count = 0

                    for cur_key in ['EXTREME', 'EURO2', 'MAX2', 'DDR5', 'MAMBO']:
                        mdb1 = parse_mdb_filenames(get_file_data(input_folder, f, cur_key), 0x2c, [], True)
                        mdb2 = parse_mdb_filenames(get_file_data(input_folder, f, cur_key), 0x30, [], True)
                        mdb3 = parse_mdb_filenames(get_file_data(input_folder, f, cur_key), 0x64, [], True)
                        mdb4 = parse_mdb_filenames(get_file_data(input_folder, f, cur_key), 0x6c, [], True)
                        mdb5 = parse_mdb_filenames(get_file_data(input_folder, f, cur_key), 0x80, [], True)

                        for mdb in [mdb1, mdb2, mdb3, mdb4, mdb5]:
                            if len(mdb) > candidate_key_count:
                                candidate_key_count = len(mdb)
                                game_key = cur_key

    if has_enc_files and game_key is None:
        print("Requires game key!", has_enc_files)
        exit(1)

    for idx, fileinfo in enumerate(files):
        if fileinfo['filename_hash'] == 0x45fda52a or (fileinfo['filename_hash'] in hash_list and hash_list[fileinfo['filename_hash']].endswith("config.dat")): # Just try to decrypt any config.dat
            try:
                config = decrypt_data_internal(get_file_data(input_folder, fileinfo, game_key), "/s573/config.dat")
                open(os.path.join(output_folder, "_config.txt"), "wb").write(config)

                config = config.decode('shift-jis')

                print("Configuration file decrypted:")
                print(config)

                for l in config.split('\n'):
                    if l.startswith("conversion "):
                        # Dumb way of doing this but I'm lazy
                        for path in l[len("conversion "):].split(':'):
                            if path.startswith('/'):
                                path = path[1:]

                            hash_list[get_filename_hash(path)] = path

            except:
                pass

        if fileinfo['filename_hash'] in hash_list:
            if hash_list[fileinfo['filename_hash']] in ["data/tex/rembind.bin", "data/all/texbind.bin"]:
                hash_list = parse_rembind_filenames(get_file_data(input_folder, fileinfo, game_key), hash_list)

            if hash_list[fileinfo['filename_hash']] == "data/mdb/mdb.bin":
                hash_list = parse_mdb_filenames(get_file_data(input_folder, fileinfo, game_key), 0x2c, hash_list)
                hash_list = parse_mdb_filenames(get_file_data(input_folder, fileinfo, game_key), 0x30, hash_list)
                hash_list = parse_mdb_filenames(get_file_data(input_folder, fileinfo, game_key), 0x64, hash_list)
                hash_list = parse_mdb_filenames(get_file_data(input_folder, fileinfo, game_key), 0x6c, hash_list)
                hash_list = parse_mdb_filenames(get_file_data(input_folder, fileinfo, game_key), 0x80, hash_list)

            if hash_list[fileinfo['filename_hash']] == "data/music/cd1.db":
                hash_list = parse_db_filenames(get_file_data(input_folder, fileinfo, game_key), hash_list)

            if hash_list[fileinfo['filename_hash']] in ["data/mdb/ja_mdb.bin", "data/mdb/ka_mdb.bin",
                                                            "data/mdb/aa_mdb.bin", "data/mdb/ea_mdb.bin",
                                                            "data/mdb/ua_mdb.bin"]:
                hash_list = parse_mdb_filenames(get_file_data(input_folder, fileinfo, game_key), 0x38, hash_list)
                hash_list = parse_mdb_filenames(get_file_data(input_folder, fileinfo, game_key), 0x6c, hash_list)

            if hash_list[fileinfo['filename_hash']] == "group_list.bin":
                hash_list = parse_group_list_filenames(get_file_data(input_folder, fileinfo, game_key), hash_list)

            if hash_list[fileinfo['filename_hash']] == "ja_mdb.bin":
                hash_list = parse_mdb_filenames(get_file_data(input_folder, fileinfo, game_key)[0x10:], 0x24, hash_list)
                hash_list = parse_mdb_filenames(get_file_data(input_folder, fileinfo, game_key), 0x38, hash_list)

            elif hash_list[fileinfo['filename_hash']] == "arrangement_data.bin":
                try:
                    hash_list = parse_group_list_filenames_dmx(get_file_data(input_folder, fileinfo, game_key), hash_list)
                except:
                    pass

                try:
                    hash_list = parse_group_list_filenames_dmx(get_file_data(input_folder, fileinfo, game_key), hash_list, True)
                except:
                    pass

    unknown_hash_list = {}
    for idx, fileinfo in enumerate(files):
        output_filename = "_output_%08x.bin" % (fileinfo['filename_hash'])

        if fileinfo['filename_hash'] in hash_list:
            output_filename = hash_list[fileinfo['filename_hash']]
            used_hash_list[fileinfo['filename_hash']] = output_filename

            if output_filename.startswith("/"):
                output_filename = "_" + output_filename[1:]

            while output_filename.startswith("../"):
                output_filename = output_filename[3:]

        else:
            print("Unknown hash %08x" % fileinfo['filename_hash'], output_filename)
            unknown_hash_list[fileinfo['filename_hash']] = input_folder

        files[idx]['filename'] = output_filename

        output_filename = os.path.join(output_folder, output_filename)

        # Mark region as used
        region_size = fileinfo['offset'] + fileinfo['filesize']

        # if (region_size % 0x800) != 0:
        #     region_size += 0x800 - (region_size % 0x800)

        # used_regions[fileinfo['flag_loc']]['data'][fileinfo['offset']:region_size] = [1] * (region_size - fileinfo['offset'])

        if os.path.exists(output_filename):
            continue

        filepath = os.path.dirname(output_filename)
        if not os.path.exists(filepath):
            os.makedirs(filepath)

        print(fileinfo)
        print("Extracting", output_filename)

        data = get_file_data(input_folder, fileinfo, game_key)

        try:
            if output_filename.endswith(".lz"):
                if files[idx]['flag_comp'] == 0:
                    data = decode_lz(data, len(data))
                output_filename = output_filename[:-len(".lz")] + ".tim"

            elif output_filename.endswith(".lz0"):
                if files[idx]['flag_comp'] == 0:
                    data = decode_lz0(data, len(data))
                output_filename = output_filename[:-len(".lz0")] + ".tim"
        except:
            pass

        with open(output_filename, "wb") as outfile:
            outfile.write(data)

    json.dump({'files': files}, open(os.path.join(output_folder, "_metadata.json"), "w"), indent=4)

    # unreferenced_path = os.path.join(output_folder, "#unreferenced")
    # for k in used_regions:
    #     data = bytearray(open(os.path.join(input_folder, used_regions[k]['filename']), "rb").read())

    #     # Find and dump unreferenced regions with data in them
    #     start = 0
    #     while start < len(used_regions[k]['data']):
    #         if used_regions[k]['data'][start] == 0:
    #             end = start

    #             while end < len(used_regions[k]['data']) and used_regions[k]['data'][end] == 0:
    #                 end += 1

    #             if len([x for x in data[start:end] if x != 0]) > 0 and len([x for x in data[start:end] if x != 0xff]) > 0:
    #                 if not os.path.exists(unreferenced_path):
    #                     os.makedirs(unreferenced_path)

    #                 print("Found unreferenced data @ %08x - %08x" % (start, end))

    #                 open(os.path.join(unreferenced_path, "%d_%08x.bin" % (k, start)), "wb").write(data[start:end])

    #             start = end + 1

    #         else:
    #             start += 1


def main():
    global hash_list
    global used_hash_list
    global unknown_hash_list

    parser = argparse.ArgumentParser()

    parser.add_argument('--input', help='Input folder', default=None, required=True)
    parser.add_argument('--output', help='Output folder', default="output")

    args, _ = parser.parse_known_args()

    hash_list = {}
    used_hash_list = {}
    unknown_hash_list = {}

    if os.path.exists("hash_list.pkl"):
        hash_list = pickle.load(open("hash_list.pkl", "rb"))
        used_hash_list = pickle.load(open("hash_list.pkl", "rb"))

    else:
        pass

    filenames = []

    for filename in filenames:
        hash_list[get_filename_hash(filename)] = filename

    # Try to determine card type via heuristics
    filetables = []
    filetables.append((read_file_table_ddr, 0xfe4000, os.path.join(args.input, "GAME.DAT"), 1))
    filetables.append((read_file_table_ddr, 0x100000, os.path.join(args.input, "GC845.DAT"), 1))
    filetables.append((read_file_table_ddr, 0x100000, os.path.join(args.input, "GN845UAA.DAT"), 2))
    filetables.append((read_file_table_ddr, 0x100000, os.path.join(args.input, "GN845EAA.DAT"), 2))
    filetables.append((read_file_table_ddr, 0x100000, os.path.join(args.input, "GN845AAA.DAT"), 2))
    filetables.append((read_file_table_ddr, 0x100000, os.path.join(args.input, "GN895JAA.DAT"), 2))
    filetables.append((read_file_table_ddr, 0x100000, os.path.join(args.input, "GE885JAA.DAT"), 2))
    filetables.append((read_file_table_ddr, 0x100000, os.path.join(args.input, "GC845EBA.DAT"), 2))
    filetables.append((read_file_table_ddr, 0x100000, os.path.join(args.input, "GQ894JAA.DAT"), 2))
    filetables.append((read_file_table_ddr_dancingstage, 0x401000, os.path.join(args.input, "GAME.DAT"), 2))
    filetables.append((read_file_table_ddr_dancingstage, 0x401000, os.path.join(args.input, "GC910JC.BIN"), 2)) # Dancing Stage
    filetables.append((read_file_table_ddr_dancingstage, 0x401000, os.path.join(args.input, "GC910JA.BIN"), 2)) # Dancing Stage
    filetables.append((read_file_table_ddr_dancingstage, 0x401000, os.path.join(args.input, "GN884JA.BIN"), 2)) # Dancing Stage

    filetables.append((read_file_table_gfdm4, 0x401000, os.path.join(args.input, "GQ881JAD.DAT"), 2)) # Drummania 1st
    filetables.append((read_file_table_gfdm4, 0x401000, os.path.join(args.input, "GQ881B.DAT"), 2)) # Drummania 1st
    filetables.append((read_file_table_gfdm, 0x180000, os.path.join(args.input, "GAME.DAT"), 1))
    filetables.append((read_file_table_gfdm, 0x198000, os.path.join(args.input, "GAME.DAT"), 1))
    filetables.append((read_file_table_gfdm, 0xff0000, os.path.join(args.input, "GAME.DAT"), 1))
    filetables.append((read_file_table_gfdm2, 0xfe4000, os.path.join(args.input, "GAME.DAT"), 1)) # Guitar Freaks 3rd Mix
    filetables.append((read_file_table_gfdm3, 0xad2800, os.path.join(args.input, "GAME.DAT"), 2)) # Guitar Freaks 4th Mix
    filetables.append((read_file_table_gfdm3, 0x384000, os.path.join(args.input, "GAME.DAT"), 2)) # Guitar Freaks 5th Mix
    filetables.append((read_file_table_gfdm3, 0x5ef800, os.path.join(args.input, "GAME.DAT"), 2)) # Drummania 2nd
    filetables.append((read_file_table_gfdm3, 0x8c6800, os.path.join(args.input, "GAME.DAT"), 2)) # Drummania 3rd
    filetables.append((read_file_table_gfdm3, 0x72f000, os.path.join(args.input, "GAME.DAT"), 2)) # Drummania 4th
    filetables.append((read_file_table_gfdm3, 0x734800, os.path.join(args.input, "GAME.DAT"), 2)) # Percussion Freaks 4th KAA
    filetables.append((read_file_table_gfdm3, 0x736000, os.path.join(args.input, "GAME.DAT"), 2)) # Percussion Freaks 4th AAA
    filetables.append((read_file_table_gfdm3, 0x8a5000, os.path.join(args.input, "GAME.DAT"), 2)) # Percussion Freaks 3rd? KAA
    filetables.append((read_file_table_gfdm2, 0x178000, os.path.join(args.input, "GQ883JA.DAT"), 1)) # Guitar Freaks 2nd Mix
    filetables.append((read_file_table_gfdm2, 0x100000, os.path.join(args.input, "GQ886JA.DAT"), 1)) # Guitar Freaks
    filetables.append((read_file_table_gfdm2, 0x100000, os.path.join(args.input, "GQ886AA.DAT"), 1))
    filetables.append((read_file_table_gfdm2, 0x100000, os.path.join(args.input, "GQ886EA.DAT"), 1))
    filetables.append((read_file_table_gfdm2, 0x100000, os.path.join(args.input, "GQ886UA.DAT"), 1))
    filetables.append((read_file_table_gfdm2, 0x1b8000, os.path.join(args.input, "GE929JA.DAT"), 1)) # Guitar Freaks Link Kit 1

    filetable_results = []
    for i, t in enumerate(filetables):
        try:
            f, offset, filename, result_type = t
            results = f(filename, offset)

            if results:
                filetable_results.append((t, results))

        except:
            pass

    candidate_results = []
    for i, (t, results) in enumerate(filetable_results):
        f, offset, filename, result_type = t

        # Try to find likely candidates by determining which follows the expected format
        if result_type == 1:
            # Hashes should be in ascending order
            is_good = True
            last_idx = None
            last_filename_hash = None
            for entry in results:
                if (last_idx is None or entry['idx'] > last_idx) and (last_filename_hash is None or entry['filename_hash'] > last_filename_hash):
                    last_idx = entry['idx']
                    last_filename_hash = entry['filename_hash']

                else:
                    is_good = False
                    break

        elif result_type == 2:
            is_good = True

        if is_good:
            candidate_results.append((t, results, filename))

    for candidate_idx, candidate in enumerate(candidate_results):
        if len(candidate_results) > 1:
            output_folder = os.path.join(args.output, "%d" % candidate_idx)

        else:
            output_folder = args.output

        if output_folder and not os.path.exists(output_folder):
            os.makedirs(output_folder)

        print("Dumping using setting:", candidate[0])
        dump_data(args.input, output_folder, candidate, candidate[2])


    # for filename, data in [("hash_list.pkl", hash_list), ("used_hash_list.pkl", used_hash_list), ("unknown_hash_list.pkl", unknown_hash_list), ("final_hash_list.pkl", used_hash_list)]:
    #     if os.path.exists(filename):
    #         existing_hash_list = pickle.load(open(filename, "rb"))
    #         data.update(existing_hash_list)

    #     pickle.dump(data, open("new_" + filename, "wb"))

    #     if os.path.exists(filename):
    #         os.unlink(filename)

    #     os.rename("new_" + filename, filename)

    print()
    for candidate_idx, candidate in enumerate(candidate_results):
        print("Dumped using settings:", candidate[0])

if __name__ == "__main__":
    main()
