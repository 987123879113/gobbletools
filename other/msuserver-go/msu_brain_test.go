package main

import (
	"bytes"
	"testing"
)

func TestMsuBrain_ClientTests(t *testing.T) {
	brain := NewMsuBrain()
	client := NewGameClient(
		nil,
		nil,
		1,
	)
	client.ClientName = []byte{'t', 'e', 's', 't'}

	t.Run("Register client", func(t *testing.T) {
		brain.RegisterClient(&client)

		if brain.RegisteredClients[client.ClientID] != &client {
			t.Errorf("Could not register client")
		}
	})

	t.Run("Get register client", func(t *testing.T) {
		c := brain.GetRegisteredClient(client.ClientID)

		if c != &client {
			t.Errorf("Could not get previously registered client")
		}
	})

	t.Run("Get registered client name", func(t *testing.T) {
		c := brain.GetRegisteredClientName(client.ClientID)

		if !bytes.Equal(c, client.ClientName) {
			t.Errorf("Could not get previously registered client")
		}
	})

	t.Run("Unregister client", func(t *testing.T) {
		brain.UnregisterClient(client.ClientID)

		if brain.RegisteredClients[client.ClientID] != nil {
			t.Errorf("Could not unregister client")
		}
	})
}
func TestMsuBrain_GetNextBufferId(t *testing.T) {
	brain := NewMsuBrain()

	for i := 0; i <= 32; i++ {
		expectedValue := i % 16
		nextBufferId := brain.GetNextBufferId()

		if nextBufferId != expectedValue {
			t.Errorf("Expected %d, found %d for next buffer ID", expectedValue, nextBufferId)
		}
	}
}
