package main

import (
	"bytes"
	"testing"
)

func TestPacketResponseGeneration(t *testing.T) {
	expected := []byte{0x01, 0x00, 0x01, 0x02, 0x03}
	packet := PacketResponse { 1, []byte{0x00, 0x01, 0x02, 0x03} }
	packet_bytes := packet.ToBytes()
	if !bytes.Equal(packet_bytes, expected) {
		t.Errorf("Packet %d did not generate correctly %v %v", packet.Command, packet_bytes, expected)
	}
}
