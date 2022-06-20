import argparse
import os


def decompress_tm2c(data):
    # 001724d0 in SLUS_216.08 from PS2 DDR SN2 US
    assert(data[0:4] == b"TGCD")

    decompress_size = int.from_bytes(data[0x04:0x08], 'little')
    data_end_offset = int.from_bytes(data[0x08:0x0c], 'little')
    data_checksum = int.from_bytes(data[0x1c:0x20], 'little')

    # The game is programmed to check that these values are a specific hardcoded value,
    # but I'm pretty sure these should control lookback buffer size and such
    comp_param_unk1 = int.from_bytes(data[0x0c:0x10], 'little')
    comp_param_unk2 = int.from_bytes(data[0x10:0x14], 'little')
    comp_param_unk3 = int.from_bytes(data[0x14:0x18], 'little')
    comp_param_unk4 = int.from_bytes(data[0x18:0x1c], 'little')

    calculated_checksum = sum(data[0x20:])
    assert(data_checksum == calculated_checksum)

    # 001889c0 in SLUS_216.08 from PS2 DDR SN2 US
    # This verification function checks with hardcoded values
    assert(data[0:4] == b"TGCD")
    assert(decompress_size > 0)
    assert(data_end_offset >= 0x20)
    assert(comp_param_unk1 == 0x7fff)
    assert(comp_param_unk2 == 0xffff)
    assert(comp_param_unk3 == 0xff)
    assert(comp_param_unk4 == 0x8000)

    output = bytearray()
    if decompress_size <= 0:
        return output

    idx = 0x20
    while idx < data_end_offset:
        cmd_bits = int.from_bytes(data[idx:idx+2], 'little')
        idx += 2

        if (cmd_bits & 0x8000) == 0:
            output_len = len(output)
            lookback_offset = 0

            if output_len >= 0x7fff:
                lookback_offset = output_len - 0x7fff

            lookback_offset += int.from_bytes(data[idx-2:idx], 'little')
            copy_len = data[idx]
            last_byte = data[idx+1]
            idx += 2

            for j in range(copy_len):
                output.append(output[lookback_offset+j])

            output.append(last_byte)

        else:
            l = int.from_bytes(data[idx:idx+2], 'little')
            idx += 2

            output += data[idx:idx+l]
            idx += l

            if (l & 0xf) != 0:
                # Why would they pad blocks in a compressed file???
                idx += 0x10 - (l & 0xf)

    return output


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', help='Input file', required=True)
    parser.add_argument('-o', '--output', help='Output file', default=None)

    args = parser.parse_args()

    input_filename = args.input
    output_filename = args.output

    if output_filename is None:
        output_filename = os.path.splitext(input_filename)[0] + ".tm2"

    data = bytearray(open(input_filename, "rb").read())
    decompressed = decompress_tm2c(data)

    print("Decompressed", input_filename)

    open(output_filename, "wb").write(decompressed)


if __name__ == "__main__":
    main()
