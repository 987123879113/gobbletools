package main

import (
	"bufio"
	"encoding/hex"
	"log"
	"net"
	"time"
)

type GameClient struct {
	conn  *net.Conn
	brain *MsuBrain

	packetInputBuffer []byte

	BufferID int

	ClientID   int
	ClientName []byte

	packetInternalInputBuffer                   []byte
	packetInternalOutputBuffer                  []byte
	packetInternalBufferInputIndex              int
	packetInternalBufferOutputIndex             int
	packetInternalBufferNextExpectedOutputIndex int
	packetInternalBufferMinimumOutputIndex      int
	packetInternalInputBufferLastExecutedIndex  int
	lastSentChainPacket                         []byte
	lastSentChainPacketCount                    int
}

func NewGameClient(conn *net.Conn, brain *MsuBrain, clientID int) GameClient {
	c := GameClient{
		conn:              conn,
		brain:             brain,
		ClientID:          clientID,
		packetInputBuffer: []byte{},
	}
	return c
}

func (c *GameClient) Close() {
	log.Printf("Closing game client %d\n", c.ClientID)

	if c.conn != nil {
		(*c.conn).Close()
		c.conn = nil
	}
}

func (c *GameClient) ReceiveData() {
	b := bufio.NewReader(*c.conn)

	ch := make(chan byte)
	go func(ch chan byte) {
		for {
			// TODO: Try to replace this with something more efficient/not one byte at a time?
			d, err := b.ReadByte()
			if err != nil {
				break
			}

			ch <- d
		}
		close(ch)
	}(ch)

	for {
		select {
		case d, ok := <-ch:
			if !ok {
				break
			}

			// A packet will always start and end with 0xc0, so we only need to store data from the time we see the first 0xc0
			if len(c.packetInputBuffer) > 0 || (len(c.packetInputBuffer) == 0 && d == PACKET_DELIM) {
				c.packetInputBuffer = append(c.packetInputBuffer, d)
			}

			if len(c.packetInputBuffer) > 1 && d == PACKET_DELIM {
				endIdx := len(c.packetInputBuffer)
				packet := unescape_packet(c.packetInputBuffer[1 : endIdx-1])
				c.brain.ProcessPacket(c, packet)
				c.packetInputBuffer = c.packetInputBuffer[endIdx:]
			}
		}
	}
}

func (c *GameClient) SendData(packet []byte) {
	log.Printf("[client %d] Send Packet:\n%v\n", c.ClientID, hex.Dump(packet))
	(*c.conn).Write(packet)
}

func (c *GameClient) SendChainBufferPackets() {
	for {
		if c.lastSentChainPacketCount < 10 {
			// These packets will always come from the MSU
			tailLen := c.packetInternalBufferNextExpectedOutputIndex - c.packetInternalBufferOutputIndex

			respData := []byte{}
			if tailLen > 0 {
				respData = c.packetInternalOutputBuffer[len(c.packetInternalOutputBuffer)-tailLen:]
			}

			if len(respData) > 0 {
				d := []byte{byte(c.packetInternalBufferOutputIndex), byte(c.packetInternalBufferInputIndex), byte(len(respData))}
				d = append(d, respData...)

				log.Printf("Sending new packet to client %d\n", c.ClientID)
				resp := PacketResponse{0xff, d}
				log.Println(hex.Dump(resp.ToBytes()))

				c.lastSentChainPacket = c.brain.SessionUnitClient.prepareResponse(c, resp.ToBytes())
				c.SendData(c.lastSentChainPacket)
			} else if len(c.lastSentChainPacket) > 0 {
				log.Printf("Sending previous packet to client %d\n", c.ClientID)
				log.Println(hex.Dump(c.lastSentChainPacket))
				c.SendData(c.lastSentChainPacket)
			} else {
				log.Println("No data to send")
			}

			c.lastSentChainPacketCount += 1
		}

		time.Sleep(time.Second / 2)
	}
}
