import argparse
import glob
import hashlib
import itertools
import os
import struct

from ctypes import c_ulong

class PakDumper:
    def __init__(self, packinfo, demux, fast):
        self.entries = self.parse_pack_data(packinfo)
        self.packlist = self.generate_packlist()
        self.crc32_tab = self.generate_crc32_table()
        self.demux = demux
        self.fast = fast


    def generate_crc32_table(self):
        crc32_tab = []
        crc32_constant = 0xEDB88320

        for i in range(0, 256):
            crc = i
            for j in range(0, 8):
                if crc & 0x00000001:
                    crc = int(c_ulong(crc >> 1).value) ^ crc32_constant
                else:
                    crc = int(c_ulong(crc >> 1).value)

            crc32_tab.append(crc)

        return crc32_tab


    def calculate_filename_hash(self, input):
        if input.startswith("data/"):
            input = "/" + input

        if input.startswith("/data/aep"):
            input = input.lower()

        input = bytearray(input, 'ascii')

        crc32_sum = 0xffffffff
        for i in range(len(input)):
            crc32_sum = self.crc32_tab[(crc32_sum & 0xff) ^ input[i]] ^ ((crc32_sum >> 8) & 0xffffffff)

        return ~crc32_sum & 0xffffffff


    def calculate_filename_hash_crc16(self, data):
        crc16_ccitt_table_reverse = [
            0x0000, 0x1189, 0x2312, 0x329B, 0x4624, 0x57AD, 0x6536, 0x74BF,
            0x8C48, 0x9DC1, 0xAF5A, 0xBED3, 0xCA6C, 0xDBE5, 0xE97E, 0xF8F7,
            0x1081, 0x0108, 0x3393, 0x221A, 0x56A5, 0x472C, 0x75B7, 0x643E,
            0x9CC9, 0x8D40, 0xBFDB, 0xAE52, 0xDAED, 0xCB64, 0xF9FF, 0xE876,
            0x2102, 0x308B, 0x0210, 0x1399, 0x6726, 0x76AF, 0x4434, 0x55BD,
            0xAD4A, 0xBCC3, 0x8E58, 0x9FD1, 0xEB6E, 0xFAE7, 0xC87C, 0xD9F5,
            0x3183, 0x200A, 0x1291, 0x0318, 0x77A7, 0x662E, 0x54B5, 0x453C,
            0xBDCB, 0xAC42, 0x9ED9, 0x8F50, 0xFBEF, 0xEA66, 0xD8FD, 0xC974,
            0x4204, 0x538D, 0x6116, 0x709F, 0x0420, 0x15A9, 0x2732, 0x36BB,
            0xCE4C, 0xDFC5, 0xED5E, 0xFCD7, 0x8868, 0x99E1, 0xAB7A, 0xBAF3,
            0x5285, 0x430C, 0x7197, 0x601E, 0x14A1, 0x0528, 0x37B3, 0x263A,
            0xDECD, 0xCF44, 0xFDDF, 0xEC56, 0x98E9, 0x8960, 0xBBFB, 0xAA72,
            0x6306, 0x728F, 0x4014, 0x519D, 0x2522, 0x34AB, 0x0630, 0x17B9,
            0xEF4E, 0xFEC7, 0xCC5C, 0xDDD5, 0xA96A, 0xB8E3, 0x8A78, 0x9BF1,
            0x7387, 0x620E, 0x5095, 0x411C, 0x35A3, 0x242A, 0x16B1, 0x0738,
            0xFFCF, 0xEE46, 0xDCDD, 0xCD54, 0xB9EB, 0xA862, 0x9AF9, 0x8B70,
            0x8408, 0x9581, 0xA71A, 0xB693, 0xC22C, 0xD3A5, 0xE13E, 0xF0B7,
            0x0840, 0x19C9, 0x2B52, 0x3ADB, 0x4E64, 0x5FED, 0x6D76, 0x7CFF,
            0x9489, 0x8500, 0xB79B, 0xA612, 0xD2AD, 0xC324, 0xF1BF, 0xE036,
            0x18C1, 0x0948, 0x3BD3, 0x2A5A, 0x5EE5, 0x4F6C, 0x7DF7, 0x6C7E,
            0xA50A, 0xB483, 0x8618, 0x9791, 0xE32E, 0xF2A7, 0xC03C, 0xD1B5,
            0x2942, 0x38CB, 0x0A50, 0x1BD9, 0x6F66, 0x7EEF, 0x4C74, 0x5DFD,
            0xB58B, 0xA402, 0x9699, 0x8710, 0xF3AF, 0xE226, 0xD0BD, 0xC134,
            0x39C3, 0x284A, 0x1AD1, 0x0B58, 0x7FE7, 0x6E6E, 0x5CF5, 0x4D7C,
            0xC60C, 0xD785, 0xE51E, 0xF497, 0x8028, 0x91A1, 0xA33A, 0xB2B3,
            0x4A44, 0x5BCD, 0x6956, 0x78DF, 0x0C60, 0x1DE9, 0x2F72, 0x3EFB,
            0xD68D, 0xC704, 0xF59F, 0xE416, 0x90A9, 0x8120, 0xB3BB, 0xA232,
            0x5AC5, 0x4B4C, 0x79D7, 0x685E, 0x1CE1, 0x0D68, 0x3FF3, 0x2E7A,
            0xE70E, 0xF687, 0xC41C, 0xD595, 0xA12A, 0xB0A3, 0x8238, 0x93B1,
            0x6B46, 0x7ACF, 0x4854, 0x59DD, 0x2D62, 0x3CEB, 0x0E70, 0x1FF9,
            0xF78F, 0xE606, 0xD49D, 0xC514, 0xB1AB, 0xA022, 0x92B9, 0x8330,
            0x7BC7, 0x6A4E, 0x58D5, 0x495C, 0x3DE3, 0x2C6A, 0x1EF1, 0x0F78
        ]

        checksum = 0xffff

        for b in bytearray(data, "ascii"):
            checksum = ((checksum >> 8) ^ crc16_ccitt_table_reverse[(checksum ^ b) & 0xff]) & 0xffff

        return ~checksum & 0xffff


    def calculate_filename_hash_crc16_cs(self, data):
        crc16_ccitt_table = [
            0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
            0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
            0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
            0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
            0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
            0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
            0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
            0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
            0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
            0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
            0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
            0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
            0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
            0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
            0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
            0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
            0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
            0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
            0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
            0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
            0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
            0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
            0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
            0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
            0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
            0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
            0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
            0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
            0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
            0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
            0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
            0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
        ]

        checksum = 0

        for b in bytearray(data, "ascii"):
            checksum = ((checksum << 8) & 0xff00 ^ crc16_ccitt_table[((checksum >> 8) & 0xff) ^ b]) & 0xffff

        return checksum & 0xffff


    def parse_pack_data(self, filename):
        entries = {}

        with open(filename, "rb") as infile:
            infile.seek(0x08)
            end_addr = int.from_bytes(infile.read(4), 'little')
            infile.seek(0x10)

            while infile.tell() < end_addr:
                md5sum = infile.read(0x10)
                data = infile.read(0x10)

                if not md5sum or not data:
                    break

                key1, key2, packid, offset, filesize = struct.unpack("<IHHII", data)

                entry = {
                    'key1': key1, # CRC32 filename hash
                    'key2': key2, # CRC16 filename hash
                    'packid': packid,
                    'offset': offset,
                    'filesize': filesize,
                    'md5sum': md5sum,
                }

                if key1 in entries and entries[key1]['key2'] == key2:
                    print("Found key already:", entries[key1])
                    continue

                entries[key1] = entry

        return entries


    def generate_packlist(self):
        packlist = []

        cur_folder = 0
        for i in range(0, 3000):
            if (i % 30) == 0 and i > 0:
                cur_folder += 1


            p1 = "data/pack/d%03d/pack%04d.pak" % (cur_folder, i)
            p2 = "data/pack_v3/d%03d/pack%04d.pak" % (cur_folder, i)

            if os.path.exists(p2):
                packlist.append(p2)

            else:
                packlist.append(p1)

        return packlist


    def rol(self, val, r_bits):
        return (val << r_bits) & 0xFFFFFFFF | ((val & 0xFFFFFFFF) >> (32 - r_bits))


    def decrypt(self, data, key1, key2):
        if self.fast:
            # Uses a Cython module for fast decryption
            import pakdec
            pakdec.decrypt(data, len(data), key1, key2)
            return data

        key = key1

        for i in range(0, int(len(data) / 4) * 4, 4):
            key = self.rol(key + key2, 3)

            data[i] ^= key & 0xff
            data[i + 1] ^= (key >> 8) & 0xff
            data[i + 2] ^= (key >> 16) & 0xff
            data[i + 3] ^= (key >> 24) & 0xff

        i += 4

        key = self.rol(key + key2, 3)
        parts = [key & 0xff, (key >> 8) & 0xff, (key >> 16) & 0xff, (key >> 24) & 0xff]
        for j in range(len(data) - i):
                data[i] ^= parts[j]

        return data


    def file_exists(self, input):
        filename_hash = self.calculate_filename_hash(input)
        filename_hash_crc16 = self.calculate_filename_hash_crc16(input)
        filename_hash_crc16_2 = self.calculate_filename_hash_crc16_cs(input)
        exists = filename_hash in self.entries and self.entries[filename_hash]['key2'] in [filename_hash_crc16, filename_hash_crc16_2]

        if exists:
            self.entries[filename_hash]['orig_filename'] = input

        return exists


    def get_md5sum(self, data):
        md5 = hashlib.md5()
        md5.update(data)
        return md5.digest()


    def extract_data_mem(self, path, input_path="", filename_hash=None):
        if filename_hash is None:
            filename_hash = self.calculate_filename_hash(path)

        if filename_hash not in self.entries:
            print("Couldn't find entry for", path)
            return None

        entry = self.entries[filename_hash]

        if entry['packid'] > len(self.packlist):
            print("[BAD PACK_ID] pack_id: %d, data_offset: %08x, data_size: %08x, filename: %s" % (entry['packid'], entry['offset'], entry['filesize'], path))
            return None

        packpath = self.packlist[entry['packid']]
        if packpath.startswith('/'):
            packpath = packpath[1:]

        packpath = os.path.join(input_path, packpath)

        if not os.path.exists(packpath):
            print("Could not find %s" % packpath)
            return None

        data = bytearray(open(packpath, "rb").read()[entry['offset']:entry['offset']+entry['filesize']])

        encryption = False
        if self.get_md5sum(data) != entry['md5sum']:
            encryption = True

        if encryption:
            decrypted = self.decrypt(data, entry['key1'], entry['key2'])

        else:
            decrypted = data

        if self.get_md5sum(data) != entry['md5sum']:
            print("Bad checksum for", path)

        return decrypted


    def extract_data(self, path, input_path, output_path):
        data = self.extract_data_mem(path, input_path)

        if path.startswith('/'):
            path = path[1:]

        output_path = os.path.join(output_path, path)

        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))

        open(output_path, "wb").write(data)

        if self.demux and os.path.splitext(output_path)[1].lower() == ".pss":
            from pss_demux import demux_pss
            demux_pss(output_path, os.path.dirname(output_path))

        return True


def bruteforce_filenames(dumper):
    filenames = []

    # TODO: Remove duplicates
    possible_filenames = [
        "/data/product/music/system/gfv_se.va2",
        "/data/product/music/system/gfv_se.va3",
        "/data/product/music/course_info.bin",
        "/data/product/music/jp_title.bin",
        "/data/product/music/music_info.bin",
        "/data/product/music/net_id.bin",
        "/data/pack/packinfo.bin",
        "/data/product/music/system/se.va2",
        "/data/product/music/system/ealogo_gf.pss",
        "/dev/nvram/config.xml",
        "/dev/nvram/network.xml",
        "/BISLPM-66575gfdmv2/gfdm.ico",
        "/BISLPM-66575gfdmv2/icon.sys",
        "/data/product/icon/gfdm.ico",
        "/data/product/icon/icon.sys",
        "/data/product/music/mdb.bin",
        "/data/product/music/mdb.xml",
        "/data/product/music/mdb_xg.xml",
        "/data/product/music/mdb_xg.bin",
        "/data/product/music/mdbe.bin",
        "/data/product/music/mdbe.xml",
        "/data/product/music/mdbe_xg.xml",
        "/data/product/music/mdbe_xg.bin",
        "/data/product/mdb.bin",
        "/data/product/mdb.xml",
        "/data/product/mdb_xg.xml",
        "/data/product/mdb_xg.bin",
        "/data/product/mdbe.bin",
        "/data/product/mdbe.xml",
        "/data/product/mdbe_xg.xml",
        "/data/product/mdbe_xg.bin",
        "/data/product/xml/mdbe_xg.xml",
        "/data/product/xml/mdbe_xg.bin",
        "/data/product/xml/mdbe.bin",
        "/data/product/xml/mdbe.xml",
        "/data/product/xml/mdbe_xg.xml",
        "/data/product/xml/mdbe_xg.bin",
        "/data/product/xml/mdbe.bin",
        "/data/product/xml/mdbe.xml",
        "/data/product/font/font16x16x8/0_0.img",
        "/data/product/font/font16x16x8/0_1.img",
        "/data/product/font/font16x16x8/1_0.img",
        "/data/product/font/font16x16x8/1_1.img",
        "/data/product/font/font16x16x8/1_2.img",
        "/data/product/font/font16x16x8/1_3.img",
        "/data/product/font/font16x16x8/2_0.img",
        "/data/product/font/font16x16x8/2_1.img",
        "/data/product/font/font16x16x8/2_2.img",
        "/data/product/font/font16x16x8/2_3.img",
        "/data/product/font/font16x16x8/3_0.img",
        "/data/product/font/font16x16x8/3_1.img",
        "/data/product/font/font16x16x8/3_2.img",
        "/data/product/font/font16x16x8/3_3.img",
        "/data/product/font/DFHSG7.TTC",
        "/data/product/d3/model/tex_gf_arc_info.bin",
        "/data/product/d3/model/tex_gf_card.bin",
        "/data/product/d3/model/tex_gf_caution.bin",
        "/data/product/d3/model/tex_gf_clear.bin",
        "/data/product/d3/model/tex_gf_common.bin",
        "/data/product/d3/model/tex_gf_ending.bin",
        "/data/product/d3/model/tex_gf_entry.bin",
        "/data/product/d3/model/tex_gf_entry1.bin",
        "/data/product/d3/model/tex_gf_free_info.bin",
        "/data/product/d3/model/tex_gf_game.bin",
        "/data/product/d3/model/tex_gf_game2.bin",
        "/data/product/d3/model/tex_gf_game2_2.bin",
        "/data/product/d3/model/tex_gf_game3.bin",
        "/data/product/d3/model/tex_gf_game3_2.bin",
        "/data/product/d3/model/tex_gf_game_2.bin",
        "/data/product/d3/model/tex_gf_hitchart.bin",
        "/data/product/d3/model/tex_gf_information.bin",
        "/data/product/d3/model/tex_gf_keyconfig.bin",
        "/data/product/d3/model/tex_gf_konamiid.bin",
        "/data/product/d3/model/tex_gf_loading.bin",
        "/data/product/d3/model/tex_gf_mcard.bin",
        "/data/product/d3/model/tex_gf_playstyle.bin",
        "/data/product/d3/model/tex_gf_puzzle.bin",
        "/data/product/d3/model/tex_gf_rec_info.bin",
        "/data/product/d3/model/tex_gf_result.bin",
        "/data/product/d3/model/tex_gf_result_total.bin",
        "/data/product/d3/model/tex_gf_resultss.bin",
        "/data/product/d3/model/tex_gf_roulette.bin",
        "/data/product/d3/model/tex_gf_save_load.bin",
        "/data/product/d3/model/tex_gf_scoreranking.bin",
        "/data/product/d3/model/tex_gf_select_mode.bin",
        "/data/product/d3/model/tex_gf_select_music.bin",
        "/data/product/d3/model/tex_gf_session.bin",
        "/data/product/d3/model/tex_gf_session2.bin",
        "/data/product/d3/model/tex_gf_session3.bin",
        "/data/product/d3/model/tex_gf_sessiona.bin",
        "/data/product/d3/model/tex_gf_sessiona2.bin",
        "/data/product/d3/model/tex_gf_sessiona3.bin",
        "/data/product/d3/model/tex_gf_sessionb.bin",
        "/data/product/d3/model/tex_gf_sessionb2.bin",
        "/data/product/d3/model/tex_gf_sessionb3.bin",
        "/data/product/d3/model/tex_gf_sessionc.bin",
        "/data/product/d3/model/tex_gf_sessionc2.bin",
        "/data/product/d3/model/tex_gf_sessionc3.bin",
        "/data/product/d3/model/tex_gf_shopranking.bin",
        "/data/product/d3/model/tex_gf_slot.bin",
        "/data/product/d3/model/tex_gf_title.bin",
        "/data/product/d3/model/tex_gf_tower.bin",
        "/data/product/d3/model/tex_gf_warning.bin",
        "/data/product/d3/model/tex_dm_arcinfo.bin",
        "/data/product/d3/model/tex_dm_freeinfo.bin",
        "/data/product/d3/model/tex_dm_game.bin",
        "/data/product/d3/model/tex_dm_game2.bin",
        "/data/product/d3/model/tex_dm_game3.bin",
        "/data/product/d3/model/tex_dm_keyconfig.bin",
        "/data/product/d3/model/tex_dm_recinfo.bin",
        "/data/product/d3/model/tex_gfdm_training.bin",
        "/data/product/d3/model/tex_usbdm_keyconfig.bin",
        "/data/product/aep/battle.bin",
        "/data/product/aep/dm_game.bin",
        "/data/product/aep/dm_game00.bin",
        "/data/product/aep/dm_select_mode.bin",
        "/data/product/aep/gf_aep_list.bin",
        "/data/product/aep/gf_battle.bin",
        "/data/product/aep/gf_battle_common.bin",
        "/data/product/aep/gf_battle_matching.bin",
        "/data/product/aep/gf_battle_result.bin",
        "/data/product/aep/gf_caution.bin",
        "/data/product/aep/gf_common.bin",
        "/data/product/aep/gf_custom.bin",
        "/data/product/aep/gf_eamuse.bin",
        "/data/product/aep/gf_ending.bin",
        "/data/product/aep/gf_game.bin",
        "/data/product/aep/gf_game00.bin",
        "/data/product/aep/gf_game_up.bin",
        "/data/product/aep/gf_hitchart.bin",
        "/data/product/aep/gf_how.bin",
        "/data/product/aep/gf_howdm.bin",
        "/data/product/aep/gf_howgf.bin",
        "/data/product/aep/gf_information.bin",
        "/data/product/aep/gf_jukebox.bin",
        "/data/product/aep/gf_name.bin",
        "/data/product/aep/gf_pass.bin",
        "/data/product/aep/gf_playdata.bin",
        "/data/product/aep/gf_result.bin",
        "/data/product/aep/gf_select_mode.bin",
        "/data/product/aep/gf_select_music.bin",
        "/data/product/aep/gf_title.bin",
        "/data/product/aep/gf_warning.bin",
        "/data/product/d3/model/dm_chip.bin",
        "/data/product/d3/model/mdl_dm_game.bin",
        "/data/product/d3/model/mdl_gf_ability.bin",
        "/data/product/d3/model/mdl_gf_ascii.bin",
        "/data/product/d3/model/mdl_gf_battle.bin",
        "/data/product/d3/model/mdl_gf_battle_common.bin",
        "/data/product/d3/model/mdl_gf_battle_matching.bin",
        "/data/product/d3/model/mdl_gf_battle_result.bin",
        "/data/product/d3/model/mdl_gf_caution.bin",
        "/data/product/d3/model/mdl_gf_chara.bin",
        "/data/product/d3/model/mdl_gf_common.bin",
        "/data/product/d3/model/mdl_gf_custom.bin",
        "/data/product/d3/model/mdl_gf_eamuse.bin",
        "/data/product/d3/model/mdl_gf_ending.bin",
        "/data/product/d3/model/mdl_gf_game.bin",
        "/data/product/d3/model/mdl_gf_hitchart.bin",
        "/data/product/d3/model/mdl_gf_how.bin",
        "/data/product/d3/model/mdl_gf_howdm.bin",
        "/data/product/d3/model/mdl_gf_howgf.bin",
        "/data/product/d3/model/mdl_gf_information.bin",
        "/data/product/d3/model/mdl_gf_jukebox.bin",
        "/data/product/d3/model/mdl_gf_name.bin",
        "/data/product/d3/model/mdl_gf_number.bin",
        "/data/product/d3/model/mdl_gf_pass.bin",
        "/data/product/d3/model/mdl_gf_playdata.bin",
        "/data/product/d3/model/mdl_gf_result.bin",
        "/data/product/d3/model/mdl_gf_select_mode.bin",
        "/data/product/d3/model/mdl_gf_select_music.bin",
        "/data/product/d3/model/mdl_gf_skill_meter.bin",
        "/data/product/d3/model/mdl_gf_taikai.bin",
        "/data/product/d3/model/mdl_gf_title.bin",
        "/data/product/d3/model/mdl_gf_warning.bin",
        "/data/product/d3/model/mdl_testmode.bin",
        "/data/product/d3/model/tex_dm_game.bin",
        "/data/product/d3/model/tex_gf_ability.bin",
        "/data/product/d3/model/tex_gf_ascii.bin",
        "/data/product/d3/model/tex_gf_battle.bin",
        "/data/product/d3/model/tex_gf_battle_common.bin",
        "/data/product/d3/model/tex_gf_battle_matching.bin",
        "/data/product/d3/model/tex_gf_battle_result.bin",
        "/data/product/d3/model/tex_gf_caution.bin",
        "/data/product/d3/model/tex_gf_chara.bin",
        "/data/product/d3/model/tex_gf_common.bin",
        "/data/product/d3/model/tex_gf_custom.bin",
        "/data/product/d3/model/tex_gf_eamuse.bin",
        "/data/product/d3/model/tex_gf_ending.bin",
        "/data/product/d3/model/tex_gf_game.bin",
        "/data/product/d3/model/tex_gf_hitchart.bin",
        "/data/product/d3/model/tex_gf_how.bin",
        "/data/product/d3/model/tex_gf_howdm.bin",
        "/data/product/d3/model/tex_gf_howgf.bin",
        "/data/product/d3/model/tex_gf_information.bin",
        "/data/product/d3/model/tex_gf_jukebox.bin",
        "/data/product/d3/model/tex_gf_name.bin",
        "/data/product/d3/model/tex_gf_number.bin",
        "/data/product/d3/model/tex_gf_pass.bin",
        "/data/product/d3/model/tex_gf_playdata.bin",
        "/data/product/d3/model/tex_gf_result.bin",
        "/data/product/d3/model/tex_gf_select_mode.bin",
        "/data/product/d3/model/tex_gf_select_music.bin",
        "/data/product/d3/model/tex_gf_skill_meter.bin",
        "/data/product/d3/model/tex_gf_taikai.bin",
        "/data/product/d3/model/tex_gf_title.bin",
        "/data/product/d3/model/tex_gf_warning.bin",
        "/data/product/d3/model/tex_testmode.bin",
        "/data/product/d3/package/debug.bin",
        "/data/product/d3/package/igai.bin",
        "/data/product/d3/package/ikeuchi.bin",
        "/data/product/d3/package/kobayashi.bin",
        "/data/product/d3/package/kono.bin",
        "/data/product/d3/package/mito.bin",
        "/data/product/d3/package/mochi.bin",
        "/data/product/d3/package/nayuta.bin",
        "/data/product/d3/package/packlist.bin",
        "/data/product/d3/package/sakai.bin",
        "/data/product/d3/package/takahashi.bin",
        "/data/product/d3/package/takehiro.bin",
        "/data/product/d3/package/usr02225.bin",
        "/data/product/d3/package/usr02798.bin",
        "/data/product/d3/package/usr04396.bin",
        "/data/product/d3/package/usr04682.bin",
        "/data/product/d3/package/usr04686.bin",
        "/data/product/d3/package/usr07026.bin",
        "/data/product/d3/package/usr10015403.bin",
        "/data/product/d3/package/usr10016395.bin",
        "/data/product/d3/package/usr10019619.bin",
        "/data/product/d3/package/usr10023386.bin",
        "/data/product/d3/package/usr10030684.bin",
        "/data/product/d3/package/usr10033101.bin",
        "/data/product/d3/package/usr14381.bin",
        "/data/product/d3/package/usr14388.bin",
        "/data/product/font/font16x16x8/0_0.img",
        "/data/product/font/font16x16x8/0_1.img",
        "/data/product/font/font16x16x8/1_0.img",
        "/data/product/font/font16x16x8/1_1.img",
        "/data/product/font/font16x16x8/1_2.img",
        "/data/product/font/font16x16x8/1_3.img",
        "/data/product/font/font16x16x8/2_0.img",
        "/data/product/font/font16x16x8/2_1.img",
        "/data/product/font/font16x16x8/2_2.img",
        "/data/product/font/font16x16x8/2_3.img",
        "/data/product/font/font16x16x8/3_0.img",
        "/data/product/font/font16x16x8/3_1.img",
        "/data/product/font/font16x16x8/3_2.img",
        "/data/product/font/font16x16x8/3_3.img",
        "/data/product/music/mdbe_xg.bin",
        "/data/product/movie/system/entry00.m2v",
        "/data/product/movie/system/title00.m2v",
        "/data/product/d3/model/dm_chip.bin",
        "/data/product/font/DFHSG7.TTC",
        "/data/product/music/system/gfxg_se.va3",
        "/data/product/music/system/dmxg_dflt.va3",
        "/data/product/music/system/gfxg_se.va3",
        "/data/product/music/system/dmxg_se.va3",
        "/data/product/music/system/gfv8_se.va3",
        "/data/product/music/system/dmv8_dflt.va3",
        "/data/product/music/system/gfv8_se.va3",
        "/data/product/music/system/dmv8_se.va3",
        "/data/product/aep/battle.bin",
        "/data/product/aep/cm_group.bin",
        "/data/product/aep/cm_group_entry.bin",
        "/data/product/aep/cm_paseli.bin",
        "/data/product/aep/cm_transition.bin",
        "/data/product/aep/cm_vtleff_bg.bin",
        "/data/product/aep/cm_vtleff_fg.bin",
        "/data/product/aep/cm_vtleff_mg.bin",
        "/data/product/aep/co_paseli.bin",
        "/data/product/aep/co_vtleff_bg.bin",
        "/data/product/aep/dm_game.bin",
        "/data/product/aep/dm_select_mode.bin",
        "/data/product/aep/gd_gam_gauge.bin",
        "/data/product/aep/gd_gam_lp.bin",
        "/data/product/aep/gd_group.bin",
        "/data/product/aep/gf_aep_list.bin",
        "/data/product/aep/gf_battle.bin",
        "/data/product/aep/gf_battle_common.bin",
        "/data/product/aep/gf_battle_matching.bin",
        "/data/product/aep/gf_battle_result.bin",
        "/data/product/aep/gf_caution.bin",
        "/data/product/aep/gf_common.bin",
        "/data/product/aep/gf_custom.bin",
        "/data/product/aep/gf_eamuse.bin",
        "/data/product/aep/gf_ending.bin",
        "/data/product/aep/gf_game.bin",
        "/data/product/aep/gf_game_up.bin",
        "/data/product/aep/gf_hitchart.bin",
        "/data/product/aep/gf_howdm.bin",
        "/data/product/aep/gf_howgf.bin",
        "/data/product/aep/gf_information.bin",
        "/data/product/aep/gf_name.bin",
        "/data/product/aep/gf_pass.bin",
        "/data/product/aep/gf_playdata.bin",
        "/data/product/aep/gf_result.bin",
        "/data/product/aep/gf_select_mode.bin",
        "/data/product/aep/gf_select_music.bin",
        "/data/product/aep/gf_title.bin",
        "/data/product/aep/gf_warning.bin",
        "/data/product/aep/sp_shop_cmpship.bin",
        "/data/product/aep/sp_shop_cmpship_rank.bin",
        "/data/product/aep/sp_shop_entry.bin",
        "/data/product/aep/sp_shop_taikai.bin",
        "/data/product/aep/sp_shop_taikai_rank.bin",
        "/data/product/d3/model/mdl_attack_effect.bin",
        "/data/product/d3/model/mdl_cm_customicon.bin",
        "/data/product/d3/model/mdl_cm_custom_icon.bin",
        "/data/product/d3/model/mdl_cm_event_logo.bin",
        "/data/product/d3/model/mdl_cm_group.bin",
        "/data/product/d3/model/mdl_cm_groupicon.bin",
        "/data/product/d3/model/mdl_cm_group_common.bin",
        "/data/product/d3/model/mdl_cm_group_entry.bin",
        "/data/product/d3/model/mdl_cm_group_icon.bin",
        "/data/product/d3/model/mdl_cm_group_match.bin",
        "/data/product/d3/model/mdl_cm_item_icon.bin",
        "/data/product/d3/model/mdl_cm_paseli.bin",
        "/data/product/d3/model/mdl_cm_transition.bin",
        "/data/product/d3/model/mdl_cm_vtleff_bg.bin",
        "/data/product/d3/model/mdl_cm_vtleff_fg.bin",
        "/data/product/d3/model/mdl_cm_vtleff_mg.bin",
        "/data/product/d3/model/mdl_com_transition.bin",
        "/data/product/d3/model/mdl_dm_game.bin",
        "/data/product/d3/model/mdl_gd_gam_lp.bin",
        "/data/product/d3/model/mdl_gfdm_transition.bin",
        "/data/product/d3/model/mdl_gf_ability.bin",
        "/data/product/d3/model/mdl_gf_ascii.bin",
        "/data/product/d3/model/mdl_gf_battle.bin",
        "/data/product/d3/model/mdl_gf_battle_common.bin",
        "/data/product/d3/model/mdl_gf_battle_matching.bin",
        "/data/product/d3/model/mdl_gf_battle_result.bin",
        "/data/product/d3/model/mdl_gf_caution.bin",
        "/data/product/d3/model/mdl_gf_chara.bin",
        "/data/product/d3/model/mdl_gf_common.bin",
        "/data/product/d3/model/mdl_gf_custom.bin",
        "/data/product/d3/model/mdl_gf_eamuse.bin",
        "/data/product/d3/model/mdl_gf_ending.bin",
        "/data/product/d3/model/mdl_gf_game.bin",
        "/data/product/d3/model/mdl_gf_hitchart.bin",
        "/data/product/d3/model/mdl_gf_how.bin",
        "/data/product/d3/model/mdl_gf_howdm.bin",
        "/data/product/d3/model/mdl_gf_howgf.bin",
        "/data/product/d3/model/mdl_gf_information.bin",
        "/data/product/d3/model/mdl_gf_name.bin",
        "/data/product/d3/model/mdl_gf_number.bin",
        "/data/product/d3/model/mdl_gf_pass.bin",
        "/data/product/d3/model/mdl_gf_playdata.bin",
        "/data/product/d3/model/mdl_gf_result.bin",
        "/data/product/d3/model/mdl_gf_select_mode.bin",
        "/data/product/d3/model/mdl_gf_select_music.bin",
        "/data/product/d3/model/mdl_gf_skill_meter.bin",
        "/data/product/d3/model/mdl_gf_taikai.bin",
        "/data/product/d3/model/mdl_gf_title.bin",
        "/data/product/d3/model/mdl_gf_warning.bin",
        "/data/product/d3/model/mdl_sp_shop_cmpship.bin",
        "/data/product/d3/model/mdl_sp_shop_cmpship_rank.bin",
        "/data/product/d3/model/mdl_sp_shop_entry.bin",
        "/data/product/d3/model/mdl_sp_shop_taikai.bin",
        "/data/product/d3/model/mdl_sp_shop_taikai_rank.bin",
        "/data/product/d3/model/mdl_testmode.bin",
        "/data/product/d3/model/mdl_test_group.bin",
        "/data/product/d3/model/tex_attack_effect.bin",
        "/data/product/d3/model/tex_cm_customicon.bin",
        "/data/product/d3/model/tex_cm_custom_icon.bin",
        "/data/product/d3/model/tex_cm_event_logo.bin",
        "/data/product/d3/model/tex_cm_group.bin",
        "/data/product/d3/model/tex_cm_groupicon.bin",
        "/data/product/d3/model/tex_cm_group_common.bin",
        "/data/product/d3/model/tex_cm_group_entry.bin",
        "/data/product/d3/model/tex_cm_group_icon.bin",
        "/data/product/d3/model/tex_cm_group_match.bin",
        "/data/product/d3/model/tex_cm_item_icon.bin",
        "/data/product/d3/model/tex_cm_paseli.bin",
        "/data/product/d3/model/tex_cm_transition.bin",
        "/data/product/d3/model/tex_cm_vtleff_bg.bin",
        "/data/product/d3/model/tex_cm_vtleff_fg.bin",
        "/data/product/d3/model/tex_cm_vtleff_mg.bin",
        "/data/product/d3/model/tex_com_transition.bin",
        "/data/product/d3/model/tex_dm_game.bin",
        "/data/product/d3/model/tex_gd_gam_lp.bin",
        "/data/product/d3/model/tex_gfdm_transition.bin",
        "/data/product/d3/model/tex_gf_ability.bin",
        "/data/product/d3/model/tex_gf_ascii.bin",
        "/data/product/d3/model/tex_gf_battle.bin",
        "/data/product/d3/model/tex_gf_battle_common.bin",
        "/data/product/d3/model/tex_gf_battle_matching.bin",
        "/data/product/d3/model/tex_gf_battle_result.bin",
        "/data/product/d3/model/tex_gf_caution.bin",
        "/data/product/d3/model/tex_gf_chara.bin",
        "/data/product/d3/model/tex_gf_common.bin",
        "/data/product/d3/model/tex_gf_custom.bin",
        "/data/product/d3/model/tex_gf_eamuse.bin",
        "/data/product/d3/model/tex_gf_ending.bin",
        "/data/product/d3/model/tex_gf_game.bin",
        "/data/product/d3/model/tex_gf_hitchart.bin",
        "/data/product/d3/model/tex_gf_how.bin",
        "/data/product/d3/model/tex_gf_howdm.bin",
        "/data/product/d3/model/tex_gf_howgf.bin",
        "/data/product/d3/model/tex_gf_information.bin",
        "/data/product/d3/model/tex_gf_name.bin",
        "/data/product/d3/model/tex_gf_number.bin",
        "/data/product/d3/model/tex_gf_pass.bin",
        "/data/product/d3/model/tex_gf_playdata.bin",
        "/data/product/d3/model/tex_gf_result.bin",
        "/data/product/d3/model/tex_gf_select_mode.bin",
        "/data/product/d3/model/tex_gf_select_music.bin",
        "/data/product/d3/model/tex_gf_skill_meter.bin",
        "/data/product/d3/model/tex_gf_taikai.bin",
        "/data/product/d3/model/tex_gf_title.bin",
        "/data/product/d3/model/tex_gf_warning.bin",
        "/data/product/d3/model/tex_sp_shop_cmpship.bin",
        "/data/product/d3/model/tex_sp_shop_cmpship_rank.bin",
        "/data/product/d3/model/tex_sp_shop_entry.bin",
        "/data/product/d3/model/tex_sp_shop_taikai.bin",
        "/data/product/d3/model/tex_sp_shop_taikai_rank.bin",
        "/data/product/d3/model/tex_testmode.bin",
        "/data/product/d3/model/tex_test_group.bin",

        "/data/product/d3/model/mdl_gf_index_shougou.bin",
        "/data/product/d3/model/tex_gf_index_shougou.bin",
        "/data/product/d3/model/mdl_gf_icon.bin",
        "/data/product/d3/model/tex_gf_icon.bin",
        "/data/product/d3/model/mdl_gf_chara.bin",
        "/data/product/d3/model/tex_gf_chara.bin",
        "/data/product/d3/model/mdl_gf_ascii.bin",
        "/data/product/d3/model/tex_gf_ascii.bin",
        "/data/product/d3/model/mdl_gf_idi.bin",
        "/data/product/d3/model/tex_gf_idi.bin",
        "/data/product/d3/model/mdl_gf_quest.bin",
        "/data/product/d3/model/tex_gf_quest.bin",
        "/data/product/d3/model/mdl_gf_quest_common.bin",
        "/data/product/d3/model/tex_gf_quest_common.bin",
        "/data/product/d3/model/mdl_gf_select_item.bin",
        "/data/product/d3/model/tex_gf_select_item.bin",
        "/data/product/d3/model/mdl_gf_select_grandprix.bin",
        "/data/product/d3/model/tex_gf_select_grandprix.bin",
        "/data/product/d3/model/mdl_gf_result_grandprix.bin",
        "/data/product/d3/model/tex_gf_result_grandprix.bin",
        "/data/product/d3/model/mdl_gf_bg.bin",
        "/data/product/d3/model/tex_gf_bg.bin",

        "/data/product/aep/gf_index_shougou.bin",
        "/data/product/aep/gf_icon.bin",
        "/data/product/aep/gf_chara.bin",
        "/data/product/aep/gf_ascii.bin",
        "/data/product/aep/gf_idi.bin",
        "/data/product/aep/gf_quest.bin",
        "/data/product/aep/gf_quest_common.bin",
        "/data/product/aep/gf_select_item.bin",
        "/data/product/aep/gf_select_grandprix.bin",
        "/data/product/aep/gf_result_grandprix.bin",
        "/data/product/aep/gf_bg.bin",

        "/data/product/aep/gf_debug.bin",
        "/data/product/d3/model/mdl_gf_debug.bin",
        "/data/product/d3/model/tex_gf_debug.bin",

        "/data/product/music/test/system.va3",
        "/data/product/music/test/se.va3",
        "/data/product/music/test/haruhi.bgm",

        "/data/product/aep/gf_battle_event.bin",
        "/data/product/d3/model/mdl_gf_battle_event.bin",
        "/data/product/d3/model/tex_gf_battle_event.bin",
    ]

    system_audio_parts = [
        "volume",
        "phase",
        "scale",
        "V6CM03",
        "V6CM02",
        "V6CM01",
        "p_custom",
        "q_result",
        "q_select",
        "battle_result",
        "battle02",
        "battle01",
        "result_total",
        "volume_check",
        "phase_check",
        "scale_check",
        "jukebox",
        "information",
        "b_result",
        "battle",
        "b_info",
        "playdata",
        "session",
        "select",
        "result",
        "ranking",
        "clear",
        "konami",
        "title",
        "entry",
        "xg_logo",
        "xg2_thankyou",
        "xg2_result",
        "xg2_entry",
        "v8_logo",
        "v8_thankyou",
        "v8_result",
        "v8_entry",
    ]

    for system_audio_part in system_audio_parts:
        for ext in ['bin', 'va2', 'va3', 'pss']:
            for game in ['_gf', '_dm', '']:
                path = "/data/product/music/system/%s%s.%s" % (system_audio_part, game, ext)
                possible_filenames.append(path)

    for path in possible_filenames:
        if dumper.file_exists(path):
            filenames.append(path)

    filenames = list(set(filenames))

    if "/data/product/d3/package/packlist.bin" in filenames:
        data = dumper.extract_data_mem("/data/product/d3/package/packlist.bin")

        if data[:4] == b"TSLF":
            offset = int.from_bytes(data[0x14:0x18], 'little')
            first_offset = int.from_bytes(data[offset:offset+4], 'little')

        else:
            offset = int.from_bytes(data[0x1c:0x20], 'little')
            first_offset = int.from_bytes(data[offset:offset+4], 'little')

        offsets = [x for x in [int.from_bytes(data[offset+idx:offset+idx+4], 'little') for idx in range(0, first_offset - offset, 4)] if x != 0]

        for offset in offsets:
            string = data[offset:offset+data[offset:].index(b'\0')].decode('ascii').strip('\0')
            path = "/data/product/d3/package/%s" % (string)

            if dumper.file_exists(path):
                filenames.append(path)

    if "/data/product/aep/gf_aep_list.bin" in filenames:
        data = dumper.extract_data_mem("/data/product/aep/gf_aep_list.bin")

        for offset in range(0, len(data), 0x20):
            string = data[offset:offset+data[offset:].index(b'\0')].decode('ascii').strip('\0')
            path = "/data/product/aep/%s.bin" % (string)

            if dumper.file_exists(path):
                filenames.append(path)

            path = "/data/product/d3/model/mdl_%s.bin" % (string)

            if dumper.file_exists(path):
                filenames.append(path)

            path = "/data/product/d3/model/tex_%s.bin" % (string)

            if dumper.file_exists(path):
                filenames.append(path)


    templates = [
        "/data/product/music/m%04d/event%04d.evt",

        "/data/product/music/m%04d/d%04d.sq2",
        "/data/product/music/m%04d/g%04d.sq2",

        "/data/product/music/m%04d/d%04d.sq3",
        "/data/product/music/m%04d/g%04d.sq3",

        "/data/product/music/m%04d/d%04d.seq",
        "/data/product/music/m%04d/g%04d.seq",

        "/data/product/music/m%04d/spu%04dd.vas",
        "/data/product/music/m%04d/spu%04dg.vas",
        "/data/product/music/m%04d/spu%04dd.va2",
        "/data/product/music/m%04d/spu%04dg.va2",
        "/data/product/music/m%04d/spu%04dd.va3",
        "/data/product/music/m%04d/spu%04dg.va3",
        "/data/product/music/m%04d/spu%04dd.pss",
        "/data/product/music/m%04d/spu%04dg.pss",

        "/data/product/music/m%04d/fre%04d.bin",

        "/data/product/music/m%04d/bgm%04d.mpg",
        "/data/product/music/m%04d/bgm%04d.m2v",
        "/data/product/music/m%04d/bgm%04d.pss",
        "/data/product/music/m%04d/m%04d.mpg",
        "/data/product/music/m%04d/m%04d.m2v",
        "/data/product/music/m%04d/m%04d.pss",

        "/data/product/music/m%04d/i%04ddm.bin",
        "/data/product/music/m%04d/i%04dgf.bin",
        "/data/product/music/m%04d/i%04ddm.at3",
        "/data/product/music/m%04d/i%04dgf.at3",
        "/data/product/music/m%04d/i%04ddm.pss",
        "/data/product/music/m%04d/i%04dgf.pss",

        "/data/product/movie/music/mv%04d.m2v",
        "/data/product/movie/thema/tm%04ds.m2v",
        "/data/product/movie/thema/tm%04d.m2v",
        "/data/product/movie/music/mv%04d.pss",
        "/data/product/movie/thema/tm%04ds.pss",
        "/data/product/movie/thema/tm%04d.pss",
        "/data/product/movie/music/mv%04d.mpg",
        "/data/product/movie/thema/tm%04ds.mpg",
        "/data/product/movie/thema/tm%04d.mpg",
    ]

    valid_t = [t for t in ["".join(i) for i in itertools.product('_gdbk', repeat = 4)] if t[0] in ['_', 'd'] and t[1] in ['_', 'g'] and t[2] in ['_', 'b'] and t[3] in ['_', 'k']]
    for t in sorted(valid_t):
        for ext in ['bin', 'at3']:
            templates.append("/data/product/music/m%04d/bgm%04d" + t + "_xg." + ext)
            templates.append("/data/product/music/m%04d/b%04d" + t + "_xg." + ext)
            templates.append("/data/product/music/m%04d/bgm%04d" + t + "." + ext)
            templates.append("/data/product/music/m%04d/b%04d" + t + "." + ext)

    for i in range(0, 9999):
        for template in templates:
            path = template % tuple(i for _ in range(template.count("%04d")))

            if dumper.file_exists(path):
                filenames.append(path)

        for j in range(0, 10):
            for path in ["/data/product/music/m%04d/dm_lesson%01d.va2" % (i, j), "/data/product/music/m%04d/gt_lesson%01d.va2" % (i, j)]:
                if dumper.file_exists(path):
                    filenames.append(path)

    templates = [
        "/data/product/aep/gf_int_%03d.bin",
        "/data/product/d3/model/mdl_gf_int_%03d.bin",
        "/data/product/d3/model/tex_gf_int_%03d.bin",
        "/data/product/d3/package/pack%03d.bin",
        "/data/product/aep/gf_int_%03d.bin",
    ]

    for i in range(0, 1000):
        for template in templates:
            path = template % tuple(i for _ in range(template.count("%03d")))

            if dumper.file_exists(path):
                filenames.append(path)

    templates = [
        "/data/product/d3/model/mdl_gf_idx_image_%02d.bin",
        "/data/product/d3/model/mdl_gf_idx_image%02d.bin",
        "/data/product/d3/model/mdl_gf_index_name%02d.bin",
        "/data/product/d3/model/mdl_gf_jac_image_%02d.bin",
        "/data/product/d3/model/mdl_gf_game%02d.bin",
        "/data/product/d3/model/mdl_dm_game%02d.bin",

        "/data/product/d3/model/tex_gf_idx_image_%02d.bin",
        "/data/product/d3/model/tex_gf_idx_image%02d.bin",
        "/data/product/d3/model/tex_gf_index_name%02d.bin",
        "/data/product/d3/model/tex_gf_jac_image_%02d.bin",
        "/data/product/d3/model/tex_gf_game%02d.bin",
        "/data/product/d3/model/tex_dm_game%02d.bin",

        "/data/product/music/system/system%02d.m2v",
        "/data/product/movie/system/title%02d.m2v",
        "/data/product/movie/system/select_music%02d.m2v",
        "/data/product/movie/system/logo_xg%02d.m2v",
        "/data/product/movie/system/select_mode%02d.m2v",
        "/data/product/movie/system/select_music_enc%02d.m2v",
        "/data/product/movie/system/ending%02d.m2v",
        "/data/product/movie/system/jukebox%02d.m2v",
        "/data/product/movie/system/records%02d.m2v",
        "/data/product/movie/system/result%02d.m2v",
        "/data/product/movie/system/select_mode%02d.m2v",
        "/data/product/movie/system/entry%02d.m2v",

        "/data/product/d3/model/mdl_cm_common%02d.bin",
        "/data/product/d3/model/mdl_sp_game_skin%02d.bin",
        "/data/product/d3/model/mdl_sp_gf_atkf%02d.bin",
        "/data/product/d3/model/mdl_sp_ggm_ef%02d.bin",

        "/data/product/d3/model/tex_cm_common%02d.bin",
        "/data/product/d3/model/tex_sp_game_skin%02d.bin",
        "/data/product/d3/model/tex_sp_gf_atkf%02d.bin",
        "/data/product/d3/model/tex_sp_ggm_ef%02d.bin",

        "/data/product/aep/cm_common%02d.bin",
        "/data/product/aep/dm_game%02d.bin",
        "/data/product/aep/gf_game%02d.bin",
        "/data/product/aep/sp_gf_atkf%02d.bin",
        "/data/product/aep/sp_ggm_ef%02d.bin",
        "/data/product/aep/sp_ggm_efbg%02d.bin",
        "/data/product/aep/sp_ggm_eflane%02d.bin",
    ]

    for i in range(0, 100):
        for template in templates:
            path = template % tuple(i for _ in range(template.count("%02d")))

            if dumper.file_exists(path):
                filenames.append(path)

    templates = [
        "/data/product/d3/model/mdl_gf_game%01d.bin",
        "/data/product/d3/model/mdl_dm_game%01d.bin",
        "/data/product/d3/model/mdl_gf_battle_common%01d.bin",

        "/data/product/d3/model/tex_gf_game%01d.bin",
        "/data/product/d3/model/tex_dm_game%01d.bin",
        "/data/product/d3/model/tex_gf_battle_common%01d.bin",
    ]

    for i in range(0, 10):
        for template in templates:
            path = template % tuple(i for _ in range(template.count("%01d")))

            if dumper.file_exists(path):
                filenames.append(path)

    for i in range(0, 100):
        for j in range(0, 100):
            for ext in ['va2', 'va3']:
                paths = [
                    "/data/product/music/system/gfv%d_v%02d.%s" % (i, j, ext),
                    "/data/product/music/system/gf%d_v%02d.%s" % (i, j, ext),
                    "/data/product/music/system/gfxg%d_v%02d.%s" % (i, j, ext),
                    "/data/product/music/system/dmv%d_v%02d.%s" % (i, j, ext),
                    "/data/product/music/system/dm%d_v%02d.%s" % (i, j, ext),
                    "/data/product/music/system/dmxg%d_v%02d.%s" % (i, j, ext),
                ]

                for path in paths:
                    if dumper.file_exists(path):
                        filenames.append(path)

        for ext in ['va2', 'va3']:
            paths = [
                "/data/product/music/system/gfv%d_se.%s" % (i, ext),
                "/data/product/music/system/gfv_v%02d.%s" % (i, ext),
                "/data/product/music/system/gf%d_se.%s" % (i, ext),
                "/data/product/music/system/gf_v%02d.%s" % (i, ext),
                "/data/product/music/system/gfxg%d_se.%s" % (i, ext),
                "/data/product/music/system/gfxg_v%02d.%s" % (i, ext),
                "/data/product/music/system/dmv%d_se.%s" % (i, ext),
                "/data/product/music/system/dmv_v%02d.%s" % (i, ext),
                "/data/product/music/system/dm%d_se.%s" % (i, ext),
                "/data/product/music/system/dm_v%02d.%s" % (i, ext),
                "/data/product/music/system/dmxg%d_se.%s" % (i, ext),
                "/data/product/music/system/dmxg_v%02d.%s" % (i, ext),
            ]

            for path in paths:
                if dumper.file_exists(path):
                    filenames.append(path)

    for filename in filenames:
        if "gf_" in filename:
            new_filename = filename.replace("gf_", "dm_")

            if new_filename not in filenames and dumper.file_exists(new_filename):
                filenames.append(new_filename)

        elif "dm_" in filename:
            new_filename = filename.replace("dm_", "gf_")

            if new_filename not in filenames and dumper.file_exists(new_filename):
                filenames.append(new_filename)

        elif "_gf" in filename:
            new_filename = filename.replace("_gf", "_dm")

            if new_filename not in filenames and dumper.file_exists(new_filename):
                filenames.append(new_filename)

        elif "_dm" in filename:
            new_filename = filename.replace("_dm", "_gf")

            if new_filename not in filenames and dumper.file_exists(new_filename):
                filenames.append(new_filename)

        elif "tex_" in filename:
            new_filename = filename.replace("tex_", "mdl_")

            if new_filename not in filenames and dumper.file_exists(new_filename):
                filenames.append(new_filename)

            new_filename = filename.replace("d3/model/tex_", "aep/")

            if new_filename not in filenames and dumper.file_exists(new_filename):
                filenames.append(new_filename)

        elif "mdl_" in filename:
            new_filename = filename.replace("mdl_", "tex_")

            if new_filename not in filenames and dumper.file_exists(new_filename):
                filenames.append(new_filename)

            new_filename = filename.replace("d3/model/mdl_", "aep/")

            if new_filename not in filenames and dumper.file_exists(new_filename):
                filenames.append(new_filename)

    return filenames


def find_packinfo(path):
    packinfo_paths = glob.glob(os.path.join(path, "**", "packinfo.bin"), recursive=True)

    if packinfo_paths:
        # Shouldn't ever really have more than one packinfo.bin in a normal setup...
        # But my setup is a mess so yeah
        return packinfo_paths[-1]

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input folder', required=True)
    parser.add_argument('-o', '--output', help='Output folder (optional)', default="output")
    parser.add_argument('-d', '--demux', help='Demux PSS files', default=False, action="store_true")
    parser.add_argument('-f', '--fast', help='Use Cython decryption code', default=False, action="store_true")

    args = parser.parse_args()

    packinfo_path = find_packinfo(args.input)

    if not packinfo_path:
        print("Couldn't find packinfo.bin in input directory")
        exit(1)

    dumper = PakDumper(packinfo_path, args.demux, args.fast)

    filenames = bruteforce_filenames(dumper)

    sorted_keys = sorted(dumper.entries, key=lambda x:(dumper.entries[x].get('packid', 0), dumper.entries[x].get('offset', 0)))

    named = 0

    for k in sorted_keys:
        if 'orig_filename' in dumper.entries[k]:
            print("%-64s packid[%04d] offset[%08x] filesize[%08x] hash[%08x]" % (dumper.entries[k]['orig_filename'], dumper.entries[k]['packid'], dumper.entries[k]['offset'], dumper.entries[k]['filesize'], k))
            dumper.extract_data(dumper.entries[k]['orig_filename'], args.input, args.output)
            named += 1

        else:
            # print("Dumping %08x.bin" % k)

            data = dumper.extract_data_mem(None, args.input, k)

            output_path = os.path.join(args.output, "unknown")
            os.makedirs(output_path, exist_ok=True)

            output_filename = os.path.join(output_path, "%08x.bin" % k)
            print("Dumping", output_filename)
            open(output_filename, "wb").write(data)

    print("Named: %d" % (named))
    print("Unnamed: %d" % (len(sorted_keys) - named))
    print("Total: %d" % (len(sorted_keys)))