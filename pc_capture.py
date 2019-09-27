import io
import sys
import json
import struct
import socket
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PIL import Image
from Ui_MainWindow import Ui_MainWindow


class MainWindow(QMainWindow):
    closeCutScreenSignal = pyqtSignal()
    def __init__(self, addr):
        self.client = socket.socket()
        self.client.connect(addr)
        super(MainWindow, self).__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.screen = QApplication.primaryScreen()
        self.getCurrentWindowsPosition()
        self.mouse_down = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_down = True
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseReleaseEvent(self, event):
        self.mouse_down = False

    def mouseMoveEvent(self, event):
        if self.mouse_down:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()

    def getCurrentWindowsPosition(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.performCapture)
        self.timer.start(100)

    def performCapture(self):
        self.screenshot = self.screen.grabWindow(QApplication.desktop().winId(), self.geometry().x()+10, self.geometry().y()+41, 480, 640)
        buf_raw = QBuffer()
        buf_raw.open(QBuffer.ReadWrite)
        self.screenshot.save(buf_raw, 'bmp')
        im = Image.open(io.BytesIO(buf_raw.data()))
        im = im.resize((240, 320), Image.ANTIALIAS)
        im = im.transpose(Image.ROTATE_90)
        buf_im = io.BytesIO()
        im.save(buf_im, format='jpeg')
        buf_im.seek(0)
        self.sendPicture(buf_im, 1)

    def sendPicture(self, fpath, phone):
        if type(fpath) == str:
            print("fpath: {}, phone: {}".format(fpath, phone))
            with open(fpath, 'rb') as f:
                frame = f.read()
        else:
            frame = fpath.getvalue()
        header = {'cmd': 'cam_frame', 'frame_size': len(frame), 'phone': phone, 'cam': 'back'}
        header_bytes = json.dumps(header).encode('utf-8')
        self.client.send(struct.pack('i', len(header_bytes)))
        self.client.send(header_bytes)
        self.client.send(frame)


if __name__ == '__main__':

    if len(sys.argv) != 3:
        print("usage: %s <host> <port>" % sys.argv[0])
        exit(1)
    host, port = sys.argv[1], int(sys.argv[2])
    addr = (host, port)
    app = QApplication(sys.argv)
    m = MainWindow(addr)
    ui = Ui_MainWindow()
    ui.setupUi(m)
    m.show()
    app.exec_()
