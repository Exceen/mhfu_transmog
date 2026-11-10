#!/usr/bin/env python3
"""Read the network player records live from a running PPSSPP and decode the online transmog bits.

Enable PPSSPP's remote debugger first (Settings -> Tools -> Developer tools -> Allow remote debugger).
Needs: pip install websocket-client

Usage: python3 online/read_records.py [port]   (port is found automatically on macOS/Linux via lsof)
"""
import base64
import json
import re
import struct
import subprocess
import sys

import websocket

RECORDS = 0x099959D0   # network records, 0x8C bytes each, player 0 = you
RECORD_SIZE = 0x8C
SLOTS = ["legs", "head", "chest", "arms", "waist"]


def find_ports():
    out = subprocess.run(["lsof", "-nP", "-a", "-iTCP", "-sTCP:LISTEN", "-c", "PPSSPP"],
                         capture_output=True, text=True).stdout
    return re.findall(r":(\d+) \(LISTEN\)", out)


def connect(ports):
    for port in ports:
        try:
            return websocket.create_connection(f"ws://127.0.0.1:{port}/debugger", timeout=3)
        except Exception as e:  # noqa: BLE001 - try the next port
            print(f"port {port}: {e}")
    sys.exit("no PPSSPP debugger found; is 'Allow remote debugger' enabled?")


def main():
    ws = connect(sys.argv[1:] or find_ports())

    def call(event, **kw):
        ws.send(json.dumps({"event": event, **kw}))
        while True:
            reply = json.loads(ws.recv())
            if reply.get("event") in (event, "error"):
                return reply

    def mem(addr, size):
        reply = call("memory.read", address=addr, size=size)
        if "base64" not in reply:
            sys.exit(reply)
        return base64.b64decode(reply["base64"])

    print(call("game.status").get("game"))
    for p in range(4):
        rec = mem(RECORDS + p * RECORD_SIZE, RECORD_SIZE)
        if not any(rec):
            continue
        w4 = struct.unpack_from("<H", rec, 0x34)[0]
        weapon = (w4 >> 11) | sum(((rec[0x40 + t * 12] >> 7) & 1) << (5 + t) for t in range(5))
        pig = "sent" if w4 & 0x400 else "not sent"
        print(f"player {p}{' (you)' if p == 0 else ''}: gender {rec[0x10]}, weapon eid {struct.unpack_from('<H', rec, 0x32)[0]}, "
              f"weapon model {weapon - 1 if weapon else 'not sent'}, pigment {pig}")
        for t, name in enumerate(SLOTS):
            e = 0x3C + t * 12
            v = rec[e + 5] | (((w4 >> t) & 1) << 8)
            model = "not sent" if v == 0 else (-1 if v == 0x1FF else v - 1)
            print(f"  {name:6} eid {struct.unpack_from('<H', rec, e + 2)[0]:3}  model {model}  "
                  f"pigment {'on' if (w4 >> (5 + t)) & 1 else 'off'}  color {rec[0x15 + t * 4]}")


if __name__ == "__main__":
    main()
