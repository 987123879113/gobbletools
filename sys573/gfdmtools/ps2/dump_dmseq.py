import os

output_path = "output"

os.makedirs(output_path, exist_ok=True)

with open("PBPX_952.06", "rb") as infile:
    infile.seek(0xabda68)

    charts = []
    for i in range(30):
        for j in range(6):
            filesize = int.from_bytes(infile.read(4), 'little') * 8
            offset = int.from_bytes(infile.read(4), 'little') - 0x1FF000

            charts.append((i, j, offset, filesize))

    for chart in sorted(charts, key=lambda x:x[2]):
        musicid = chart[0]
        diff = ["prac", "easy", "norm", "real", "expr", "lnkn", "lnkx", "bnus"][chart[1]]
        offset = chart[2]
        filesize = chart[3]

        output_filename = os.path.join(output_path, "seq%03d%s.dsq" % (musicid, diff))

        print("%s: %08x %04x" % (output_filename, chart[2], chart[3]))

        with open(output_filename, "wb") as outfile:
            infile.seek(offset)
            outfile.write(infile.read(filesize))
