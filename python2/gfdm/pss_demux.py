import argparse
import os
import sys

def demux_pss(input_filename, output_folder):
    base_filename = os.path.splitext(os.path.basename(input_filename))[0]

    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)

    with open(input_filename, "rb") as infile:
        data = bytearray(infile.read())

        idx = 0

        video_output = open(os.path.join(output_folder, "%s.m2v" % base_filename), "wb")
        audio_outputs = {}

        while True:
            header = data[idx:idx+4]
            idx += 4

            if header == bytearray([0x00, 0x00, 0x01, 0xba]):
                # MPEG start
                idx += 0x0a

            elif header == bytearray([0x00, 0x00, 0x01, 0xb9]):
                # MPEG end
                break

            elif header == bytearray([0x00, 0x00, 0x01, 0xbb]):
                # Not sure
                idx += int.from_bytes(data[idx:idx+2], byteorder="big") + 2

            elif header == bytearray([0x00, 0x00, 0x01, 0xbe]):
                # Audio?
                idx += int.from_bytes(data[idx:idx+2], byteorder="big") + 2

            elif header[:3] == bytearray([0x00, 0x00, 0x01]):
                if header[3] >= 0xbd and header[3] <= 0xdf and header[3] != 0xbe:
                    streamType = (data[idx+0x10] + data[idx+0x12]) & 0xf0
                    streamId = (data[idx+0x10] + data[idx+0x12]) & 0x0f

                    if streamType != 0x90:
                        print("Found unexpected audio stream type @ %08x" % (idx - 4))
                        exit(1)

                    if streamId not in audio_outputs:
                        part = ["___k", "__bk", "_gbk", "d__k", "d_bk"][streamId - 1]
                        audio_outputs[streamId] = open(os.path.join(output_folder, "%s%s.at3" % (base_filename, part)), "wb")

                    dataLen = int.from_bytes(data[idx:idx+2], byteorder="big")
                    headerOffset = int.from_bytes(data[idx+4:idx+5], byteorder="little")
                    dataLen -= headerOffset + 7
                    idx += headerOffset + 9

                    audio_outputs[streamId].write(data[idx:idx+dataLen])
                    idx += dataLen

                elif header[3] >= 0xe0 and header[3] <= 0xef:
                    dataLen = int.from_bytes(data[idx:idx+2], byteorder="big")
                    headerOffset = int.from_bytes(data[idx+4:idx+5], byteorder="little")
                    dataLen -= headerOffset + 3
                    idx += headerOffset + 5

                    video_output.write(data[idx:idx+dataLen])
                    idx += dataLen

                else:
                    exit(1)

            else:
                exit(1)

    for k in audio_outputs:
        audio_outputs[k].close()

    video_output.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input PSS file', required=True)
    parser.add_argument('-o', '--output', help='Output folder (optional)', default="")

    args = parser.parse_args()

    demux_pss(args.input, args.output)

