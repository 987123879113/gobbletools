import argparse

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


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--input', help='Input GAME.DAT', required=False, default="GAME.DAT")
    parser.add_argument('--output', help='Output file', required=False, default="config.txt")
    parser.add_argument('--insert', help='Input configuration text into output file', default=False, action='store_true')

    args = parser.parse_args()

    if args.insert:
        # Insert into GAME.DAT
        config = decrypt_data_internal(bytearray(open("config.txt", "rb").read()), "/s573/config.dat")
        import hexdump
        hexdump.hexdump(config)

        open("config.dat", "wb").write(config)

    else:
        # Extract from GAME.DAT
        data = bytearray(open(args.input, "rb").read())[0x1fc4 * 0x800:0x1fc4 * 0x800 + 0x7f6]
        config = decrypt_data_internal(data, "/s573/config.dat")
        open(args.output, "wb").write(config)

        try:
            print(config.decode('cp932'))
        except:
            pass


if __name__ == "__main__":
    main()

