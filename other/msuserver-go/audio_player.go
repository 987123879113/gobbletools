package main

import (
	"bytes"
	"log"
	"time"

	"github.com/hajimehoshi/oto/v2"
	"github.com/tosone/minimp3"
)

type AudioPlayer struct {
	decoder   *minimp3.Decoder
	context   *oto.Context
	player    oto.Player
	startTime time.Time
}

func NewAudioPlayer(filename string) *AudioPlayer {
	decoder, data, _ := minimp3.DecodeFull(
		DecryptMp3(filename),
	)

	ctx, _, err := oto.NewContext(decoder.SampleRate, decoder.Channels, 2)
	if err != nil {
		log.Printf("audio error. Unable to create new OtoContext: %v \n\r", err)
		return nil
	}

	return &AudioPlayer{
		decoder: decoder,
		context: ctx,
		player:  ctx.NewPlayer(bytes.NewReader(data)),
	}
}

func (c *AudioPlayer) Start() {
	if c.player != nil {
		c.player.Reset()
		c.startTime = time.Now()
		c.player.Play()
	}
}

func (c *AudioPlayer) Stop() {
	if c.player.IsPlaying() {
		c.context.Suspend()
	}
}

func (c *AudioPlayer) GetPosition() uint32 {
	var timestamp uint32

	if c.player != nil && c.player.IsPlaying() {
		duration := float64(time.Now().Sub(c.startTime).Milliseconds()) / 1000
		timestamp = uint32(float64(c.decoder.SampleRate) * duration)
	}

	return timestamp
}
