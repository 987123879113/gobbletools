# Error correction code shamelessly stolen from jPSXdec (https://github.com/m35/jpsxdec/)
import argparse
import os
import sys

EDC_crctable = [
    0x00000000, 0x90910101, 0x91210201, 0x01B00300, 0x92410401, 0x02D00500, 0x03600600, 0x93F10701,
    0x94810801, 0x04100900, 0x05A00A00, 0x95310B01, 0x06C00C00, 0x96510D01, 0x97E10E01, 0x07700F00,
    0x99011001, 0x09901100, 0x08201600, 0x98B11301, 0x0B401400, 0x9BD11501, 0x9A611601, 0x0AF01700,
    0x0D801800, 0x9D111901, 0x9CA11A01, 0x0C301B00, 0x9FC11C01, 0x0F501D00, 0x0EE01E00, 0x9E711F01,
    0x82016001, 0x12902100, 0x13202200, 0x83B12301, 0x10402400, 0x80D12501, 0x81612601, 0x11F02700,
    0x16802800, 0x86112901, 0x87A12A01, 0x17302B00, 0x84C12C01, 0x14502D00, 0x15E02E00, 0x85712F01,
    0x1B003000, 0x8B913101, 0x8A213201, 0x1AB03300, 0x89413401, 0x19D03500, 0x18603600, 0x88F13701,
    0x8F813801, 0x1F103900, 0x1EA03A00, 0x8E313B01, 0x1DC03C00, 0x8D513D01, 0x8CE13E01, 0x1C703F00,
    0xB4014001, 0x24904100, 0x25204200, 0xB5B14301, 0x26404400, 0xB6D14501, 0xB7614601, 0x27F04700,
    0x20804800, 0xB0114901, 0xB1A14A01, 0x21304B00, 0xB2C14C01, 0x22504D00, 0x23E04E00, 0xB3714F01,
    0x2D005000, 0xBD915101, 0xBC215201, 0x2CB05300, 0xBF415401, 0x2FD05500, 0x2E605600, 0xBEF15701,
    0xB9815801, 0x29105900, 0x28A05A00, 0xB8315B01, 0x2BC05C00, 0xBB515D01, 0xBAE15E01, 0x2A705F00,
    0x36006000, 0xA6916101, 0xA7216201, 0x37B06300, 0xA4416401, 0x34D06500, 0x35606600, 0xA5F16701,
    0xA2816801, 0x32106900, 0x33A06A00, 0xA3316B01, 0x30C06C00, 0xA0516D01, 0xA1E16E01, 0x31706F00,
    0xAF017001, 0x3F907100, 0x3E207200, 0xAEB17301, 0x3D407400, 0xADD17501, 0xAC617601, 0x3CF07700,
    0x3B807800, 0xAB117901, 0xAAA17A01, 0x3A307B00, 0xA9C17C01, 0x39507D00, 0x38E07E00, 0xA8717F01,
    0xD8018001, 0x48908100, 0x49208200, 0xD9B18301, 0x4A408400, 0xDAD18501, 0xDB618601, 0x4BF08700,
    0x4C808800, 0xDC118901, 0xDDA18A01, 0x4D308B00, 0xDEC18C01, 0x4E508D00, 0x4FE08E00, 0xDF718F01,
    0x41009000, 0xD1919101, 0xD0219201, 0x40B09300, 0xD3419401, 0x43D09500, 0x42609600, 0xD2F19701,
    0xD5819801, 0x45109900, 0x44A09A00, 0xD4319B01, 0x47C09C00, 0xD7519D01, 0xD6E19E01, 0x46709F00,
    0x5A00A000, 0xCA91A101, 0xCB21A201, 0x5BB0A300, 0xC841A401, 0x58D0A500, 0x5960A600, 0xC9F1A701,
    0xCE81A801, 0x5E10A900, 0x5FA0AA00, 0xCF31AB01, 0x5CC0AC00, 0xCC51AD01, 0xCDE1AE01, 0x5D70AF00,
    0xC301B001, 0x5390B100, 0x5220B200, 0xC2B1B301, 0x5140B400, 0xC1D1B501, 0xC061B601, 0x50F0B700,
    0x5780B800, 0xC711B901, 0xC6A1BA01, 0x5630BB00, 0xC5C1BC01, 0x5550BD00, 0x54E0BE00, 0xC471BF01,
    0x6C00C000, 0xFC91C101, 0xFD21C201, 0x6DB0C300, 0xFE41C401, 0x6ED0C500, 0x6F60C600, 0xFFF1C701,
    0xF881C801, 0x6810C900, 0x69A0CA00, 0xF931CB01, 0x6AC0CC00, 0xFA51CD01, 0xFBE1CE01, 0x6B70CF00,
    0xF501D001, 0x6590D100, 0x6420D200, 0xF4B1D301, 0x6740D400, 0xF7D1D501, 0xF661D601, 0x66F0D700,
    0x6180D800, 0xF111D901, 0xF0A1DA01, 0x6030DB00, 0xF3C1DC01, 0x6350DD00, 0x62E0DE00, 0xF271DF01,
    0xEE01E001, 0x7E90E100, 0x7F20E200, 0xEFB1E301, 0x7C40E400, 0xECD1E501, 0xED61E601, 0x7DF0E700,
    0x7A80E800, 0xEA11E901, 0xEBA1EA01, 0x7B30EB00, 0xE8C1EC01, 0x7850ED00, 0x79E0EE00, 0xE971EF01,
    0x7700F000, 0xE791F101, 0xE621F201, 0x76B0F300, 0xE541F401, 0x75D0F500, 0x7460F600, 0xE4F1F701,
    0xE381F801, 0x7310F900, 0x72A0FA00, 0xE231FB01, 0x71C0FC00, 0xE151FD01, 0xE0E1FE01, 0x7070FF00,
]

rs_l12_log = [
      0,   0,   1,  25,   2,  50,  26, 198,   3, 223,  51, 238,  27, 104, 199,  75,
      4, 100, 224,  14,  52, 141, 239, 129,  28, 193, 105, 248, 200,   8,  76, 113,
      5, 138, 101,  47, 225,  36,  15,  33,  53, 147, 142, 218, 240,  18, 130,  69,
     29, 181, 194, 125, 106,  39, 249, 185, 201, 154,   9, 120,  77, 228, 114, 166,
      6, 191, 139,  98, 102, 221,  48, 253, 226, 152,  37, 179,  16, 145,  34, 136,
     54, 208, 148, 206, 143, 150, 219, 189, 241, 210,  19,  92, 131,  56,  70,  64,
     30,  66, 182, 163, 195,  72, 126, 110, 107,  58,  40,  84, 250, 133, 186,  61,
    202,  94, 155, 159,  10,  21, 121,  43,  78, 212, 229, 172, 115, 243, 167,  87,
      7, 112, 192, 247, 140, 128,  99,  13, 103,  74, 222, 237,  49, 197, 254,  24,
    227, 165, 153, 119,  38, 184, 180, 124,  17,  68, 146, 217,  35,  32, 137,  46,
     55,  63, 209,  91, 149, 188, 207, 205, 144, 135, 151, 178, 220, 252, 190,  97,
    242,  86, 211, 171,  20,  42,  93, 158, 132,  60,  57,  83,  71, 109,  65, 162,
     31,  45,  67, 216, 183, 123, 164, 118, 196,  23,  73, 236, 127,  12, 111, 246,
    108, 161,  59,  82,  41, 157,  85, 170, 251,  96, 134, 177, 187, 204,  62,  90,
    203,  89,  95, 176, 156, 169, 160,  81,  11, 245,  22, 235, 122, 117,  44, 215,
     79, 174, 213, 233, 230, 231, 173, 232, 116, 214, 244, 234, 168,  80,  88, 175,
]

rs_l12_alog = [
      1,   2,   4,   8,  16,  32,  64, 128,  29,  58, 116, 232, 205, 135,  19,  38,
     76, 152,  45,  90, 180, 117, 234, 201, 143,   3,   6,  12,  24,  48,  96, 192,
    157,  39,  78, 156,  37,  74, 148,  53, 106, 212, 181, 119, 238, 193, 159,  35,
     70, 140,   5,  10,  20,  40,  80, 160,  93, 186, 105, 210, 185, 111, 222, 161,
     95, 190,  97, 194, 153,  47,  94, 188, 101, 202, 137,  15,  30,  60, 120, 240,
    253, 231, 211, 187, 107, 214, 177, 127, 254, 225, 223, 163,  91, 182, 113, 226,
    217, 175,  67, 134,  17,  34,  68, 136,  13,  26,  52, 104, 208, 189, 103, 206,
    129,  31,  62, 124, 248, 237, 199, 147,  59, 118, 236, 197, 151,  51, 102, 204,
    133,  23,  46,  92, 184, 109, 218, 169,  79, 158,  33,  66, 132,  21,  42,  84,
    168,  77, 154,  41,  82, 164,  85, 170,  73, 146,  57, 114, 228, 213, 183, 115,
    230, 209, 191,  99, 198, 145,  63, 126, 252, 229, 215, 179, 123, 246, 241, 255,
    227, 219, 171,  75, 150,  49,  98, 196, 149,  55, 110, 220, 165,  87, 174,  65,
    130,  25,  50, 100, 200, 141,   7,  14,  28,  56, 112, 224, 221, 167,  83, 166,
     81, 162,  89, 178, 121, 242, 249, 239, 195, 155,  43,  86, 172,  69, 138,   9,
     18,  36,  72, 144,  61, 122, 244, 245, 247, 243, 251, 235, 203, 139,  11,  22,
     44,  88, 176, 125, 250, 233, 207, 131,  27,  54, 108, 216, 173,  71, 142,
]

DQ = [
    [
        190,  96, 250, 132,  59,  81, 159, 154, 200,   7, 111, 245,  10,  20,  41, 156, 168,  79, 173, 231, 229, 171,
        210, 240,  17,  67, 215,  43, 120,   8, 199,  74, 102, 220, 251,  95, 175,  87, 166, 113,  75, 198,  25
    ],
    [
         97, 251, 133,  60,  82, 160, 155, 201,   8, 112, 246,  11,  21,  42, 157, 169,  80, 174, 232, 230, 172,
        211, 241,  18,  68, 216,  44, 121,   9, 200,  75, 103, 221, 252,  96, 176,  88, 167, 114,  76, 199,  26, 1
    ]
]

DP = [
    [
        231, 229, 171, 210, 240,  17, 67, 215,  43, 120,   8, 199,
         74, 102, 220, 251,  95, 175, 87, 166, 113,  75, 198,  25
    ],
    [
        230, 172, 211, 241, 18, 68, 216,  44, 121,  9, 200, 75,
        103, 221, 252, 96, 176, 88, 167, 114, 76, 199, 26,   1
    ]
]

RS_L12_BITS = 8
L2_P = 43 * 2 * 2
L2_Q = 26 * 2 * 2


def generateErrorDetectionAndCorrection(data, iStart, iEnd):
    edc_i = 0

    for i in range(iStart, iEnd):
        edc_i = EDC_crctable[(int)((edc_i ^ data[i]) & 0xFF)] ^ (edc_i >> 8)

    return edc_i


def generateErrorCorrectionCode_P(data, data_p, output, output_p):
    assert(len(data) - data_p >= 43 * 24 * 2)
    assert(len(output) - output_p >= L2_P)

    for j in range(0, 43):
        for i in range(0, 24):
            for n in range(0, 2):
                cdata = data[data_p + i * 2 * 43 + n] & 0xff

                if cdata == 0:
                    continue

                base = rs_l12_log[cdata]

                for t in range(0, 2):
                    sum = base + DP[t][i]

                    if sum >= ((1 << RS_L12_BITS) - 1):
                        sum -= (1 << RS_L12_BITS) - 1

                    output[output_p + 43 * 2 * t + n] ^= rs_l12_alog[sum]

        output_p += 2
        data_p += 2

    return output


def generateErrorCorrectionCode_Q(data, data_p, output, output_p):
    assert(len(data) - data_p >= 4 + 0x800 + 4 + 8 + L2_P)
    assert(len(output) - output_p >= L2_Q)

    for j in range(0, 26):
        for i in range(0, 43):
            for n in range(0, 2):
                cdata = data[data_p + (j * 43 * 2 + i * 2 * 44 + n) % (4 + 0x800 + 4 + 8 + L2_P)] & 0xff

                if cdata == 0:
                    continue

                base = rs_l12_log[cdata]

                for t in range(0, 2):
                    sum = base + DQ[t][i]

                    if sum >= ((1 << RS_L12_BITS) - 1):
                        sum -= (1 << RS_L12_BITS) - 1

                    output[output_p + 26 * 2 * t + n] ^= rs_l12_alog[sum]

        output_p += 2

    return output


def bcd_to_int(bytes):
    ints = []

    for c in bytes:
        ints.append((c >> 4) & 0x0f)
        ints.append(c & 0x0f)

    return int("".join([str(i) for i in ints]))


def int_to_bcd(input):
    digits = [int(c) for c in str(input)][::-1]
    output = []

    if (len(digits) % 2) != 0:
        digits.append(0)

    for i in range(0, len(digits), 2):
        output.append(digits[i] | (digits[i+1] << 4))

    return bytearray(output[::-1])

def parse_sbs(input_filename, output_filename, frame_width, frame_height):
    with open(input_filename, "rb") as infile:
        data = bytearray(infile.read())
        chunks = [data[i:i+0x2000] for i in range(0, len(data), 0x2000)]

        frame_cnt = 0
        with open(output_filename, "wb") as outfile:
            for frame_idx, chunk in enumerate(chunks):
                chunk_padding = 1

                chunk_split = [chunk[i:i+2016] for i in range(0, len(chunk), 2016)]

                str_header = bytearray([
                    0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x16, 0x52, 0x56, 0x02,
                    0x01, 0x01, 0x42, 0x80, 0x01, 0x01, 0x42, 0x80,
                ])

                frame_header = bytearray([
                    0x60, 0x01, 0x01, 0x80, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00,
                    0x40, 0x01, 0xE0, 0x00, 0xA0, 0x06, 0x00, 0x38, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00
                ])

                frame_header[0x06:0x08] = int.to_bytes(len(chunk_split), 2, 'little')  # Number of multiplexed chunks in this frame
                frame_header[0x08:0x0c] = int.to_bytes(frame_idx + 1, 4, 'little')  # Frame number: Starts at 1
                frame_header[0x0c:0x10] = int.to_bytes(len(chunk) * 8, 4, 'little')  # Bytes of data used in demuxed frame
                frame_header[0x10:0x12] = int.to_bytes(frame_width, 2, 'little')  # Width of frame in pixels
                frame_header[0x12:0x14] = int.to_bytes(frame_height, 2, 'little')  # Height of frame in pixels
                frame_header[0x14:0x1a] = chunk[:6]

                for chunk_idx, chunk_data in enumerate(chunk_split):
                    str_header[0x0c:0x0f] = int_to_bcd(bcd_to_int(str_header[0x0c:0x0f]) + frame_cnt)
                    frame_cnt += 1

                    # Multiplexed chunk number of this video frame
                    frame_header[0x04:0x06] = int.to_bytes(chunk_idx, 2, 'little')

                    if len(chunk_data) < 2016:
                        chunk_data += bytearray([0] * (2016 - len(chunk_data)))

                    if len(chunk_data) < 0x930 - 0x38:
                        chunk_data += bytearray([0] * (0x930 - 0x38 - len(chunk_data)))

                    abRawSectorData = bytearray()
                    abRawSectorData += str_header
                    abRawSectorData += frame_header
                    abRawSectorData += chunk_data

                    lngEdc = generateErrorDetectionAndCorrection(abRawSectorData, 0x10, 0x818)
                    abRawSectorData[0x818] = lngEdc & 0xff
                    abRawSectorData[0x818+1] = (lngEdc >> 8) & 0xff
                    abRawSectorData[0x818+2] = (lngEdc >> 16) & 0xff
                    abRawSectorData[0x818+3] = (lngEdc >> 24) & 0xff

                    abRawSectorData[12:16] = bytearray([0] * 4)

                    abRawSectorData = generateErrorCorrectionCode_P(abRawSectorData, 12, abRawSectorData, 0x81C)
                    abRawSectorData = generateErrorCorrectionCode_Q(abRawSectorData, 12, abRawSectorData, 0x8C8)

                    abRawSectorData[12:16] = str_header[12:16]

                    outfile.write(abRawSectorData)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--input', help='Input file', required=True)
    parser.add_argument('--output', help='Output file', default=None)

    # DDR resolution: 304x176
    # Mambo a Go Go: 160x192
    parser.add_argument('--width', help='Video width', required=True, type=int)
    parser.add_argument('--height', help='Video height', required=True, type=int)

    args = parser.parse_args()

    print(args.input)

    if args.output is None:
        args.output = os.path.splitext(args.input)[0] + ".STR"

    parse_sbs(args.input, args.output, args.width, args.height)


if __name__ == "__main__":
    main()
