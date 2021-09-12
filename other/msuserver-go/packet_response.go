package main

type PacketResponse struct {
    Command  byte
    Data     []byte
}

func (c PacketResponse) ToBytes() []byte {
	return append([]byte{c.Command}, c.Data...)
}

