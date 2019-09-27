#coding: utf-8

import os
import sys
import time
import json
import struct
import traceback
from adbutils import adb
from PIL import Image
from io import BytesIO
from socketserver import ThreadingTCPServer, StreamRequestHandler

class CamServerHandler(StreamRequestHandler):
    dev_sers = ['usb:1-1.1',
                'usb:1-1.2',
                'usb:1-1.3',
                'usb:1-1.4',
                'usb:1-1.5',
                'usb:1-1.6',
                'usb:1-1.7.1',
                'usb:1-1.7.2',
                'usb:1-1.7.3',
                'usb:1-1.7.4']
    devs = []

    def _print(self, msg):
        time_cur = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print("{} [CamServerHandler][{}] {}".format(time_cur, self.client_address, msg))

    def execShell(self, cmd):
        self._print(cmd)
        return os.system(cmd) == 0

    def write(self, msg):
        msg_bytes = json.dumps(msg).encode('utf-8')
        self.wfile.write(struct.pack('i', len(msg_bytes)))
        self.wfile.write(msg_bytes)

    def switchPhoneRoot(self):
        for ser in self.dev_sers:
            self.execShell("adb -s %s root" % ser)

    def handle(self):
        self.responses = {
            'cam_frame': self.handleCamFrame
        }
        # self.switchPhoneRoot()
        while True:
            try:
                # 1. 获取报文头大小
                header_size = self.rfile.read(4)
                if not header_size:
                    break
                header_size = struct.unpack('i', header_size)[0]
                # 2. 获取报文头
                header = self.rfile.read(header_size)
                if not header:
                    break
                header = header.decode('utf-8')
                header = json.loads(header)
                # 3. 报文处理
                if 'cmd' not in header:
                    self._print("ERR: 'cmd' not in header!")
                    break
                if header['cmd'] not in self.responses:
                    self._print("ERR: cmd '{}' unknow!".format(self.responses['cmd']))
                    break
                _handle = self.responses[header['cmd']]
                if not _handle(header):
                    self._print("ERR: handle '{}' failed!".format(self.responses['cmd']))
                    self.write({'ret': -1})
                    break
                else:
                    self.write({'ret': 0})
            except ConnectionResetError:
                break
            except:
                traceback.print_exc()
                break
        self._print("disconnect")

    def handleCamFrame(self, msg):
        if 'frame_size' not in msg or type(msg['frame_size']) != int:
            return False
        if 'phone' not in msg or type(msg['phone']) != int:
            return False
        if 'cam' not in msg or type(msg['cam']) != str:
            return False
        rk_cam_path = "/dev/video0" if msg['cam'] == 'front' else "/dev/video1"
        frame_name = msg['frame_name'] if 'frame_name' in msg else "frame.bmp"
        rk_frame_path = os.path.join('/mnt', frame_name)
        frame_size = msg['frame_size']
        phone = msg['phone']
        if phone <= 0 or phone > len(self.dev_sers):
            return False
        # 获取 frame data
        self._print("recv frame(size=%d)..." % frame_size)
        frame_data = self.rfile.read(frame_size)
        if not frame_data or len(frame_data) != frame_size:
            return False
        self._print("recv frame finish.")
        image = Image.open(BytesIO(frame_data))
        img_bytes = BytesIO()
        image.save(img_bytes, format='bmp')
        # 传到指定RK
        dev = self.devs[phone-1]
        img_bytes.seek(0)
        dev.sync.push(img_bytes, rk_frame_path)
        # 切换Frame
        dev.shell("vcam_ctl %s %s" % (rk_cam_path, rk_frame_path))
        return True


if __name__ == '__main__':
    if os.geteuid() != 0:
        print('ERR: Must run by root')
        exit(1)
    if len(sys.argv) != 3:
        print("usage: %s <host> <port>" % sys.argv[0])
        exit(1)
    for ser in CamServerHandler.dev_sers:
        print("switch '%s' to root" % ser)
        os.system("adb -s %s root" % ser)
    time.sleep(3)
    for ser in CamServerHandler.dev_sers:
        CamServerHandler.devs.append(adb.device(serial=ser))

    host, port = sys.argv[1], int(sys.argv[2])
    addr = (host, port)
    server = ThreadingTCPServer(addr, CamServerHandler)
    print("# start...")
    server.serve_forever()