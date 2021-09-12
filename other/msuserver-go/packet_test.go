package main

import (
	"reflect"
	"testing"
)

func Test_escape_packet(t *testing.T) {
	tests := []struct {
		data []byte
		want []byte
	}{
		{[]byte{0x00, 0x01, 0x02}, []byte{0x00, 0x01, 0x02}},
		{[]byte{0xdb}, []byte{0xdb, 0xdd}},
		{[]byte{0xc0}, []byte{0xdb, 0xdc}},
		{[]byte{0xdb, 0xaa, 0xaa, 0xc0, 0x00}, []byte{0xdb, 0xdd, 0xaa, 0xaa, 0xdb, 0xdc, 0x00}},
	}
	for _, tt := range tests {
		if got := escape_packet(tt.data); !reflect.DeepEqual(got, tt.want) {
			t.Errorf("escape_packet() = %v, want %v", got, tt.want)
		}
	}
}

func Test_unescape_packet(t *testing.T) {
	tests := []struct {
		data []byte
		want []byte
	}{
		{[]byte{0x00, 0x01, 0x02}, []byte{0x00, 0x01, 0x02}},
		{[]byte{0xdb, 0xdd}, []byte{0xdb}},
		{[]byte{0xdb, 0xdc}, []byte{0xc0}},
		{[]byte{0xdb, 0xdd, 0xaa, 0xaa, 0xdb, 0xdc, 0x00}, []byte{0xdb, 0xaa, 0xaa, 0xc0, 0x00}},
	}
	for _, tt := range tests {
		if got := unescape_packet(tt.data); !reflect.DeepEqual(got, tt.want) {
			t.Errorf("unescape_packet() = %v, want %v", got, tt.want)
		}
	}
}
