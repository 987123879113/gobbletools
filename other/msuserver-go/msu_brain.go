package main

import (
	"encoding/binary"
	"encoding/hex"
	"log"
)

const (
	ClientID_SessionUnit = 1
	ClientID_Game1       = 2
	ClientID_Game2       = 4
	ClientID_Game3       = 8
)

type MsuBrain struct {
	NextBufferId      int
	SessionUnitClient *SessionUnitClient
	RegisteredClients []*GameClient
}

func NewMsuBrain() MsuBrain {
	return MsuBrain{
		NextBufferId:      0,
		SessionUnitClient: nil,
		RegisteredClients: make([]*GameClient, 5),
	}
}

func (c *MsuBrain) RegisterSessionUnitClient(client *SessionUnitClient) {
	c.SessionUnitClient = client
}

func (c *MsuBrain) RegisterClient(client *GameClient) {
	c.RegisteredClients[client.ClientID] = client
}

func (c *MsuBrain) UnregisterClient(clientId int) {
	c.RegisteredClients[clientId].Close()
	c.RegisteredClients[clientId] = nil
}

func (c *MsuBrain) GetRegisteredClient(clientId int) *GameClient {
	return c.RegisteredClients[clientId]
}

func (c *MsuBrain) GetRegisteredClientName(clientId int) []byte {
	if clientId == 0 {
		// Multisession unit itself
		return c.SessionUnitClient.ClientName
	}

	client := c.RegisteredClients[clientId]

	if client == nil {
		return []byte{}
	}

	return client.ClientName
}

func (c *MsuBrain) GetNextBufferId() int {
	curBufferId := c.NextBufferId
	c.NextBufferId = (c.NextBufferId + 1) % 16
	return curBufferId
}

func (c *MsuBrain) ProcessPacket(sourceClient *GameClient, packet []byte) {
	log.Printf("[brain] Packet:\n%v\n", hex.Dump(packet))

	payload := packet[:len(packet)-2]
	expected_checksum := binary.LittleEndian.Uint16(packet[len(packet)-2:])
	checksum := calc_crc16(payload)

	if expected_checksum != checksum {
		log.Printf("Packet has invalid checksum! %04x vs %04x | %v\n", checksum, expected_checksum, packet)
		return
	}

	// status := packet[0]
	// sourceClientID := int(payload[1] >> 4)

	destinationClientID := int(payload[1] & 0x0f)
	if destinationClientID == ClientID_SessionUnit {
		c.SessionUnitClient.ProcessPacket(sourceClient, payload[2:])
	} else {
		// This is a direct send packet and doesn't get processed on the MSU
		clientIdLookup := map[int]int{
			ClientID_Game1: 1,
			ClientID_Game2: 2,
			ClientID_Game3: 3,
		}
		destinationClient := c.GetRegisteredClient(clientIdLookup[destinationClientID])

		packet = escape_packet(packet)
		packet = append([]byte{PACKET_DELIM}, packet...)
		packet = append(packet, PACKET_DELIM)

		destinationClient.SendData(packet)
	}
}
