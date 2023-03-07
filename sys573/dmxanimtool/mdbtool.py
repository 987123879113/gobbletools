import argparse


def parse_mdb(mdb_path):
    def get_fixed_title(title):
        return {
            "@ (J-SUMMER MIX)": "祭 (J-SUMMER MIX)",
            "% Odoru Ponpokorin": "おどるポンポコリン",
            "% Romance no Kamisama": "ロマンスの神様",
            "% Junanasai": "17才",
        }.get(title, title)

    def read_string(data, start):
        return data[start:data.index(b'\0', start)].decode('cp932').replace('|', ' ').replace('  ', ' ')

    def read_all_string(data):
        return [c.decode('cp932').replace('|', ' ').replace('  ', ' ') for c in data.split(b'\0')]

    mdb_data = bytearray(open(mdb_path, "rb").read())
    data_start = int.from_bytes(mdb_data[0:4], 'little')
    entries_len = int.from_bytes(mdb_data[4:8], 'little')
    titles_len = int.from_bytes(mdb_data[8:12], 'little')
    artists_len = int.from_bytes(mdb_data[12:16], 'little')

    titles = mdb_data[data_start+entries_len:data_start+entries_len+titles_len]
    artists = read_all_string(mdb_data[data_start+entries_len +
                              titles_len:data_start+entries_len+titles_len+artists_len])

    entries = {}
    for offset in range(data_start, data_start + entries_len, 0x24):
        cur_idx = offset // 0x24
        entry = mdb_data[offset:offset+0x24]

        song_id = entry[:6].decode('ascii').strip('\0').strip().lower()
        title_full_offset = int.from_bytes(entry[0x1c:0x20], 'little')
        title_short_offset = int.from_bytes(entry[0x20:0x24], 'little')
        diff_sp_mild = (entry[0x17] >> 4) & 0x0f
        diff_sp_wild = entry[0x17] & 0x0f
        diff_dp_mild = entry[0x16] & 0x0f
        diff_dp_wild = (entry[0x15] >> 4) & 0x0f
        bpm = int.from_bytes(entry[0x10:0x12], 'little', signed=True)
        mp3_full_id = int.from_bytes(entry[0x08:0x0a], 'little')
        mp3_preview_id = int.from_bytes(entry[0x0a:0x0c], 'little')
        artist_id = int.from_bytes(entry[0x0c:0x0e], 'little')

        if not song_id:
            break

        assert (song_id not in entries)

        entries[song_id] = {
            'id': cur_idx,
            'song_id': song_id,
            'artist': artists[artist_id-1] if artist_id > 0 and artist_id < len(artists) else "",
            'title_full': get_fixed_title(read_string(titles, title_full_offset)),
            'title_short': get_fixed_title(read_string(titles, title_short_offset)),
            'bpm': bpm,
            'diffs': {
                'sp_mild': diff_sp_mild,
                'sp_wild': diff_sp_wild,
                'dp_mild': diff_dp_mild,
                'dp_wild': diff_dp_wild,
            },
            'mp3_full_id': mp3_full_id,
            'mp3_preview_id': mp3_preview_id,
        }

    return entries


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input_mdb_path')
    parser.add_argument('-s', '--short', help="Short output", default=False, action="store_true")

    args = parser.parse_args()

    mdb = parse_mdb(args.input_mdb_path)
    for k in sorted(mdb, key=lambda x: mdb[x]['id']):
        entry = mdb[k]

        if args.short:
            print("%-5s | %s (%s)" %
                  (entry['song_id'], " - ".join([x for x in [entry['artist'], entry['title_full']] if x]), entry['title_short']))

        else:
            print("%s" % entry['song_id'])
            print("\tArtist: %s" % entry['artist'])
            print("\tTitle: %s" % entry['title_full'])
            print("\tTitle (Short): %s" % entry['title_short'])
            print("\tBPM: %d" % (entry['bpm']))
            print("\tDiffs SP[%d %d] DP[%d %d]" % (entry['diffs']['sp_mild'], entry['diffs']
                  ['sp_wild'], entry['diffs']['dp_mild'], entry['diffs']['dp_wild']))
            print()
