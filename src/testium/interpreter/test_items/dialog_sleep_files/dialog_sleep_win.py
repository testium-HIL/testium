# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_sleep_win.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QApplication, QDateTimeEdit,
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QLayout, QSizePolicy, QSpacerItem, QTimeEdit,
    QVBoxLayout, QWidget)

class Ui_SleepDialogWindow(object):
    def setupUi(self, SleepDialogWindow):
        if not SleepDialogWindow.objectName():
            SleepDialogWindow.setObjectName(u"SleepDialogWindow")
        SleepDialogWindow.resize(493, 124)
        font = QFont()
        font.setFamilies([u"Sans"])
        SleepDialogWindow.setFont(font)
        SleepDialogWindow.setModal(True)
        self.verticalLayout = QVBoxLayout(SleepDialogWindow)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SetMinimumSize)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(SleepDialogWindow)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setFamilies([u"Sans"])
        font1.setPointSize(21)
        self.label.setFont(font1)

        self.horizontalLayout.addWidget(self.label)

        self.timeEdit = QTimeEdit(SleepDialogWindow)
        self.timeEdit.setObjectName(u"timeEdit")
        font2 = QFont()
        font2.setFamilies([u"Sans"])
        font2.setPointSize(24)
        self.timeEdit.setFont(font2)
        self.timeEdit.setFrame(False)
        self.timeEdit.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.timeEdit.setReadOnly(True)
        self.timeEdit.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.timeEdit.setCurrentSection(QDateTimeEdit.HourSection)

        self.horizontalLayout.addWidget(self.timeEdit)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.label_4 = QLabel(SleepDialogWindow)
        self.label_4.setObjectName(u"label_4")
        font3 = QFont()
        font3.setFamilies([u"Sans"])
        font3.setPointSize(10)
        self.label_4.setFont(font3)

        self.horizontalLayout_2.addWidget(self.label_4)

        self.label_3 = QLabel(SleepDialogWindow)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font3)

        self.horizontalLayout_2.addWidget(self.label_3)

        self.label_2 = QLabel(SleepDialogWindow)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font3)

        self.horizontalLayout_2.addWidget(self.label_2)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.buttonBox = QDialogButtonBox(SleepDialogWindow)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(SleepDialogWindow)
        self.buttonBox.accepted.connect(SleepDialogWindow.accept)
        self.buttonBox.rejected.connect(SleepDialogWindow.reject)

        QMetaObject.connectSlotsByName(SleepDialogWindow)
    # setupUi

    def retranslateUi(self, SleepDialogWindow):
        SleepDialogWindow.setWindowTitle(QCoreApplication.translate("SleepDialogWindow", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("SleepDialogWindow", u"Remaining time", None))
        self.timeEdit.setDisplayFormat(QCoreApplication.translate("SleepDialogWindow", u"HH:mm:ss", None))
        self.label_4.setText(QCoreApplication.translate("SleepDialogWindow", u"hr", None))
        self.label_3.setText(QCoreApplication.translate("SleepDialogWindow", u"min", None))
        self.label_2.setText(QCoreApplication.translate("SleepDialogWindow", u"sec", None))
    # retranslateUi

