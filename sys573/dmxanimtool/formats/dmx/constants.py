from enum import IntEnum


class AnimationCommands(IntEnum):
    Uninitialized = -1
    Nop = 0
    PlayNormal = 1
    MovieAppend = 2
    MovieStart = 3
    PlayBeat = 4
    ReverseDirection = 5
    PlayBeat2 = 6
    PlayFast = 7
