import argparse
import ctypes
import os
import string
import struct

def get_filename_hash(filename):
    hash = 0

    for cidx, c in enumerate(filename):
        for i in range(6):
            hash = ctypes.c_int(((hash >> 31) & 0x4c11db7) ^ ((hash << 1) | ((ord(c) >> i) & 1))).value

    return hash & 0xffffffff


def decrypt_data(data):
    from Crypto.Cipher import Blowfish

    keys = {
        '13G0': {'iv': 'desvsrow', 'key': 'パパパヤーぶっちゃけＰＯＰ’Ｎ大迷惑'},
        '13S0': {'iv': 'wacvsjun', 'key': 'いろはにほへぽちりぬるぽ'},
        '13P0': {'iv': 'tvCxT5no', 'key': 'キャホーイ！祭りだ！わっしょこい！'},
        '13G1': {'iv': 'LTgStteb', 'key': 'いつだってお祭りさわぎのカーニバル。なんでもあるよ〜。'},
        '13G2': {'iv': 'wNyxSyDQ', 'key': 'ドンドンチキチキカーニバル！'},
        '13G3': {'iv': 'wClBXmGr', 'key': 'ぼくらの街にやってきた素敵で愉快なカーニバル'},
        '13G4': {'iv': 'PiWHlj56', 'key': 'さぁさぁ\u3000みなさんお待ちかね\u3000とってもゆかいなカーニバル！'},
        '13G5': {'iv': 'dkWEN8Qk', 'key': 'いつだってお祭りさわぎのカーニバル。なんでもあるよ〜。'},
        '13G6': {'iv': 'WmPMVqCr', 'key': 'わくわくカーニバル！なにで遊ぶかまよっちゃう〜'},
        '13G7': {'iv': '2V00iGp5', 'key': 'リズムにのってボタンを叩けば、わくわくカーニバル・オン・ステージ！'},
        '13G8': {'iv': 'WlMhESmP', 'key': 'ようこそ、きらめきカーニバルへ'},
        '13G9': {'iv': 'cisXpifl', 'key': 'わくわく\u3000はじまる\u3000カーニバル！'},
        '13S1': {'iv': 'C47vuHWv', 'key': 'カーニバルがやってきた'},
        '13S2': {'iv': 'DUtTySYu', 'key': 'ポップンカーニバルのお通りだい'},
        '13S3': {'iv': 'bLMNB8DN', 'key': 'ポップンカーニバルでココロうきうき'},
        '13S4': {'iv': 'o5INlY6V', 'key': 'さわげやポップン'},
        '13S5': {'iv': '2brvTlYu', 'key': '集まれポップンカーニバル'},
        '13S6': {'iv': 'grnOhljs', 'key': 'ポップンサーカスが街にやってきた！'},
        '13S7': {'iv': '43fFbQqx', 'key': '吃驚仰天摩訶不思議'},
        '13S8': {'iv': 'T9je5pa5', 'key': 'ぼくらの街にやってきた素敵で愉快なカーニバル'},
        '13S9': {'iv': 'zzAqUyUa', 'key': '摩訶不思議な宴をお楽しみあそばせ。'},
        '13P1': {'iv': 'XfXeyeGD', 'key': 'ぼくもわたしもお祭り大好き'},
        '13P2': {'iv': 'hUgqKFXC', 'key': 'うかれてはじけて'},
        '13P3': {'iv': 'MgOREWWd', 'key': 'みんなの町にやってきた！'},
        '13P4': {'iv': 'vvDq1vyZ', 'key': '夢のチケット発売中。'},
        '13P5': {'iv': 'KvdgJSRY', 'key': '聞こえてくるよ遠くから'},
        '13P6': {'iv': 'K8osNm4z', 'key': '乙女心に恋心'},
        '13P7': {'iv': 'AToePkrl', 'key': 'さぁさぁみんな寄っといで！'},
        '13P8': {'iv': 'N2JPvhOd', 'key': '楽しい音楽ショー'},
        '13P9': {'iv': 'NZuuPltz', 'key': '火の輪くぐりに\u3000トライアゲエイン'},
        '13A0': {'iv': 'rP2eb6LK', 'key': 'さあ！ハッピータイム'},
        '13A1': {'iv': 'X9YNso6d', 'key': 'サーカスがぼくらの街にやってくるくるミラクル'},
        '13A2': {'iv': 'oP2U6O7R', 'key': '世界じゅうの音楽のどきわく大行進ー♪お祭り騒ぎはまだまだ続くよ。'},
        '13A3': {'iv': 'MzkBVL9m', 'key': 'すてきなショーの\u3000\u3000'},
        '13A4': {'iv': 'AbzKfkud', 'key': '見てるだけじゃ楽しくないない'},
        '13A5': {'iv': 'sqYSM25b', 'key': 'みんなでお祭り盛り上げろ。'},
        '13A6': {'iv': 'R63VSaLE', 'key': 'あの娘もポワンと頬染める。'},
        '13A7': {'iv': 'K5eDOnXm', 'key': 'ひとときの夢をごらんあれ〜'},
        '13A8': {'iv': 'ww6JPyWf', 'key': '1人で・2人で・3人で！'},
        '13A9': {'iv': 'XS7JUaUJ', 'key': 'うっふんもあるでよ〜。'},
    }

    try:
        key_info = keys[data[:4].decode('ascii')]
        enc_len = int.from_bytes(data[4:8], 'little')

        cipher = Blowfish.new(key_info['key'].encode('shift-jis'), Blowfish.MODE_CBC, key_info['iv'].encode('ascii'))
        dec_data = cipher.decrypt(data)[8:]

        return bytearray(dec_data)[:enc_len]

    except:
        # Not encrypted?
        return data


def decompress_gcz(data):
    data_length = len(data)
    offset = 0
    output = []

    while offset < data_length:
        flag = data[offset]
        offset += 1

        for bit in range(8):
            if flag & (1 << bit):
                output.append(data[offset])
                offset += 1

            else:
                if offset + 2 > data_length:
                    break

                cmd1, cmd2 = data[offset:offset+2]
                lookback_length = (cmd1 & 0x0f) + 3
                lookback_offset = ((cmd1 & 0xf0) << 4) + cmd2
                offset += 2

                if cmd1 == 0 and cmd2 == 0:
                    break

                for _ in range(lookback_length):
                    loffset = len(output) - lookback_offset
                    if loffset <= 0 or loffset >= len(output):
                        output.append(0)

                    else:
                        output.append(output[loffset])

    return bytearray(output)


def get_file_data(infile, fileinfo):
    cur_offset = infile.tell()

    infile.seek(fileinfo['offset'])
    data = infile.read(fileinfo['size'])
    infile.seek(cur_offset)

    return data


def parse_system_idx(data):
    filename_hashes_add = {}

    count = int.from_bytes(data[6:8], byteorder="little")
    stroff = int.from_bytes(data[8:10], byteorder="little") - 0x180

    for i in range(count):
        filename = data[stroff+i*0x20:stroff+(i+1)*0x20].decode('ascii').strip('\0').lstrip('/')
        filename = "image/%s" % filename.lower()
        filename_hashes_add[get_filename_hash(filename)] = filename

    return filename_hashes_add


def find_strings_binary(exe_data, search_key):
    found_strings = []
    i = 0

    while i < len(exe_data) - len(search_key):
        if exe_data[i:i+len(search_key)] == search_key or exe_data[i:i+len(search_key)] == search_key.upper() or exe_data[i:i+len(search_key)] == search_key.lower():
            str_start = i
            str_end = i + len(search_key)

            while exe_data[str_end] != 0:
                str_end += 1

            while chr(exe_data[str_start - 1]) in string.printable:
                str_start -= 1

            found_str = exe_data[str_start:str_end].decode('ascii').lower()

            if found_str.startswith("disk0:/"):
                found_str = found_str[len("disk0:/"):]

            if found_str.startswith("disk0:"):
                found_str = found_str[len("disk0:"):]

            if found_str[0] == '/':
                found_str = found_str[1:]

            if '%' not in found_str:
                found_strings.append(found_str)

            i = str_end + 1

        else:
            i += 1

    return found_strings


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', help='Input folder', default=None, required=True)
    parser.add_argument('-o', '--output', help='Output folder', default=None)
    parser.add_argument('-d', '--decrypt', help='Decryption for pop\'n 13 and 14', default=False, action='store_true')

    args = parser.parse_args()

    if not os.path.exists(args.output):
        os.makedirs(args.output)

    entries = []
    with open(args.input, "rb") as infile:
        system_files = []

        # Not sure how this really works
        for offset in [0x20]:
            infile.seek(offset)
            sysfile_offset = int.from_bytes(infile.read(4), byteorder="big") * 0x100
            sysfile_offset2 = int.from_bytes(infile.read(4), byteorder="big") * 0x100

            infile.seek(offset + 0x10)
            sysfile_size = int.from_bytes(infile.read(4), byteorder="big")
            checksum = int.from_bytes(infile.read(4), byteorder="big")

            system_files.append({
                'offsets': [x for x in [sysfile_offset, sysfile_offset2] if x != 0],
                'size': sysfile_size,
                'checksum': checksum,
            })

        for offset in [0xa0]:
            infile.seek(offset)
            sysfile_offset = int.from_bytes(infile.read(4), byteorder="little") * 0x100

            infile.seek(offset + 0x10)
            sysfile_size = int.from_bytes(infile.read(4), byteorder="little")
            infile.seek(4, 1)
            checksum = int.from_bytes(infile.read(4), byteorder="little")

            system_files.append({
                'offsets': [x for x in [sysfile_offset] if x != 0],
                'size': sysfile_size,
                'checksum': checksum,
            })

        filetable_offset = 0
        for offset in [0x100]:
            infile.seek(offset)
            sysfile_offset = int.from_bytes(infile.read(4), byteorder="little") * 0x100
            sysfile_offset2 = int.from_bytes(infile.read(4), byteorder="little") * 0x100

            infile.seek(offset + 0x10)
            sysfile_size = int.from_bytes(infile.read(4), byteorder="little")
            checksum = int.from_bytes(infile.read(4), byteorder="little")

            filetable_offset = sysfile_offset + 0x100000

            system_files.append({
                'offsets': [x for x in [sysfile_offset, sysfile_offset2] if x != 0],
                'size': sysfile_size,
                'checksum': checksum,
            })

        for idx, sysfile in enumerate(system_files):
            for idx2, offset in enumerate(sysfile['offsets']):
                infile.seek(offset)

                print(sysfile)

                if idx2 == 0:
                    output_filename = "sysfile_%d.bin" % idx

                else:
                    output_filename = "sysfile_%d_%d.bin" % (idx, idx2)

                raw_data = infile.read(sysfile['size'])

                with open(os.path.join(args.output, "raw_" + output_filename), "wb") as outfile:
                    outfile.write(raw_data)

                checksum = sum([int.from_bytes(raw_data[i:i+2], 'big') for i in range(0, len(raw_data), 2)]) & 0x7fffffff
                if checksum != sysfile.get('checksum', 0):
                    print("sysfile %s checksum did not match! %08x vs %08x" % (output_filename, checksum, sysfile.get('checksum', 0)))

                try:
                    dec_data = decompress_gcz(raw_data)

                    with open(os.path.join(args.output, output_filename), "wb") as outfile:
                        outfile.write(dec_data)

                except:
                    pass

        filenames = [
            "ee/boot/game.bin",
            "boot/game.bin",
            "game.bin",
            "boot.bin",
            "title.txt",
        ]

        exe_data = open(os.path.join(args.output, "sysfile_2.bin"), "rb").read()

        print("Filetable Offset: %08x" % filetable_offset)

        infile.seek(filetable_offset)

        # Find game.bin if it exists. Hacky piece of shit code
        filename_hashes = {}
        for filename in filenames:
            filename_hashes[get_filename_hash(filename)] = filename

        while True:
            filename_hash, file_offset, file_size, file_unk, checksum, file_unk3 = struct.unpack("<IIIIII", infile.read(0x18))

            if filename_hash == 0:
                break

            file_offset *= 0x200

            entry = {
                'filename_hash': filename_hash,
                'offset': file_offset,
                'size': file_size,
                'checksum': checksum,
            }

            entries.append(entry)

        for entry in entries:
            infile.seek(entry['offset'])

            if entry['filename_hash'] in filename_hashes:
                output_filename = filename_hashes[entry['filename_hash']]

            else:
                continue

            output_filename = os.path.join(args.output, output_filename)

            if os.path.exists(output_filename):
                continue

            basedir = os.path.dirname(output_filename)
            if basedir and not os.path.exists(basedir):
                os.makedirs(basedir)

            with open(output_filename, "wb") as outfile:
                print(entry)
                print(output_filename)

                data = infile.read(entry['size'])

                if args.decrypt:
                    data = decrypt_data(data)

                outfile.write(data)

        exe_path = os.path.join(args.output, "ee", "boot", "game.bin")
        if os.path.exists(exe_path):
            exe_data += open(exe_path, "rb").read()
            print("Found", exe_path)

        infile.seek(filetable_offset)

        found_filenames = [
            'libsd.irx',
            'mcman.irx',
            'mcserv.irx',
            'padman.irx',
            'sddrviop.irx',
            'sio2man.irx',
            'snd.irx',
            'snd2.irx',
            'filesys.irx',
            'filesys2.irx',
        ]
        found_filenames += find_strings_binary(exe_data, b".bin")
        found_filenames += find_strings_binary(exe_data, b".gcz")
        found_filenames += find_strings_binary(exe_data, b".gzz")
        found_filenames += find_strings_binary(exe_data, b".irx")
        found_filenames += find_strings_binary(exe_data, b".mhd")
        found_filenames += find_strings_binary(exe_data, b".idx")

        for folder in ["image/", "patch/", "modules/", "irx/", "iop/", "iop/modules", ""]:
            for filename in found_filenames + filenames:
                filenames.append(folder + filename)
                filenames.append((folder + filename).upper())
                filenames.append((folder + filename).lower())

        # TODO: Find strings that contain number formats and try to bruteforce them automatically
        # Specific files from pop'n music 9
        for i1 in range(0, 10):
            for i2 in range(0, 10):
                for i3 in range(0, 100):
                    filenames.append("md_xx/md_%d%d%02d.dat" % (i1, i2, i3))

        for i in range(0, 1000):
            for subfolder in ["", "image/"]:
                for ext in ["gcz", "gzz"]:
                    filenames.append("%snorma/d_n_%03d.%s" % (subfolder, i, ext))
                    filenames.append("%sbg/bg_%03d.%s" % (subfolder, i, ext))
                    filenames.append("%snt/nt_%03d.%s" % (subfolder, i, ext))
                    filenames.append("%skc/kc_%03d.%s" % (subfolder, i, ext))
                    filenames.append("%skc_normal/banner_%02d.%s" % (subfolder, i, ext))
                    filenames.append("%srj/rj_%03d.%s" % (subfolder, i, ext))
                    filenames.append("%scg/cg_%03d.%s" % (subfolder, i, ext))
                    filenames.append("%sha_art/ha_at%03d.%s" % (subfolder, i, ext))
                    filenames.append("%sha_art/ha_art_%03d.%s" % (subfolder, i, ext))
                    filenames.append("%sprize_picture/g_%02d.%s" % (subfolder, i, ext))

        filename_hashes = {}
        for filename in filenames:
            filename_hashes[get_filename_hash(filename)] = filename

        while True:
            filename_hash, file_offset, file_size, file_unk, checksum, file_unk3 = struct.unpack("<IIIIII", infile.read(0x18))

            if filename_hash == 0:
                break

            file_offset *= 0x200

            entry = {
                'filename_hash': filename_hash,
                'offset': file_offset,
                'size': file_size,
                'checksum': checksum,
            }

            entries.append(entry)

            if entry['filename_hash'] in filename_hashes and filename_hashes[entry['filename_hash']].endswith("system.idx"):
                # Parse system.idx for more filenames
                filename_hashes.update(parse_system_idx(get_file_data(infile, entry)))

                base_filename = filename_hashes[entry['filename_hash']].lstrip("image/").rstrip("/system.idx")

                for subfolder in ["", "image/"]:
                    for ext in ["gcz", "gzz"]:
                        ha_chara_filename = "%sha_chara/ha_%s.%s" % (subfolder, base_filename, ext)
                        filename_hashes[get_filename_hash(ha_chara_filename)] = ha_chara_filename

        for entry in entries:
            infile.seek(entry['offset'])

            if entry['filename_hash'] in filename_hashes:
                output_filename = filename_hashes[entry['filename_hash']]

            else:
                output_filename = "%08x.bin" % entry['filename_hash']

            output_filename = os.path.join(args.output, output_filename)

            if os.path.exists(output_filename):
                continue

            basedir = os.path.dirname(output_filename)
            if basedir and not os.path.exists(basedir):
                os.makedirs(basedir)

            with open(output_filename, "wb") as outfile:
                print(entry)
                print(output_filename)

                data = infile.read(entry['size'])

                if args.decrypt:
                    data = decrypt_data(data)

                outfile.write(data)

            checksum = sum(data) & 0xffffffff
            if checksum != entry['checksum']:
                print("%s checksum did not match! %08x vs %08x" % (output_filename, checksum, entry['checksum']))

        # Seems to always be 0x20000000? But later HDDs use encrypted data so the PM09 header won't be found
        next_file_offset = 0x20000000
        file_id = 0

        while True:
            infile.seek(next_file_offset)
            next_file_offset = infile.tell() + 0x1400000

            header = infile.read(4)

            if len(header) != 4:
                break

            if header != b'PM09':
                continue

            print("Dumping sound data @ %08x" % (infile.tell() - 4))

            filecount = int.from_bytes(infile.read(4), byteorder="little")

            file_id2 = 0
            for i in range(filecount):
                file_offset, file_size = struct.unpack("<II", infile.read(8))
                file_offset *= 0x200

                if file_offset == 0 and file_size == 0:
                    break

                output_folder = os.path.join(args.output, "_data/%04d/" % file_id)

                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)

                output_filename = os.path.join(output_folder, "%04d_%d.bin" % (file_id, file_id2))

                if os.path.exists(output_filename):
                    continue

                print("Dumping", output_filename)
                with open(output_filename, "wb") as outfile:
                    entry = {
                        'offset': file_offset,
                        'size': file_size,
                    }

                    data = get_file_data(infile, entry)

                    if args.decrypt:
                        data = decrypt_data(data)

                        try:
                            data = decompress_gcz(data)

                        except:
                            pass


                    outfile.write(data)

                file_id2 += 1

            file_id += 1