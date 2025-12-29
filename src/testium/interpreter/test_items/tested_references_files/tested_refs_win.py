# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tested_refs_win.ui'
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
    QHeaderView, QLabel, QSizePolicy, QTableWidget,
    QTableWidgetItem, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(481, 386)
        Dialog.setModal(True)
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(10, 350, 461, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.labelDialog = QLabel(Dialog)
        self.labelDialog.setObjectName(u"labelDialog")
        self.labelDialog.setGeometry(QRect(10, 10, 461, 111))
        font = QFont()
        font.setPointSize(20)
        self.labelDialog.setFont(font)
        self.labelDialog.setAlignment(Qt.AlignCenter)
        self.labelDialog.setWordWrap(True)
        self.tableReferences = QTableWidget(Dialog)
        if (self.tableReferences.columnCount() < 3):
            self.tableReferences.setColumnCount(3)
        font1 = QFont()
        font1.setPointSize(10)
        __qtablewidgetitem = QTableWidgetItem()
        __qtablewidgetitem.setFont(font1);
        self.tableReferences.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        __qtablewidgetitem1.setFont(font1);
        self.tableReferences.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        __qtablewidgetitem2.setFont(font1);
        self.tableReferences.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.tableReferences.setObjectName(u"tableReferences")
        self.tableReferences.setGeometry(QRect(10, 130, 461, 211))
        self.tableReferences.setMinimumSize(QSize(461, 0))
        self.tableReferences.setFont(font1)
        self.tableReferences.setAlternatingRowColors(True)
        self.tableReferences.setRowCount(0)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.labelDialog.setText(QCoreApplication.translate("Dialog", u"TextLabel", None))
        ___qtablewidgetitem = self.tableReferences.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("Dialog", u"Reference", None));
        ___qtablewidgetitem1 = self.tableReferences.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("Dialog", u"Revision", None));
        ___qtablewidgetitem2 = self.tableReferences.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("Dialog", u"Serial number", None));
    # retranslateUi

