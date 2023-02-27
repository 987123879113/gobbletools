from enum import IntEnum


class PlaybackMethod(IntEnum):
    Unknown = 0
    Normal = 1
    PingPong = 2
    Freeze = 3


class PlaybackDirection(IntEnum):
    Freeze = 0
    Forward = 1
    Reverse = -1


class AnimationFlags(IntEnum):
    PlaybackMethodNormal = 1
    PlaybackMethodPingPong = 2
    PlaybackMethodFreeze = 3

    PlaybackDirectionFreeze = 0
    PlaybackDirectionForward = 1
    PlaybackDirectionReverse = 2


class AnimationCommands(IntEnum):
    Play2 = 1
    Play3 = 2
    Play4 = 3
    PlayStretch = 4
    AppendLoopAll = 5
    FreezeFrame = 6
    AppendLoopLast = 7
    Clear = 8  # Are these two clear commands any different? I see more special cases for the 9 command but not for the 8 comand
    Clear2 = 9
    Play1 = 10  # Only on PS2
