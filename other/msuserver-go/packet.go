package main

const (
	PACKET_DELIM = 0xc0
)

func escape_packet(data []byte) []byte {
	output := []byte{}

	for _, c := range data {
		switch c {
		case 0xc0:
			output = append(output, []byte{0xdb, 0xdc}...)
		case 0xdb:
			output = append(output, []byte{0xdb, 0xdd}...)
		default:
			output = append(output, c)
		}
	}

	return output
}

func unescape_packet(data []byte) []byte {
	output := []byte{}

	for i := 0; i < len(data); i++ {
		if i+1 < len(data) && data[i] == 0xdb {
			switch data[i+1] {
			case 0xdd:
				output = append(output, 0xdb)
				i += 1
			case 0xdc:
				output = append(output, 0xc0)
				i += 1
			}
		} else {
			output = append(output, data[i])
		}
	}

	return output
}
