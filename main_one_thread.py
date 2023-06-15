import sys

import cv2

import untitled
from PyQt5.Qt import *
from PyQt5 import QtWidgets,QtCore,QtGui
from PyQt5.QtWidgets import *
from UI_mainwindow import *
# from predict import predict
from detect1 import dectectVideo,dectectImage

class UiMain(QMainWindow,Ui_MainWindow):
    def __init__(self,parent=None):
        super(UiMain, self).__init__()
        self.setupUi(self)
        self.OpenBtn.clicked.connect(self.loadImage)

    def loadImage(self):
        self.fname, _ = QFileDialog.getOpenFileName(self, 'Open Image', '', 'Image Files (*.png *.jpg *.bmp *.mkv)')
        if self.fname:
            try:
                print(self.fname,type(self.fname))
                self.Infolabel.setText('文件打开成功\n'+ self.fname)

                # 显示画面显示图像,(比例转换全画面)
                # jpg = QtGui.QPixmap(str(self.fname)).scaled(self.Imglablel.width(),self.Imglablel.height())
                # self.Imglablel.setPixmap(jpg)

                # 切割图像,固定尺寸
                # pixmap = QPixmap(self.fname)
                # self.Imglablel.setPixmap(pixmap)

                # rtsp 预测
                # url = 'rtsp://admin:admin123@70.0.120.141:554/cam/realmonitor?channel=1&subtype=0'
                # url = 'e_love_8_62.mp4'
                # dectectVideo(url)

                # 图片的预测
                result = dectectImage(self.fname)
                print(self.fname)
                print(result)

                self.img_rgb = cv2.cvtColor(self.fname,cv2.COLOR_BGR2RGB) # 转换RGB
                self.QtImg = QtGui.QImage(self.img_rgb.data,self.img_rgb.shape[1],self.img_rgb.shape[0],QtGui.QImage.Format_RGB8888)
                self.Imglablel.resize(QtCore.QSize(self.img_rgb.shape[1],self.img_rgb.shape[0]))
                self.Imglablel.setPixmap(QtGui.QPixmap.fromImage(self.QtImg))

                # result = predict(self.fname)

                self.Infolabel.setText('result')
            except Exception as e:
                print(e)

        else:
            print('打开失败')
            self.Infolabel.setText('打开失败')

if __name__ =='__main__':
    app = QApplication(sys.argv)
    ui = UiMain()
    ui.show()
    # ui.showFullScreen()
    sys.exit(app.exec_())