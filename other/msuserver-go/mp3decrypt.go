package main

import (
	"crypto/md5"
	"encoding/binary"
	"log"
	"os"
	"path"
)

func generateMp3Key(filename []byte) [8]uint16 {
	key := []byte("!kAiNsYuu4NkAn3594NnAnbo9tyouzUi105DaisOugEnmIn4N")

	endIdx := 0
	for endIdx = 0; endIdx < len(filename); endIdx++ {
		if filename[endIdx] == '.' {
			break
		}
	}

	filename = filename[:endIdx]

	for i, c := range filename {
		if c >= 'A' && c <= 'Z' {
			// Make uppercase
			c += 0x20
		}

		key[i+len(filename)] = c
	}

	md5key := md5.Sum(key)

	result := [8]uint16{}
	for i := 0; i < len(md5key); i += 2 {
		result[i/2] = binary.BigEndian.Uint16(md5key[i : i+2])
	}

	return result
}

func DecryptMp3(filename string) []byte {
	file, err := os.Open(path.Join("data", filename))
	if err != nil {
		log.Printf("Couldn't open %s\n", filename)
		return nil
	}

	key := generateMp3Key([]byte(filename))
	expandedKey := []uint16{
		0xb7e1, 0x5618, 0xf44f, 0x9286, 0x30bd, 0xcef4, 0x6d2b, 0x0b62,
		0xa999, 0x47d0, 0xe607, 0x843e, 0x2275, 0xc0ac, 0x5ee3, 0xfd1a,
		0x9b51, 0x3988, 0xd7bf, 0x75f6, 0x142d, 0xb264, 0x509b, 0xeed2,
		0x8d09, 0x2b40, 0xc977, 0x67ae, 0x05e5, 0xa41c, 0x4253, 0xe08a,
	}

	// Mix key
	var t0 uint16
	var t1 uint16
	var s1 uint8
	for x := 0; x < 32; x++ {
		a2 := expandedKey[x]
		a0 := key[x%len(key)]

		for k := 0; k < 3; k++ {
			v0 := a2 + t1 + t0
			v1 := v0 >> 3
			a2 = v1 | (v0 << 13)
			t1 = a2

			a0 += t1 + t0
			v1 = a0
			v0 = a0 & 0x0f
			a0 = (v1 << v0) | (v1 >> (0x10 - v0))
			t0 = a0
		}

		expandedKey[x] = t1
		key[x%len(key)] = t0

		s1 += uint8(t1)
	}

	v1 := uint8((uint64(s1) * 0x5AC056B1) >> 32)
	counter := (s1 - (((v1 + ((s1 - v1) >> 1)) >> 7) * 0xbd)) + 0x43

	// If there's an extra byte at the end of the file, drop it because the data must be in 16-bit words to be decrypted.
	// This shouldn't affect any songs as far as I know since usually the last byte is a 00.
	// TODO: Determine if the MSU even decrypts or does anything with the last byte in the case of a non-even number of bytes.
	fileInfo, _ := file.Stat()
	data := make([]uint16, fileInfo.Size()/2)
	binary.Read(file, binary.BigEndian, data)

	// Decrypt data
	expandedKeyLen := uint8(len(expandedKey))

	output := []byte{}
	for i := 0; i < len(data); i++ {
		t0 := expandedKey[(counter+3)%expandedKeyLen]
		t1 := expandedKey[(counter+2)%expandedKeyLen]
		v1 := data[i] - t0
		v0 := ((t1 + t0) & 7) + 4
		v1 = (((v1 << (0x10 - v0)) | (v1 >> v0)) ^ t1) - (expandedKey[counter%expandedKeyLen] ^ expandedKey[(counter+1)%expandedKeyLen])

		expandedKey[counter%expandedKeyLen] = (expandedKey[counter%expandedKeyLen] + expandedKey[(counter+1)%expandedKeyLen]) & 0xffff
		counter += 1

		s := make([]byte, 2)
		binary.BigEndian.PutUint16(s, v1)
		output = append(output, s...)
	}

	file.Close()

	return output
}
