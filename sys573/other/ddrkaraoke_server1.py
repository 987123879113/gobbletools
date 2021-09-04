# Commands:
# PS Music Start
# PE Music End
# B0 Beat top
# B1 Beat other
# BK Song Start
# BI Song End
# BE Ending Start
# BP Paging
# BS SABI start
# Bs SABI end
# BC Climax start
# Bc Climax end
# BF Fade out

import struct
import time

from socket import *

import playsound

def send_beats(conn, bpm=160, beats=30, u=4):
    dur = 60000 / bpm / 1000

    cur_timestamp = 0
    for i in range(0, beats):
        for j in range(0, u):
            # if msvcrt.kbhit() and msvcrt.getch() == b'q':
            #     print("Stopping sending beats...")
            #     return

            cmd = "B" + str(min(j, 1))
            print(cur_timestamp, cmd)

            conn.sendall(b"\x00" + cmd.encode('ascii') + b"\x0d")
            # conn.write(b"\x00" + cmd.encode('ascii') + b"\x0d")

            time.sleep(dur)
            cur_timestamp += dur


def send_start_seq(conn):
    for cmd in ["PS", "BK"]:
        print(cmd)
        conn.sendall(b"\x00" + cmd.encode('ascii') + b"\x0d")
        # conn.write(b"\x00" + cmd.encode('ascii') + b"\x0d")
        time.sleep(0.5)


s = socket(AF_INET, SOCK_STREAM)
s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
s.bind(('127.0.0.1', 5731))
s.listen(1)
conn, addr = s.accept()
conn.setblocking(0)
while True:
    try:
        data = bytearray(conn.recv(4096))

    except:
        data = None

    ch = input("Enter command (play [bpm] [beats] [mp3 filename]): ").strip().lower()

    if ch == "start":
        send_start_seq(conn)

    elif ch.startswith("bpm"):
        # Same as play, but without the filename
        _, bpm, beats = ch.split(' ')

        bpm = float(bpm)
        beats = int(beats)

        send_beats(conn, bpm, beats)

    elif ch.startswith("play"):
        _, bpm, beats, mp3_filename = ch.split(' ')

        bpm = float(bpm)
        beats = int(beats)

        mp3_filename = mp3_filename.strip()
        if not mp3_filename.startswith("./"):
            mp3_filename = "./" + mp3_filename

        send_start_seq(conn)
        print(mp3_filename)
        playsound.playsound(mp3_filename, False)

        send_beats(conn, bpm, beats)
