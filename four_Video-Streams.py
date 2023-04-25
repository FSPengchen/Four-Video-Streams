# 用python 使用pyqt5与opencv显示4个RTSP,采用四分屏显示上下左右面积相等,用来显示，断线重连，降低视频延时，以避免OpenCV库的频闪问题，并在稳定运行情况下，降低CPU及内存使用量
# https://pypi.tuna.tsinghua.edu.cn/simple  pip install opencv-python
import sys
import time

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt5 import QtGui, QtCore, QtWidgets
import cv2

class Thread(QThread):
    changePixmap = pyqtSignal(QImage, int)

    def __init__(self, url, index):
        super().__init__()
        self.url = url
        self.index = index
        self.flag = True

    def run(self):
        cap = cv2.VideoCapture(self.url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)
        while self.flag:
            # 检查是否成功连接到视频流
            if not cap.isOpened():
                print("视频流连接失败，尝试重新连接...",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                time.sleep(5)
                continue
            # 开始读取视频帧数据
            ret, frame = cap.read()

            # 如果读取失败，说明连接已经中断，需要重新连接
            if not ret:
                print("图像读取连接中断，尝试重新连接...",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                cap.release()  # 释放原始视频流
                cap = cv2.VideoCapture(self.url)  # 重新连接视频流
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)  # 设置缓存区大小
                time.sleep(5)
                continue

            if ret:
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgbImage.shape
                bytesPerLine = ch * w
                convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
                # 获取屏幕大小并计算四分屏后的每个小部件大小和位置
                screen_rect = QtWidgets.QDesktopWidget().screenGeometry(-1)
                screen_width, screen_height = screen_rect.width(), screen_rect.height()
                self.widget_width = screen_width // 2
                self.widget_height = screen_height // 2
                # print(self.index)
                # print(screen_rect.width(), screen_rect.height())

                # 1024 748
                # print(widget_width, widget_height)

                p = convertToQtFormat.scaled(self.widget_width, self.widget_height, Qt.KeepAspectRatio)
                self.changePixmap.emit(p, self.index)

        cap.release()

    def stop(self):
        self.flag = False


class App(QWidget):

    def __init__(self):
        super().__init__()
        desktop = QApplication.desktop()  # 获取屏幕分辨率
        # print(desktop.width(), desktop.height())
        self.title = 'Four Video Streams'
        self.left = 0
        self.top = 0
        self.width = desktop.width()
        self.height = desktop.height()
        self.initUI()
        self.thread_1 = Thread("rtsp://admin:admin123@70.0.120.141:554/cam/realmonitor?channel=1&subtype=0", 1)
        self.thread_2 = Thread("rtsp://admin:admin123@70.0.120.127:554/cam/realmonitor?channel=1&subtype=0", 2)
        self.thread_3 = Thread("rtsp://admin:fsxgt123@70.0.120.145:554/cam/realmonitor?channel=1&subtype=0", 3)
        self.thread_4 = Thread("rtsp://admin:fsxgt123@70.0.120.144:554/cam/realmonitor?channel=1&subtype=0", 4)
        self.thread_1.changePixmap.connect(self.setImage1)
        self.thread_2.changePixmap.connect(self.setImage2)
        self.thread_3.changePixmap.connect(self.setImage3)
        self.thread_4.changePixmap.connect(self.setImage4)
        self.thread_1.start()
        self.thread_2.start()
        self.thread_3.start()
        self.thread_4.start()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        vbox = QVBoxLayout()

        hbox1 = QHBoxLayout()
        hbox2 = QHBoxLayout()

        self.label1 = QLabel(self)
        self.label2 = QLabel(self)
        self.label3 = QLabel(self)
        self.label4 = QLabel(self)

        hbox1.addWidget(self.label1)
        hbox1.addWidget(self.label2)
        hbox2.addWidget(self.label3)
        hbox2.addWidget(self.label4)

        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)

        self.setLayout(vbox)
        self.show()

    def setImage1(self, image, index):
        if index == 1:
            self.label1.setPixmap(QPixmap.fromImage(image))

    def setImage2(self, image, index):
        if index == 2:
            self.label2.setPixmap(QPixmap.fromImage(image))

    def setImage3(self, image, index):
        if index == 3:
            self.label3.setPixmap(QPixmap.fromImage(image))

    def setImage4(self, image, index):
        if index == 4:
            self.label4.setPixmap(QPixmap.fromImage(image))

    def closeEvent(self, event):
        self.thread_1.stop()
        self.thread_2.stop()
        self.thread_3.stop()
        self.thread_4.stop()

    def keyPressEvent(self, event):
        # 按下Esc键退出程序
        if event.key() == Qt.Key_Escape:
            self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.showFullScreen()
    sys.exit(app.exec_())
    # pyinstaller -F -w main.py
