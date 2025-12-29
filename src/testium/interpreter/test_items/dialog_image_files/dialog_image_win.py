# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_image_win.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QLabel, QSizePolicy, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.setWindowModality(Qt.WindowModal)
        Dialog.resize(700, 600)
        Dialog.setSizeGripEnabled(False)
        Dialog.setModal(True)
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(10, 560, 681, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.labelDialog = QLabel(Dialog)
        self.labelDialog.setObjectName(u"labelDialog")
        self.labelDialog.setGeometry(QRect(10, 10, 681, 71))
        font = QFont()
        font.setPointSize(20)
        self.labelDialog.setFont(font)
        self.labelDialog.setAlignment(Qt.AlignCenter)
        self.labelDialog.setWordWrap(True)
        self.labelImage = QLabel(Dialog)
        self.labelImage.setObjectName(u"labelImage")
        self.labelImage.setGeometry(QRect(10, 80, 681, 471))
        self.labelImage.setAlignment(Qt.AlignCenter)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.labelDialog.setText(QCoreApplication.translate("Dialog", u"TextLabel", None))
        self.labelImage.setText("")
    # retranslateUi

