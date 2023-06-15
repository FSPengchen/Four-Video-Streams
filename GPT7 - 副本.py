# 用python 使用pyqt5与opencv显示4个RTSP,采用四分屏显示上下左右面积相等,用来显示，断线重连，降低视频延时，以避免OpenCV库的频闪问题，并在稳定运行情况下，降低CPU及内存使用量
# https://pypi.tuna.tsinghua.edu.cn/simple  pip install opencv-python
import sys
import time
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt5 import QtGui, QtCore, QtWidgets
import cv2
import detect
import argparse
import os
import platform
import sys
from pathlib import Path
import argparse
import os
import sys
from pathlib import Path

import torch
import torch.backends.cudnn as cudnn

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from utils.general import (LOGGER, Profile, check_file, check_img_size, check_imshow, check_requirements, colorstr, cv2,
                           increment_path, non_max_suppression, print_args, scale_boxes, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device, smart_inference_mode



class Thread(QThread):
    changePixmap = pyqtSignal(QImage, int)
    started_signal = pyqtSignal()
    finished_signal = pyqtSignal()

    def __init__(self, url, index, color):
        super().__init__()
        self.url = url
        self.index = index
        self.color = color
        self._is_paused = False
        self.is_running = True
        self.flag = True


    def run(self):
        # if self.index == 1:
        #     source = "rtsp://admin:admin123@70.0.120.141:554/cam/realmonitor?channel=1&subtype=0"
        #     weights = ROOT / 'best.pt'
        # elif self.index == 2:
        #     source = "rtsp://admin:admin123@70.0.120.122:554/cam/realmonitor?channel=1&subtype=0"
        #     weights = ROOT / 'best.pt'
        # elif self.index == 3:
        #     source = "rtsp://admin:fsxgt123@70.0.120.145:554/cam/realmonitor?channel=1&subtype=0"
        #     weights = ROOT / 'best.pt'
        # elif self.index == 4:
        #     source = "rtsp://admin:fsxgt123@70.0.120.144:554/cam/realmonitor?channel=1&subtype=0"
        #     weights = ROOT / 'best.pt'
        # elif self.index == 5:
        #     source = "rtsp://admin:fsxgt123@70.0.120.146:554/cam/realmonitor?channel=1&subtype=0"
        #     weights = ROOT / 'best.pt'
        # elif self.index == 6:
        #     source = "rtsp://admin:admin123@70.0.120.147:554/cam/realmonitor?channel=1&subtype=0"
        #     weights = ROOT / 'best.pt'
        # else:
        #     print('异常')
        #     source = "rtsp://admin:admin123@70.0.120.127:554/cam/realmonitor?channel=1&subtype=0"
        #     weights = ROOT / 'best.pt'

        print('线程初始化')
        source = self.url
        weights = ROOT / 'best.pt'
        source = str(source)
        save_dir = increment_path(Path(ROOT / 'runs/detect') / 'exp', exist_ok=False)
        # (save_dir / 'labels').mkdir(parents=True, exist_ok=True)
        device = select_device('')
        model = DetectMultiBackend(weights, device=device, dnn=False, data=ROOT / 'data/coco128.yaml', fp16=False)
        stride, names, pt = model.stride, model.names, model.pt
        imgsz = check_img_size((640, 640), s=stride)

        # Dataloader
        print('装载模型')
        bs = 1
        view_img = True
        dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=1)
        bs = len(dataset)
        vid_path, vid_writer = [None] * bs, [None] * bs

        # Run inference
        print('运行推理')
        model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))  # warmup
        seen, windows, dt = 0, [], (Profile(), Profile(), Profile())

        self.started_signal.emit()
        while self.is_running:
            print('线程运行',self._is_paused,self.index)
            if self._is_paused:
                time.sleep(1)
                continue

            for path, im, im0s, vid_cap, s in dataset:
                with dt[0]:
                    im = torch.from_numpy(im).to(model.device)
                    im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
                    im /= 255  # 0 - 255 to 0.0 - 1.0
                    if len(im.shape) == 3:
                        im = im[None]  # expand for batch dim

                # Inference
                # print('Inference')
                with dt[1]:
                    print('pred')
                    pred = model(im, augment=False, visualize=False)
                    print('pred end')

                # NMS
                # print('NMS')
                with dt[2]:
                    pred = non_max_suppression(pred, 0.25, 0.45, None, False, max_det=3)

                # Process predictions
                # print('Process predictions')
                for i, det in enumerate(pred):  # per image
                    # print('pred', pred)
                    seen += 1
                    p, im0, frame = path[i], im0s[i].copy(), dataset.count
                    s += f'{i}: '

                    p = Path(p)  # to Path
                    save_path = str(save_dir / p.name)  # im.jpg
                    txt_path = str(save_dir / 'labels' / p.stem) + (
                        '' if dataset.mode == 'image' else f'_{frame}')  # im.txt
                    s += '%gx%g ' % im.shape[2:]  # print string
                    gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
                    imc = im0.copy()  # for save_crop
                    annotator = Annotator(im0, line_width=3, example=str(names))
                    if len(det):
                        # Rescale boxes from img_size to im0 size
                        det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                        # Print results
                        for c in det[:, 5].unique():
                            n = (det[:, 5] == c).sum()  # detections per class
                            s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                        # Write results
                        for *xyxy, conf, cls in reversed(det):
                            c = int(cls)  # integer class
                            label = None if False else (names[c] if False else f'{names[c]} {conf:.2f}')
                            annotator.box_label(xyxy, label, color=colors(c, True))


                    # Stream results
                    im0 = annotator.result()
                    # print(type(im0),im0)
                    # if view_img:
                    #     if platform.system() == 'Linux' and p not in windows:
                    #         windows.append(p)
                    #         cv2.namedWindow(str(p),
                    #                         cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
                    #         cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])

                    frame = im0
                    rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # 绘制视频边框
                    if self.index == 1:
                        rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
                                                 thickness=5)
                    elif self.index == 2:
                        rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
                                                 thickness=5)
                    elif self.index == 3:
                        rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
                                                 thickness=5)
                    elif self.index == 4:
                        rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
                                                 thickness=5)
                    elif self.index == 5:
                        rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
                                                 thickness=5)
                    elif self.index == 6:
                        rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
                                                 thickness=5)

                    # print(self.index,rgbImage.shape)

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

            #
            # cap = cv2.VideoCapture(self.url)
            # cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)
            # while self.flag:
            #     # 检查是否成功连接到视频流
            #     if not cap.isOpened():
            #         print("视频流连接失败，尝试重新连接...", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            #               self.index)
            #         time.sleep(5)
            #         continue
            #     # 开始读取视频帧数据
            #     ret, frame = cap.read()
            #
            #     # 如果读取失败，说明连接已经中断，需要重新连接
            #     if not ret:
            #         print("图像读取连接中断，尝试重新连接...", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            #               self.index)
            #         cap.release()  # 释放原始视频流
            #         cap = cv2.VideoCapture(self.url)  # 重新连接视频流
            #         cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)  # 设置缓存区大小
            #         time.sleep(5)
            #         continue
            #
            #     if ret:
            #         rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            #
            #         # 绘制视频边框
            #         if self.index == 1:
            #             rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
            #                                      thickness=5)
            #         elif self.index == 2:
            #             rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
            #                                      thickness=5)
            #         elif self.index == 3:
            #             rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
            #                                      thickness=5)
            #         elif self.index == 4:
            #             rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
            #                                      thickness=5)
            #         elif self.index == 5:
            #             rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
            #                                      thickness=5)
            #         elif self.index == 6:
            #             rgbImage = cv2.rectangle(rgbImage, (0, 0), (frame.shape[1], frame.shape[0]), self.color,
            #                                      thickness=5)
            #
            #         # print(self.index,rgbImage.shape)
            #
            #         h, w, ch = rgbImage.shape
            #         bytesPerLine = ch * w
            #         convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
            #         # 获取屏幕大小并计算四分屏后的每个小部件大小和位置
            #         screen_rect = QtWidgets.QDesktopWidget().screenGeometry(-1)
            #         screen_width, screen_height = screen_rect.width(), screen_rect.height()
            #         self.widget_width = screen_width // 2
            #         self.widget_height = screen_height // 2
            #         # print(self.index)
            #         # print(screen_rect.width(), screen_rect.height())
            #
            #         # 1024 748
            #         # print(widget_width, widget_height)
            #
            #         p = convertToQtFormat.scaled(self.widget_width, self.widget_height, Qt.KeepAspectRatio)
            #         self.changePixmap.emit(p, self.index)

            # cap.release()

        self.finished_signal.emit()

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def stop(self):
        self.is_running = False
        self._is_paused = False
        self.flag = True


class App(QWidget):

    def __init__(self, *arg, **kwargs):
        super().__init__()
        desktop = QApplication.desktop()  # 获取屏幕分辨率
        # print(desktop.width(), desktop.height())
        self.loction = 1
        self.title = 'Four Video Streams'
        self.left = 0
        self.top = 0
        self.width = desktop.width()
        self.height = desktop.height()
        self.initUI()
        self.thread_1 = Thread("rtsp://admin:admin123@70.0.120.141:554/cam/realmonitor?channel=1&subtype=0", 1,
                               color=(0, 0, 0))
        # self.thread_2 = Thread("rtsp://admin:admin123@70.0.120.127:554/cam/realmonitor?channel=1&subtype=0", 2)
        self.thread_2 = Thread("rtsp://admin:admin123@70.0.120.122:554/cam/realmonitor?channel=1&subtype=0", 2,
                               color=(0, 0, 0))
        self.thread_3 = Thread("rtsp://admin:fsxgt123@70.0.120.145:554/cam/realmonitor?channel=1&subtype=0", 3,
                               color=(0, 0, 0))
        self.thread_4 = Thread("rtsp://admin:fsxgt123@70.0.120.144:554/cam/realmonitor?channel=1&subtype=0", 4,
                               color=(0, 0, 0))
        self.thread_5 = Thread("rtsp://admin:fsxgt123@70.0.120.146:554/cam/realmonitor?channel=1&subtype=0", 5,
                               color=(0, 0, 0))
        self.thread_6 = Thread("rtsp://admin:admin123@70.0.120.147:554/cam/realmonitor?channel=1&subtype=0", 6,
                               color=(0, 0, 0))

        # 将按键0与change_color函数绑定
        # self.key_0 = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_0), self)
        # self.key_0.activated.connect(self.change_color)

        self.thread_1.changePixmap.connect(self.setImage1)
        self.thread_2.changePixmap.connect(self.setImage2)
        self.thread_3.changePixmap.connect(self.setImage3)
        self.thread_4.changePixmap.connect(self.setImage4)
        self.thread_5.changePixmap.connect(self.setImage3)
        self.thread_6.changePixmap.connect(self.setImage4)

        self.thread_1.started_signal.connect(self.on_thread_started)
        self.thread_1.finished_signal.connect(self.on_thread_finished)
        self.thread_2.started_signal.connect(self.on_thread_started)
        self.thread_2.finished_signal.connect(self.on_thread_finished)
        self.thread_3.started_signal.connect(self.on_thread_started)
        self.thread_3.finished_signal.connect(self.on_thread_finished)
        self.thread_4.started_signal.connect(self.on_thread_started)
        self.thread_4.finished_signal.connect(self.on_thread_finished)
        self.thread_5.started_signal.connect(self.on_thread_started)
        self.thread_5.finished_signal.connect(self.on_thread_finished)
        self.thread_6.started_signal.connect(self.on_thread_started)
        self.thread_6.finished_signal.connect(self.on_thread_finished)

        self.thread_1.start()
        self.thread_2.start()
        self.thread_3.start()
        self.thread_4.start()
        self.thread_5.start()
        self.thread_6.start()

        if self.loction == 2:
            self.thread_3.pause()
            self.thread_4.pause()
        else:
            self.thread_5.pause()
            self.thread_6.pause()

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
        if self.loction == 1:
            if index == 3:
                self.label3.setPixmap(QPixmap.fromImage(image))
        else:
            if index == 5:
                self.label3.setPixmap(QPixmap.fromImage(image))

    def setImage4(self, image, index):
        if self.loction == 1:
            if index == 4:
                self.label4.setPixmap(QPixmap.fromImage(image))
        else:
            if index == 6:
                self.label4.setPixmap(QPixmap.fromImage(image))

    def closeEvent(self, event):
        self.thread_1.stop()
        self.thread_2.stop()
        self.thread_3.stop()
        self.thread_4.stop()
        self.thread_5.stop()
        self.thread_6.stop()

    def on_thread_started(self):
        print("Thread started")

    def on_thread_finished(self):
        print("Thread finished")

    def keyPressEvent(self, event):
        global color_1
        global color_2
        global color_3
        global color_4
        global color_5
        global color_6
        # 按下Esc键退出程序
        if event.key() == Qt.Key_Escape:
            self.close()

        if event.key() == Qt.Key_2:
            self.thread_3.is_running = True
            self.thread_3.flag = True
            self.thread_3.start()

        if event.key() == Qt.Key_3:
            self.loction = 2
            self.thread_3.pause()
            self.thread_3.flag = False
            self.thread_4.pause()
            self.thread_4.flag = False

            self.thread_5.flag = True
            self.thread_5.resume()
            self.thread_6.flag = True
            self.thread_6.resume()

        if event.key() == Qt.Key_4:
            self.loction = 1
            self.thread_5.pause()
            self.thread_5.flag = False
            self.thread_6.pause()
            self.thread_6.flag = False

            self.thread_3.flag = True
            self.thread_3.resume()
            self.thread_4.flag = True
            self.thread_4.resume()

        if event.key() == Qt.Key_5:
            self.thread_3.flag = False
            self.thread_3.stop()

        if event.key() == Qt.Key_0:
            # 改变颜色
            self.thread_1.color = (0, 255, 0)
            self.thread_2.color = (0, 255, 0)
            self.thread_3.color = (0, 255, 0)
            self.thread_4.color = (0, 255, 0)
            self.thread_5.color = (0, 255, 0)
            self.thread_6.color = (0, 255, 0)
        if event.key() == Qt.Key_9:
            # 改变颜色
            self.thread_1.color = (255, 0, 0)
            self.thread_2.color = (255, 0, 0)
            self.thread_3.color = (255, 0, 0)
            self.thread_4.color = (255, 0, 0)
            self.thread_5.color = (255, 0, 0)
            self.thread_6.color = (255, 0, 0)


if __name__ == '__main__':
    # opt = detect.parse_opt()
    # detect.main(opt)
    app = QApplication(sys.argv)
    ex = App()
    ex.showFullScreen()
    sys.exit(app.exec_())
    # pyinstaller -F -w main.py
