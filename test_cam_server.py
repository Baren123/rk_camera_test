#coding: utf-8

import os
import sys
import time
import json
import struct
import socket

if __name__ == '__main__':

    client = socket.socket()

    if len(sys.argv) != 5:
        print("usage: %s <host> <port> <phone> <fpath>" % sys.argv[0])
        exit(1)
    host, port, phone, fpath = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    addr = (host, port)
    client = socket.socket()
    client.connect(addr)

    with open(fpath, 'rb') as f:
        frame = f.read()
    # frame = 'Hello, I am tester.'.encode('utf-8')

    header = {'cmd': 'cam_frame', 'frame_size': len(frame), 'phone': phone}
    header_bytes = json.dumps(header).encode('utf-8')
    client.send(struct.pack('i', len(header_bytes)))
    client.send(header_bytes)
    client.send(frame)
    print("发送完毕")
    client.close()


