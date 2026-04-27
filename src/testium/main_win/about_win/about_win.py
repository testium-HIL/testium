# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about_win.ui'
##
## Created by: Qt User Interface Compiler version 6.11.0
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
    QFrame, QLabel, QPlainTextEdit, QSizePolicy,
    QWidget)
import about_win_rc

class Ui_About(object):
    def setupUi(self, About):
        if not About.objectName():
            About.setObjectName(u"About")
        About.resize(400, 247)
        self.buttonBox = QDialogButtonBox(About)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(30, 200, 341, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)
        self.label = QLabel(About)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(30, 20, 341, 31))
        font = QFont()
        font.setPointSize(14)
        self.label.setFont(font)
        self.label.setWordWrap(True)
        self.labelVersion = QLabel(About)
        self.labelVersion.setObjectName(u"labelVersion")
        self.labelVersion.setGeometry(QRect(30, 60, 341, 16))
        self.plainTextEdit = QPlainTextEdit(About)
        self.plainTextEdit.setObjectName(u"plainTextEdit")
        self.plainTextEdit.setGeometry(QRect(30, 100, 341, 91))
        self.plainTextEdit.setFrameShape(QFrame.NoFrame)
        self.plainTextEdit.setFrameShadow(QFrame.Sunken)
        self.plainTextEdit.setReadOnly(True)
        self.labelCesUnitVersion = QLabel(About)
        self.labelCesUnitVersion.setObjectName(u"labelCesUnitVersion")
        self.labelCesUnitVersion.setGeometry(QRect(30, 70, 341, 16))

        self.retranslateUi(About)
        self.buttonBox.accepted.connect(About.accept)

        QMetaObject.connectSlotsByName(About)
    # setupUi

    def retranslateUi(self, About):
        About.setWindowTitle(QCoreApplication.translate("About", u"A propos", None))
        self.label.setText(QCoreApplication.translate("About", u"Testium", None))
        self.labelVersion.setText(QCoreApplication.translate("About", u"Version", None))
        self.plainTextEdit.setPlainText(QCoreApplication.translate("About", u"This gui was developed with the help of Qt by Fran\u00e7ois Dausseur.", None))
        self.labelCesUnitVersion.setText(QCoreApplication.translate("About", u"Version", None))
    # retranslateUi

