# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'f1_win_core.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QToolButton, QVBoxLayout,
    QWidget)
import f1_win_rc

class Ui_F1Dialog(object):
    def setupUi(self, F1Dialog):
        if not F1Dialog.objectName():
            F1Dialog.setObjectName(u"F1Dialog")
        F1Dialog.resize(550, 450)
        icon = QIcon()
        if QIcon.hasThemeIcon(QIcon.ThemeIcon.HelpAbout):
            icon = QIcon.fromTheme(QIcon.ThemeIcon.HelpAbout)
        else:
            icon.addFile(u":/icons/testium_logo.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        F1Dialog.setWindowIcon(icon)
        F1Dialog.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.verticalLayout_2 = QVBoxLayout(F1Dialog)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.tabWidget = QTabWidget(F1Dialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabTestItem = QWidget()
        self.tabTestItem.setObjectName(u"tabTestItem")
        self.verticalLayout_tab0 = QVBoxLayout(self.tabTestItem)
        self.verticalLayout_tab0.setObjectName(u"verticalLayout_tab0")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.typeLabel = QLabel(self.tabTestItem)
        self.typeLabel.setObjectName(u"typeLabel")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.typeLabel)

        self.typeLineEdit = QLineEdit(self.tabTestItem)
        self.typeLineEdit.setObjectName(u"typeLineEdit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.typeLineEdit.sizePolicy().hasHeightForWidth())
        self.typeLineEdit.setSizePolicy(sizePolicy)
        self.typeLineEdit.setReadOnly(True)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.typeLineEdit)

        self.sequenceFileNameLabel = QLabel(self.tabTestItem)
        self.sequenceFileNameLabel.setObjectName(u"sequenceFileNameLabel")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.sequenceFileNameLabel)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.sequenceFileNameLineEdit = QLineEdit(self.tabTestItem)
        self.sequenceFileNameLineEdit.setObjectName(u"sequenceFileNameLineEdit")
        self.sequenceFileNameLineEdit.setReadOnly(True)

        self.horizontalLayout_3.addWidget(self.sequenceFileNameLineEdit)

        self.ButtLocOpen = QToolButton(self.tabTestItem)
        self.ButtLocOpen.setObjectName(u"ButtLocOpen")

        self.horizontalLayout_3.addWidget(self.ButtLocOpen)


        self.formLayout.setLayout(1, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_3)


        self.verticalLayout_tab0.addLayout(self.formLayout)

        self.label = QLabel(self.tabTestItem)
        self.label.setObjectName(u"label")

        self.verticalLayout_tab0.addWidget(self.label)

        self.TestContentEdit = QTextEdit(self.tabTestItem)
        self.TestContentEdit.setObjectName(u"TestContentEdit")
        self.TestContentEdit.setReadOnly(True)

        self.verticalLayout_tab0.addWidget(self.TestContentEdit)

        self.tabWidget.addTab(self.tabTestItem, "")
        self.tabVariables = QWidget()
        self.tabVariables.setObjectName(u"tabVariables")
        self.verticalLayout_tab1 = QVBoxLayout(self.tabVariables)
        self.verticalLayout_tab1.setObjectName(u"verticalLayout_tab1")
        self.varsTable = QTableWidget(self.tabVariables)
        if (self.varsTable.columnCount() < 3):
            self.varsTable.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.varsTable.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.varsTable.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.varsTable.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.varsTable.setObjectName(u"varsTable")

        self.verticalLayout_tab1.addWidget(self.varsTable)

        self.addVarLayout = QHBoxLayout()
        self.addVarLayout.setObjectName(u"addVarLayout")
        self.newKeyEdit = QLineEdit(self.tabVariables)
        self.newKeyEdit.setObjectName(u"newKeyEdit")

        self.addVarLayout.addWidget(self.newKeyEdit)

        self.newValueEdit = QLineEdit(self.tabVariables)
        self.newValueEdit.setObjectName(u"newValueEdit")

        self.addVarLayout.addWidget(self.newValueEdit)

        self.addVarButton = QPushButton(self.tabVariables)
        self.addVarButton.setObjectName(u"addVarButton")
        self.addVarButton.setMaximumSize(QSize(30, 16777215))

        self.addVarLayout.addWidget(self.addVarButton)


        self.verticalLayout_tab1.addLayout(self.addVarLayout)

        self.tabWidget.addTab(self.tabVariables, "")

        self.verticalLayout_2.addWidget(self.tabWidget)

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

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(F1Dialog)
    # setupUi

    def retranslateUi(self, F1Dialog):
        F1Dialog.setWindowTitle(QCoreApplication.translate("F1Dialog", u"Test information", None))
        self.typeLabel.setText(QCoreApplication.translate("F1Dialog", u"Test step type", None))
        self.sequenceFileNameLabel.setText(QCoreApplication.translate("F1Dialog", u"Test file name", None))
        self.ButtLocOpen.setText(QCoreApplication.translate("F1Dialog", u"...", None))
        self.label.setText(QCoreApplication.translate("F1Dialog", u"Test content:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabTestItem), QCoreApplication.translate("F1Dialog", u"Test item", None))
        ___qtablewidgetitem = self.varsTable.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("F1Dialog", u"Key", None))
        ___qtablewidgetitem1 = self.varsTable.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("F1Dialog", u"Value", None))
        self.newKeyEdit.setPlaceholderText(QCoreApplication.translate("F1Dialog", u"New key", None))
        self.newValueEdit.setPlaceholderText(QCoreApplication.translate("F1Dialog", u"Value", None))
        self.addVarButton.setText(QCoreApplication.translate("F1Dialog", u"+", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabVariables), QCoreApplication.translate("F1Dialog", u"Variables", None))
        self.ButtClose.setText(QCoreApplication.translate("F1Dialog", u"Close", None))
    # retranslateUi

