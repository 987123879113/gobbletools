package main

import (
	"reflect"
	"testing"
)

func Test_generateMp3Key(t *testing.T) {
	tests := []struct {
		filename []byte
		want     [8]uint16
	}{
		{[]byte("JA10.DAT"), [8]uint16{0xe1b2, 0xdd4a, 0x4ed3, 0x707d, 0xbae1, 0x83c7, 0x05e8, 0x8aca}},
		{[]byte("VER001.DAT"), [8]uint16{0x66ac, 0x0c95, 0xd0d6, 0x1960, 0xaaf7, 0x8322, 0x7d1d, 0xe4b5}},
	}
	for _, tt := range tests {
		if got := generateMp3Key(tt.filename); !reflect.DeepEqual(got, tt.want) {
			t.Errorf("generate_mp3_key() = %v, want %v", got, tt.want)
		}
	}
}
