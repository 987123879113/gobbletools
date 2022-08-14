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
    ch = input("Enter command (s, sn (num), s2): ").strip().lower()

    if ch == "s":
        request_no_upper = "1234"
        request_no_lower = "1234"
        conn.sendall(b"~\x42\x00\x00\x15\x00\x07\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x02\x02\x00\x01\x01")

    elif ch.startswith("sn "):
        # Request a specific song
        request_no_str = ch[2:].strip()
        request_no = [int(x) for x in request_no_str.split('-')]
        request_no_bytes = int.to_bytes(request_no[0], 2, 'big') + int.to_bytes(request_no[1], 1, 'big')
        conn.sendall(b"~\x42\x00\x00\x15\x00" + request_no_bytes + b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x02\x02\x00\x01\x01")

    # elif ch == "s1":
    #     conn.sendall(b"~\x42\x00\x00\x15\x00\x07\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")

    elif ch == "s2":
        conn.sendall(b"~\x02\x02\x00\x01\x01")

    elif ch.startswith("^"):
        conn.sendall(ch.encode('ascii'))

    # else:
    #     print("Unknown command: '%s'" % ch)
