package main

import (
	"log"
	"net"
)

func main() {
	brain := NewMsuBrain()
	sessionUnitClient := NewSessionUnitClient(&brain)
	brain.RegisterSessionUnitClient(&sessionUnitClient)

	go sessionUnitClient.BroadcastTimestamp()

	ln, err := net.Listen("tcp", ":8001")
	if err != nil {
		panic(err)
	}

	defer func() {
		for _, client := range brain.RegisteredClients {
			if client != nil {
				(*client).Close()
			}
		}
	}()

	clientID := 1
	for {
		conn, e := ln.Accept()
		if e != nil {
			if ne, ok := e.(net.Error); ok && ne.Temporary() {
				log.Printf("accept temp err: %v", ne)
				continue
			}

			log.Printf("accept err: %v", e)
			return
		}

		client := NewGameClient(&conn, &brain, clientID)
		brain.RegisterClient(&client)
		clientID += 1

		go client.SendChainBufferPackets()
		go client.ReceiveData()
	}
}
