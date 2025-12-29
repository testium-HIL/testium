# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'f1_win_core.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTextEdit, QToolButton, QVBoxLayout,
    QWidget)
import f1_win_rc

class Ui_F1Dialog(object):
    def setupUi(self, F1Dialog):
        if not F1Dialog.objectName():
            F1Dialog.setObjectName(u"F1Dialog")
        F1Dialog.resize(400, 300)
        icon = QIcon()
        if QIcon.hasThemeIcon(QIcon.ThemeIcon.HelpAbout):
            icon = QIcon.fromTheme(QIcon.ThemeIcon.HelpAbout)
        else:
            icon.addFile(u":/icons/testium_logo.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        F1Dialog.setWindowIcon(icon)
        F1Dialog.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.verticalLayout_2 = QVBoxLayout(F1Dialog)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")

        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.typeLabel = QLabel(F1Dialog)
        self.typeLabel.setObjectName(u"typeLabel")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.typeLabel)

        self.typeLineEdit = QLineEdit(F1Dialog)
        self.typeLineEdit.setObjectName(u"typeLineEdit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.typeLineEdit.sizePolicy().hasHeightForWidth())
        self.typeLineEdit.setSizePolicy(sizePolicy)
        self.typeLineEdit.setReadOnly(True)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.typeLineEdit)

        self.sequenceFileNameLabel = QLabel(F1Dialog)
        self.sequenceFileNameLabel.setObjectName(u"sequenceFileNameLabel")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.sequenceFileNameLabel)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.sequenceFileNameLineEdit = QLineEdit(F1Dialog)
        self.sequenceFileNameLineEdit.setObjectName(u"sequenceFileNameLineEdit")
        self.sequenceFileNameLineEdit.setReadOnly(True)

        self.horizontalLayout_3.addWidget(self.sequenceFileNameLineEdit)

        self.ButtLocOpen = QToolButton(F1Dialog)
        self.ButtLocOpen.setObjectName(u"ButtLocOpen")

        self.horizontalLayout_3.addWidget(self.ButtLocOpen)


        self.formLayout.setLayout(1, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_3)


        self.verticalLayout_2.addLayout(self.formLayout)

        self.label = QLabel(F1Dialog)
        self.label.setObjectName(u"label")

        self.verticalLayout_2.addWidget(self.label)

        self.TestContentEdit = QTextEdit(F1Dialog)
        self.TestContentEdit.setObjectName(u"TestContentEdit")
        self.TestContentEdit.setReadOnly(True)

        self.verticalLayout_2.addWidget(self.TestContentEdit)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.ButtClose = QPushButton(F1Dialog)
        self.ButtClose.setObjectName(u"ButtClose")
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.WindowClose))
        self.ButtClose.setIcon(icon1)

        self.horizontalLayout.addWidget(self.ButtClose)


        self.verticalLayout_2.addLayout(self.horizontalLayout)


        self.retranslateUi(F1Dialog)

        QMetaObject.connectSlotsByName(F1Dialog)
    # setupUi

    def retranslateUi(self, F1Dialog):
        F1Dialog.setWindowTitle(QCoreApplication.translate("F1Dialog", u"Test information", None))
        self.typeLabel.setText(QCoreApplication.translate("F1Dialog", u"Test step type", None))
        self.sequenceFileNameLabel.setText(QCoreApplication.translate("F1Dialog", u"Test file name", None))
        self.ButtLocOpen.setText(QCoreApplication.translate("F1Dialog", u"...", None))
        self.label.setText(QCoreApplication.translate("F1Dialog", u"Test content:", None))
        self.ButtClose.setText(QCoreApplication.translate("F1Dialog", u"Close", None))
    # retranslateUi

