# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about_win.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
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
    QLabel, QSizePolicy, QVBoxLayout, QWidget)
import about_win_rc

class Ui_About(object):
    def setupUi(self, About):
        if not About.objectName():
            About.setObjectName(u"About")
        About.resize(500, 220)
        self.verticalLayout = QVBoxLayout(About)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(20, 16, 20, 16)
        self.label = QLabel(About)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(14)
        self.label.setFont(font)

        self.verticalLayout.addWidget(self.label)

        self.labelVersion = QLabel(About)
        self.labelVersion.setObjectName(u"labelVersion")
        self.labelVersion.setWordWrap(True)

        self.verticalLayout.addWidget(self.labelVersion)

        self.labelCopyright = QLabel(About)
        self.labelCopyright.setObjectName(u"labelCopyright")

        self.verticalLayout.addWidget(self.labelCopyright)

        self.labelLicence = QLabel(About)
        self.labelLicence.setObjectName(u"labelLicence")
        self.labelLicence.setOpenExternalLinks(True)

        self.verticalLayout.addWidget(self.labelLicence)

        self.buttonBox = QDialogButtonBox(About)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(About)
        self.buttonBox.accepted.connect(About.accept)

        QMetaObject.connectSlotsByName(About)
    # setupUi

    def retranslateUi(self, About):
        About.setWindowTitle(QCoreApplication.translate("About", u"\u00c0 propos", None))
        self.label.setText(QCoreApplication.translate("About", u"Testium", None))
        self.labelVersion.setText("")
        self.labelCopyright.setText(QCoreApplication.translate("About", u"\u00a9 2025-2026 Fran\u00e7ois Dausseur", None))
        self.labelLicence.setText(QCoreApplication.translate("About", u"Licensed under <a href=\"https://eupl.eu/1.2/en/\">EUPL-1.2</a>", None))
    # retranslateUi

