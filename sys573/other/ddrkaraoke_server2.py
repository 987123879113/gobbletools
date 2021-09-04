# Spam s at the title screen until it changes to the loading screen
# Then spam s2 until you hear "are you ready?"
# Then go to server1 and run "play bpm beats filename.mp3" to play the song

from socket import *

s = socket(AF_INET, SOCK_STREAM)
s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
s.bind(('127.0.0.1', 5732))
s.listen(1)
conn, addr = s.accept()

while True:
    ch = input("Enter command (s, s1, s2): ").strip().lower()

    if ch == "s":
        conn.sendall(b"~\x42\x00\x00\x15\x00\x08\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x02\x02\x00\x01\x01")

    elif ch == "s1":
        conn.sendall(b"~\x42\x00\x00\x15\x00\x08\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")

    elif ch == "s2":
        conn.sendall(b"~\x02\x02\x00\x01\x01")

    elif ch.startswith("^"):
        conn.sendall(ch.encode('ascii'))

    # else:
    #     print("Unknown command: '%s'" % ch)
