package main

import (
	"encoding/binary"
	"encoding/hex"
	"log"
	"time"
)

type opcodeFn func(*SessionUnitClient, *GameClient, []byte) ([]PacketResponse, int, error)

type SessionUnitClient struct {
	brain          *MsuBrain
	opcodeHandlers map[byte]opcodeFn

	ClientID   int
	ClientName []byte

	audioPlayer *AudioPlayer
}

func NewSessionUnitClient(brain *MsuBrain) SessionUnitClient {
	s := SessionUnitClient{
		brain: brain,
		opcodeHandlers: map[byte]opcodeFn{
			0x02: opcodeRegisterClient,
			0x04: opcodeGetRegisteredClientName,
			0x06: opcodeEcho,
			0x1e: opcodeKeepAlive,
			0x20: opcode_20,
			0x40: opcodeLoadFile,
			0x42: opcode_42,
			0x44: opcode_44,
			0x48: opcode_48,
			0x4a: opcode_4a,
			0x4c: opcode_4c,
			0x50: opcode_50,
			0x58: opcode_58,
			0x60: opcode_60,
			0x62: opcode_62,
			0x68: opcode_68,
			0xff: opcodeChainPacket,
		},
		ClientID:   0,
		ClientName: []byte{'S', 'E', 'S', 'S', 'I', 'O', 'N'},
	}

	return s
}

func (c *SessionUnitClient) BroadcastTimestamp() {
	for {
		if c.audioPlayer != nil && c.audioPlayer.player.IsPlaying() {
			for i := 0; i < len(c.brain.RegisteredClients); i++ {
				client := c.brain.RegisteredClients[i]

				if client == nil {
					continue
				}

				timestamp := c.audioPlayer.GetPosition()

				log.Printf("Timestamp: %d\n", timestamp)

				var packet PacketResponse
				b := make([]byte, 4)
				binary.LittleEndian.PutUint32(b, timestamp)
				if timestamp > 0xffffff {
					packet = PacketResponse{0x46, b}
				} else {
					packet = PacketResponse{0x4e, b[:3]}
				}

				client.SendData(c.prepareResponse(client, packet.ToBytes()))
			}
		}

		time.Sleep(time.Second / 30)
	}
}

func (c *SessionUnitClient) BroadcastPacket(packet PacketResponse) {
	for i := 0; i < len(c.brain.RegisteredClients); i++ {
		client := c.brain.RegisteredClients[i]

		if client == nil {
			continue
		}

		client.SendData(c.prepareResponse(client, packet.ToBytes()))
	}
}

func (c *SessionUnitClient) prepareResponse(targetClient *GameClient, data []byte) []byte {
	sourcedest := byte(1 << targetClient.ClientID)
	data = append([]byte{0x00, sourcedest}, data...)
	checksum := calc_crc16(data)

	data = append(data, []byte{byte(checksum & 0xff), byte(checksum >> 8)}...)
	data = escape_packet(data)

	data = append([]byte{PACKET_DELIM}, data...)
	data = append(data, PACKET_DELIM)

	return data
}

func (c *SessionUnitClient) ProcessPacket(targetClient *GameClient, packet []byte) {
	log.Printf("[session] Packet:\n%v\n", hex.Dump(packet))

	allResponses := []byte{}

	for {
		if len(packet) <= 0 {
			break
		}

		command := packet[0]
		responses, parsedLen, err := c.opcodeHandlers[command](c, targetClient, packet[1:])

		if err != nil {
			// TODO: Proper error handling
			log.Printf("Error with packet: %v\n", err)
			continue
		}

		for _, response := range responses {
			responseBytes := response.ToBytes()

			if len(responseBytes)+len(allResponses)+6 > 0x40 {
				r := c.prepareResponse(targetClient, allResponses)
				targetClient.SendData(r)
				allResponses = []byte{}
			}

			allResponses = append(allResponses, responseBytes...)
		}

		packet = packet[1+parsedLen:]
	}

	if len(allResponses) > 0 {
		r := c.prepareResponse(targetClient, allResponses)
		targetClient.SendData(r)
	}
}

func opcodeRegisterClient(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80001238
	// MSU Response: 80001328
	// DM10 Handler: 80065d34
	// Returns the port number for the player

	nameLen := int(inputPacket[0])
	targetClient.ClientName = inputPacket[1 : 1+nameLen]

	// c.brain.RegisterClient(targetClient)

	targetClient.BufferID = (c.brain.GetNextBufferId() << 4) | targetClient.ClientID
	bufferPacket := PacketResponse{0x01, []byte{byte(targetClient.BufferID)}}

	for i := 0; i < 4; i++ {
		// This gets sent out about 4 times or so immediately after registration.
		// It would come together with this packet's response or after usually though, but timing is hard.
		c.BroadcastPacket(bufferPacket)
	}

	// TODO: Reset buffer state here
	// self.packet_output_buffers[targetClient.ClientID] = []
	targetClient.packetInternalInputBuffer = []byte{}
	targetClient.packetInternalOutputBuffer = []byte{}
	targetClient.packetInternalBufferInputIndex = 0
	targetClient.packetInternalBufferOutputIndex = 0
	targetClient.packetInternalBufferNextExpectedOutputIndex = 0
	targetClient.packetInternalBufferMinimumOutputIndex = 0
	targetClient.packetInternalInputBufferLastExecutedIndex = 0

	return []PacketResponse{
		{0x03, []byte{byte(targetClient.ClientID)}},
		bufferPacket,
	}, 1 + nameLen, nil
}

func opcodeGetRegisteredClientName(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 800014b0
	// MSU Response: 80001568
	// DM10 Handler: 80065824
	// Returns the requested client name string of the request size

	requestedClientName := c.brain.SessionUnitClient.brain.GetRegisteredClientName(int(inputPacket[0]))
	nameLen := int(inputPacket[1])

	if nameLen > 32 {
		// Max possible size
		nameLen = 32
	}

	if len(requestedClientName) < nameLen {
		// Pad to requested length
		padding := make([]byte, 32)
		requestedClientName = append(requestedClientName, padding...)
	}

	return []PacketResponse{
		{0x05, append([]byte{byte(nameLen)}, requestedClientName[:nameLen]...)},
	}, 2, nil
}

func opcodeEcho(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 8000110c
	// MSU Response: 80001194
	// DM10 Handler: 80065b10
	// Returns the exact same data that was sent to it
	payloadLen := int(inputPacket[0])
	if payloadLen > 0x3e {
		payloadLen = 0x3e
	}

	payload := inputPacket[:1+payloadLen]
	return []PacketResponse{
		{0x07, payload},
	}, 1 + payloadLen, nil
}

func opcodeKeepAlive(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80001048
	// MSU Response: 80001098
	// DM10 Handler: 80065f1c
	// Returns nothing
	return []PacketResponse{
		{0x1f, nil},
	}, 0, nil
}

func opcode_20(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 8000250c
	// MSU Response: 80002518
	// DM10 Handler: 80065e90
	// Returns a length and 4 bytes (what data? timestamps?)

	// Sets +0x1a04 to 1
	// Will return either 1 or 2? Seems to only be set at 0x800005cc
	// Possibly related to file loading???
	return []PacketResponse{
		{0x21, []byte{0x04, 0x00, 0x00, 0x00, 0x00}},
	}, 0, nil
}

func opcodeLoadFile(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80001724
	// MSU Response: 80001804
	// DM10 Handler: 80065f58
	filenameLen := int(inputPacket[0])
	filename := string(inputPacket[1 : 1+filenameLen])

	log.Printf("Load file:\n%s\n", filename)

	if c.audioPlayer != nil {
		c.audioPlayer.Stop()
	}

	c.audioPlayer = NewAudioPlayer(filename)

	result := 1
	if c.audioPlayer == nil {
		result = 0
	}

	return []PacketResponse{
		{0x41, []byte{uint8(result)}},
	}, 1 + filenameLen, nil
}

func opcode_42(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80001868
	// MSU Response: 800018fc
	// DM10 Handler: 80065fa8

	// TODO: Calls some function, 80005e58, and the return value is based on its result
	// Starts fifotask
	// Used to call: FUN_80005e58(*(obj + 0x19cc), [4, 0, 1, 2, 3][self.ClientID])
	return []PacketResponse{
		{0x43, []byte{0x01}},
	}, 0, nil
}

func opcode_44(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80001960
	// MSU Response: 80001a18
	// DM10 Handler: 80065ff8
	// param := math.Min(inputPacket[0], 0x7f)

	// TODO: Calls some function, 80005eb8, and the return value is based on its result
	// Used to call: FUN_80005eb8(*(obj + 0x19cc), [4, 0, 1, 2, 3][self.ClientID], param)
	return []PacketResponse{
		{0x45, []byte{0x01}},
	}, 1, nil
}

func opcode_48(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80001b98
	// MSU Response: 80001c0c
	// DM10 Handler: 80066108

	// Functionally the same as 0x4c
	// Will always return 1

	// param1 := inputPacket[0] & 3
	// param2 := inputPacket[0] >> 2

	return []PacketResponse{
		{0x49, []byte{0x01}},
	}, 1, nil
}

func opcode_4a(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80001a7c
	// MSU Response: 80001b34
	// DM10 Handler: 80066154

	// param := inputPacket[0] & 1

	// TODO: In 80001a7c, a function (80005e8c) is called.
	// If it fails, the result will be 2. If it succeeds, it's 1.
	// Figure out what the function is doing.
	// Used to call: FUN_80005e8c(*(obj + 0x19cc), [4, 0, 1, 2, 3][self.ClientID], param)
	return []PacketResponse{
		{0x4b, []byte{0x01}},
		// {0x47, []byte{0x01}},
	}, 1, nil
}

func opcode_4c(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80001c68
	// MSU Response: 80001cd8
	// DM10 Handler: 800661a4

	// Functionally the same as 0x48
	// Will always return 1

	// param1 := inputPacket[0] & 3
	param2 := inputPacket[0] >> 2

	if param2 == 2 {
		// Play song??
		if c.audioPlayer != nil {
			c.audioPlayer.Start()
		}
	} else if param2 == 0 {
		// Stop song??
		if c.audioPlayer != nil {
			c.audioPlayer.Stop()
		}
	}

	return []PacketResponse{
		{0x4d, []byte{0x01}},
	}, 1, nil
}

func opcode_50(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80001ef0
	// MSU Response: 800020a4
	// DM10 Handler: 80066248

	// param1 := inputPacket[0] & 0x0f
	// param6 := inputPacket[2] & 1
	// param7 := (inputPacket[2] >> 1) & 3
	// This is really a lookup table and a branch in the real code but this is equivalent
	// unk_param = (0x10 << param7) * param6
	// Used to call: FUN_8000d288([4, 0, 1, 2, 3][self.ClientID], ((0x10 << param7) * param6) | param1)

	// param2 := inputPacket[1] & 3
	// param3 := (inputPacket[1] >> 2) & 3
	// param4 := (inputPacket[1] >> 4) & 3
	// param5 := (inputPacket[1] >> 6) & 3
	param8 := (inputPacket[2] >> 3) & 3
	// Used in another call: FUN_8000e36c([4, 0, 1, 2, 3][self.ClientID], (param8 << 8) | (param2 << 6) | (param3 << 4) | (param4 << 2) | param5)

	// Possibly in charge of starting songs?
	// param1 == 1 is start song?
	// param1 == 0 is stop song?

	// (2 if param8 == 2 else 1) == 1
	result := 1
	if param8 == 2 {
		result = 0
	}
	return []PacketResponse{
		{0x51, []byte{byte(result)}},
	}, 3, nil
}

func opcode_58(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80002108
	// MSU Response: 800021a4
	// DM10 Handler: 80066290
	// Will always return 1

	// param := inputPacket[0] & 1
	// s := ((3 - [4, 0, 1, 2, 3][self.ClientID]) * 2 + 9) & 0x1f
	// REG_B0400040 &= ~(1 << s) // Clear bit
	// REG_B0400040 |= param << s // Set bit with param
	return []PacketResponse{
		{0x59, []byte{0x01}},
	}, 1, nil
}

func opcode_60(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 80002200
	// MSU Response: 8000229c
	// DM10 Handler: 800662d8
	// Will always return 1

	// param := inputPacket[0] & 1
	// s := ((3 - [4, 0, 1, 2, 3][self.ClientID]) * 2 + 8) & 0x1f
	// REG_B0400040 &= ~(1 << s) // Clear bit
	// REG_B0400040 |= param << s // Set bit with param
	return []PacketResponse{
		{0x61, []byte{0x01}},
	}, 1, nil
}

func opcode_62(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 800022f8
	// MSU Response: 80002394
	// DM10 Handler: 80066320
	// Will always return 1

	// param := inputPacket[0] & 1
	// s := (7 - [4, 0, 1, 2, 3][self.ClientID]) & 0x1f
	// REG_B0400040 &= ~(1 << s) // Clear bit
	// REG_B0400040 |= param << s // Set bit with param
	return []PacketResponse{
		{0x63, []byte{0x01}},
	}, 1, nil
}

func opcode_68(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	// MSU Handler: 800023f8
	// MSU Response: 8000245c
	// DM10 Handler: 80066368

	// TODO: Calls a function, 80005878, and the return value is used as the result of the opcode
	return []PacketResponse{
		{0x69, []byte{0x01}},
	}, 0, nil
}

func opcodeChainPacket(c *SessionUnitClient, targetClient *GameClient, inputPacket []byte) ([]PacketResponse, int, error) {
	bufferInputIndex := int(inputPacket[0])
	bufferOutputIndex := int(inputPacket[1])
	payloadLen := int(inputPacket[2])
	payload := inputPacket[3 : 3+payloadLen]
	packetUsedSize := 3 + payloadLen

	log.Printf("%02x %02x %02x | %02x %02x %02x\n", bufferInputIndex, len(targetClient.packetInternalInputBuffer), targetClient.packetInternalBufferInputIndex, bufferOutputIndex, len(targetClient.packetInternalOutputBuffer), targetClient.packetInternalBufferOutputIndex)

	if bufferInputIndex > len(targetClient.packetInternalInputBuffer) {
		log.Printf("bufferInputIndex > len(targetClient.packetInternalInputBuffer): %d > %d", bufferInputIndex, len(targetClient.packetInternalInputBuffer))
		// If the input index is greater then it gets set to the end of the input index buffer and is not executed
		targetClient.packetInternalBufferInputIndex = len(targetClient.packetInternalInputBuffer)
		return []PacketResponse{}, packetUsedSize, nil
	}

	if bufferOutputIndex > len(targetClient.packetInternalOutputBuffer) {
		log.Printf("bufferOutputIndex > len(targetClient.packetInternalOutputBuffer): %d > %d", bufferOutputIndex, len(targetClient.packetInternalOutputBuffer))
		// If the output index is greater then the command gets ignored and the output index is not updated
		return []PacketResponse{}, packetUsedSize, nil
	}

	if bufferInputIndex > targetClient.packetInternalBufferInputIndex {
		// It's possible to increase but not decrease this by sending FF commands, even if the command fails
		targetClient.packetInternalBufferInputIndex = bufferInputIndex
	}

	if bufferOutputIndex > targetClient.packetInternalBufferOutputIndex {
		// It's possible to increase but not decrease this by sending FF commands, even if the command fails
		targetClient.packetInternalBufferOutputIndex = bufferOutputIndex
	}

	// TODO: Fix these buffers
	if bufferInputIndex == len(targetClient.packetInternalInputBuffer) && bufferOutputIndex <= len(targetClient.packetInternalOutputBuffer) {
		foundCommands := make(map[byte]bool)
		immediateReturnOffset := len(targetClient.packetInternalOutputBuffer)

		targetClient.packetInternalInputBuffer = append(targetClient.packetInternalInputBuffer, payload...)
		targetClient.packetInternalBufferInputIndex += payloadLen

		payload = []byte{}
		if targetClient.packetInternalInputBufferLastExecutedIndex < len(targetClient.packetInternalInputBuffer) {
			payload = targetClient.packetInternalInputBuffer[targetClient.packetInternalInputBufferLastExecutedIndex:]
		}

		for {
			curPayloadLen := len(payload)

			if curPayloadLen <= 0 {
				break
			}

			log.Printf("payload[0]: %02x\n", payload[0])
			responses, parsedLen, err := c.opcodeHandlers[payload[0]](c, targetClient, payload[1:])
			parsedLen += 1 // 1 for the opcode byte itself

			log.Printf("payloadLen: %d %02x %d\n", curPayloadLen, payload[0], len(responses))

			payload = payload[parsedLen:]

			if err != nil {
				// TODO: Proper error handling
				log.Printf("Error with packet: %v\n", err)
				continue
			}

			targetClient.packetInternalInputBufferLastExecutedIndex += parsedLen

			for _, response := range responses {
				if _, ok := foundCommands[response.Command]; response.Command == 0x4d && ok {
					continue
				}

				responseBytes := response.ToBytes()

				log.Println("Response data:")
				log.Println(hex.Dump(responseBytes))

				targetClient.packetInternalOutputBuffer = append(targetClient.packetInternalOutputBuffer, responseBytes...)
				targetClient.packetInternalBufferNextExpectedOutputIndex += len(responseBytes)

				foundCommands[response.Command] = true
			}
		}

		if payloadLen == 0 {
			// Hack
			resp2 := PacketResponse{0x47, []byte{1}}
			targetClient.SendData(c.prepareResponse(targetClient, resp2.ToBytes()))
			foundCommands[resp2.Command] = true
		}

		// The result of the command should be immediately returned, separate from the looped return results
		respData := targetClient.packetInternalOutputBuffer[immediateReturnOffset:]
		if len(respData) > 0 {
			log.Printf("Immediate return")
			d := []byte{byte(immediateReturnOffset), byte(targetClient.packetInternalBufferInputIndex), byte(len(respData))}
			d = append(d, respData...)

			resp := PacketResponse{0xff, d}
			log.Println(hex.Dump(resp.ToBytes()))
			targetClient.lastSentChainPacket = c.prepareResponse(targetClient, resp.ToBytes())
			targetClient.SendData(targetClient.lastSentChainPacket)
			targetClient.lastSentChainPacketCount = 0
		}
	} else {
		targetClient.packetInternalBufferOutputIndex = targetClient.packetInternalBufferNextExpectedOutputIndex
	}

	targetClient.packetInternalBufferMinimumOutputIndex = targetClient.packetInternalBufferOutputIndex

	return []PacketResponse{}, packetUsedSize, nil
}
