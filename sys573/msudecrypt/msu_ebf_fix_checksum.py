import struct
import sys
import ctypes

with open(sys.argv[1], "rb") as infile:
    data = bytearray(infile.read())
    data[0x1c:0x20] = struct.pack("<I", 0)

    checksum = 0
    for i in range(0, len(data), 4):
        checksum += struct.unpack(">I", data[i:i+4])[0]
        checksum &= 0xffffffff

checksum_diff = 0xffffffff - checksum

print("%08x %08x" % (checksum, checksum_diff))

if checksum_diff != 0:
    with open(sys.argv[1], "rb+") as outfile:
        outfile.seek(0x1c)
        outfile.write(struct.pack(">I", checksum_diff))
