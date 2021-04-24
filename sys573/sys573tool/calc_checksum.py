import argparse
import os

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


def verify_checksums(cards):
    card_sizes = [len(x) // 0x8000 for x in cards]

    chunk_size = 0x20000
    last_chunk_offset = len(cards[0]) - chunk_size
    last_chunk_checksum_offset = last_chunk_offset + 0x10

    checksums = [int.from_bytes(cards[0][last_chunk_checksum_offset+x:last_chunk_checksum_offset+x+4], 'little') for x in range(0, 0x2000, 4)]

    is_valid = True
    for real_card_index, card_data in enumerate(cards):
        for i in range(0, len(card_data) // chunk_size):
            offset = (i * chunk_size) + (0x20 if real_card_index == 0 and i == 0 else 0)
            length = chunk_size - (0x20 if real_card_index == 0 and i == 0 else 0)
            checksum_bytes = int.from_bytes(sum573.checksum_chunk(card_data, offset, length), 'little')

            target_checksum = checksums[i + (sum(card_sizes[:real_card_index]) // 4)]
            if checksum_bytes != target_checksum:
                print("Sector %d of DAT %d is invalid! %08x vs %08x" % (i, real_card_index, checksum_bytes, target_checksum))
                is_valid = False

    return is_valid


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--input', help='Input DAT file (list all in order)', nargs='+', required=True)
    parser.add_argument('--output', help='Output folder', default="output")

    args, _ = parser.parse_known_args()

    cards = [bytearray(open(x, "rb").read()) for x in args.input]

    for x in args.input:
        print(x)

    is_valid = verify_checksums(cards)
    print("Is checksum table valid?", is_valid)

    if not is_valid:
        rebuild_checksum_table(cards)

        is_valid = verify_checksums(cards)
        print("Is checksum table valid?", is_valid)

        os.makedirs(args.output, exist_ok=True)
        for i, x in enumerate(args.input):
            open(os.path.join(args.output, os.path.basename(x)), "wb").write(cards[i])


if __name__ == "__main__":
    main()
