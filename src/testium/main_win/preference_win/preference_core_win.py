# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preference_core_win.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFontComboBox, QFormLayout,
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QScrollArea, QSizePolicy, QSpacerItem,
    QSpinBox, QTabWidget, QToolButton, QVBoxLayout,
    QWidget)

class Ui_preferenceWindow(object):
    def setupUi(self, preferenceWindow):
        if not preferenceWindow.objectName():
            preferenceWindow.setObjectName(u"preferenceWindow")
        preferenceWindow.resize(597, 386)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(preferenceWindow.sizePolicy().hasHeightForWidth())
        preferenceWindow.setSizePolicy(sizePolicy)
        font = QFont()
        font.setFamilies([u"Sans"])
        font.setPointSize(9)
        preferenceWindow.setFont(font)
        self.verticalLayout_2 = QVBoxLayout(preferenceWindow)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.tabWidget = QTabWidget(preferenceWindow)
        self.tabWidget.setObjectName(u"tabWidget")
        font1 = QFont()
        font1.setFamilies([u"Sans"])
        font1.setPointSize(10)
        self.tabWidget.setFont(font1)
        self.tabInterfaceParams = QWidget()
        self.tabInterfaceParams.setObjectName(u"tabInterfaceParams")
        self.verticalLayout = QVBoxLayout(self.tabInterfaceParams)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.scrollArea = QScrollArea(self.tabInterfaceParams)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.NoFrame)
        self.scrollArea.setFrameShadow(QFrame.Sunken)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, -9, 557, 152))
        self.formLayout = QFormLayout(self.scrollAreaWidgetContents)
        self.formLayout.setObjectName(u"formLayout")
        self.label_4 = QLabel(self.scrollAreaWidgetContents)
        self.label_4.setObjectName(u"label_4")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_4)

        self.checkDocPane = QCheckBox(self.scrollAreaWidgetContents)
        self.checkDocPane.setObjectName(u"checkDocPane")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.checkDocPane.sizePolicy().hasHeightForWidth())
        self.checkDocPane.setSizePolicy(sizePolicy1)
        self.checkDocPane.setLayoutDirection(Qt.RightToLeft)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.checkDocPane)

        self.label_5 = QLabel(self.scrollAreaWidgetContents)
        self.label_5.setObjectName(u"label_5")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_5)

        self.checkLogPane = QCheckBox(self.scrollAreaWidgetContents)
        self.checkLogPane.setObjectName(u"checkLogPane")
        sizePolicy1.setHeightForWidth(self.checkLogPane.sizePolicy().hasHeightForWidth())
        self.checkLogPane.setSizePolicy(sizePolicy1)
        self.checkLogPane.setLayoutDirection(Qt.RightToLeft)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.checkLogPane)

        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.checkBoxTest = QCheckBox(self.scrollAreaWidgetContents)
        self.checkBoxTest.setObjectName(u"checkBoxTest")
        sizePolicy1.setHeightForWidth(self.checkBoxTest.sizePolicy().hasHeightForWidth())
        self.checkBoxTest.setSizePolicy(sizePolicy1)
        self.checkBoxTest.setLayoutDirection(Qt.RightToLeft)

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.checkBoxTest)

        self.label_6 = QLabel(self.scrollAreaWidgetContents)
        self.label_6.setObjectName(u"label_6")

        self.formLayout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_6)

        self.checkShowTime = QCheckBox(self.scrollAreaWidgetContents)
        self.checkShowTime.setObjectName(u"checkShowTime")
        sizePolicy1.setHeightForWidth(self.checkShowTime.sizePolicy().hasHeightForWidth())
        self.checkShowTime.setSizePolicy(sizePolicy1)
        self.checkShowTime.setLayoutDirection(Qt.RightToLeft)

        self.formLayout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.checkShowTime)

        self.label_7 = QLabel(self.scrollAreaWidgetContents)
        self.label_7.setObjectName(u"label_7")

        self.formLayout.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_7)

        self.checkDblClick = QCheckBox(self.scrollAreaWidgetContents)
        self.checkDblClick.setObjectName(u"checkDblClick")
        sizePolicy1.setHeightForWidth(self.checkDblClick.sizePolicy().hasHeightForWidth())
        self.checkDblClick.setSizePolicy(sizePolicy1)
        self.checkDblClick.setLayoutDirection(Qt.RightToLeft)

        self.formLayout.setWidget(4, QFormLayout.ItemRole.FieldRole, self.checkDblClick)

        self.choiceIconsTheme = QComboBox(self.scrollAreaWidgetContents)
        self.choiceIconsTheme.addItem("")
        self.choiceIconsTheme.addItem("")
        self.choiceIconsTheme.setObjectName(u"choiceIconsTheme")

        self.formLayout.setWidget(5, QFormLayout.ItemRole.FieldRole, self.choiceIconsTheme)

        self.label_10 = QLabel(self.scrollAreaWidgetContents)
        self.label_10.setObjectName(u"label_10")

        self.formLayout.setWidget(5, QFormLayout.ItemRole.LabelRole, self.label_10)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.scrollArea)

        self.verticalSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.tabWidget.addTab(self.tabInterfaceParams, "")
        self.tabTestParams = QWidget()
        self.tabTestParams.setObjectName(u"tabTestParams")
        self.verticalLayout_3 = QVBoxLayout(self.tabTestParams)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.scrollArea_2 = QScrollArea(self.tabTestParams)
        self.scrollArea_2.setObjectName(u"scrollArea_2")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.scrollArea_2.sizePolicy().hasHeightForWidth())
        self.scrollArea_2.setSizePolicy(sizePolicy2)
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 555, 141))
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.scrollAreaWidgetContents_2.sizePolicy().hasHeightForWidth())
        self.scrollAreaWidgetContents_2.setSizePolicy(sizePolicy3)
        self.formLayout_2 = QFormLayout(self.scrollAreaWidgetContents_2)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.label = QLabel(self.scrollAreaWidgetContents_2)
        self.label.setObjectName(u"label")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy4)

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.editDefaultLogPath = QLineEdit(self.scrollAreaWidgetContents_2)
        self.editDefaultLogPath.setObjectName(u"editDefaultLogPath")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.editDefaultLogPath.sizePolicy().hasHeightForWidth())
        self.editDefaultLogPath.setSizePolicy(sizePolicy5)

        self.horizontalLayout.addWidget(self.editDefaultLogPath)

        self.butLogPath = QToolButton(self.scrollAreaWidgetContents_2)
        self.butLogPath.setObjectName(u"butLogPath")

        self.horizontalLayout.addWidget(self.butLogPath)


        self.formLayout_2.setLayout(0, QFormLayout.ItemRole.FieldRole, self.horizontalLayout)

        self.label_2 = QLabel(self.scrollAreaWidgetContents_2)
        self.label_2.setObjectName(u"label_2")
        sizePolicy4.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy4)

        self.formLayout_2.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_2)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.editDefaultReportPath = QLineEdit(self.scrollAreaWidgetContents_2)
        self.editDefaultReportPath.setObjectName(u"editDefaultReportPath")
        sizePolicy5.setHeightForWidth(self.editDefaultReportPath.sizePolicy().hasHeightForWidth())
        self.editDefaultReportPath.setSizePolicy(sizePolicy5)

        self.horizontalLayout_2.addWidget(self.editDefaultReportPath)

        self.butReportPath = QToolButton(self.scrollAreaWidgetContents_2)
        self.butReportPath.setObjectName(u"butReportPath")

        self.horizontalLayout_2.addWidget(self.butReportPath)


        self.formLayout_2.setLayout(1, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_2)

        self.labelgit = QLabel(self.scrollAreaWidgetContents_2)
        self.labelgit.setObjectName(u"labelgit")

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.LabelRole, self.labelgit)

        self.checkGitSupported = QCheckBox(self.scrollAreaWidgetContents_2)
        self.checkGitSupported.setObjectName(u"checkGitSupported")
        self.checkGitSupported.setLayoutDirection(Qt.RightToLeft)

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.FieldRole, self.checkGitSupported)

        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout_3.addWidget(self.scrollArea_2)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_2)

        self.tabWidget.addTab(self.tabTestParams, "")
        self.tabLog = QWidget()
        self.tabLog.setObjectName(u"tabLog")
        self.verticalLayout_4 = QVBoxLayout(self.tabLog)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.scrollArea_3 = QScrollArea(self.tabLog)
        self.scrollArea_3.setObjectName(u"scrollArea_3")
        sizePolicy5.setHeightForWidth(self.scrollArea_3.sizePolicy().hasHeightForWidth())
        self.scrollArea_3.setSizePolicy(sizePolicy5)
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 555, 72))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents_3)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_8 = QLabel(self.scrollAreaWidgetContents_3)
        self.label_8.setObjectName(u"label_8")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.label_8.sizePolicy().hasHeightForWidth())
        self.label_8.setSizePolicy(sizePolicy6)

        self.gridLayout.addWidget(self.label_8, 0, 0, 1, 1)

        self.font_choice = QFontComboBox(self.scrollAreaWidgetContents_3)
        self.font_choice.setObjectName(u"font_choice")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.font_choice.sizePolicy().hasHeightForWidth())
        self.font_choice.setSizePolicy(sizePolicy7)

        self.gridLayout.addWidget(self.font_choice, 0, 1, 1, 1)

        self.label_9 = QLabel(self.scrollAreaWidgetContents_3)
        self.label_9.setObjectName(u"label_9")

        self.gridLayout.addWidget(self.label_9, 1, 0, 1, 1)

        self.font_size = QSpinBox(self.scrollAreaWidgetContents_3)
        self.font_size.setObjectName(u"font_size")
        self.font_size.setMinimum(1)
        self.font_size.setValue(8)

        self.gridLayout.addWidget(self.font_size, 1, 1, 1, 1)

        self.scrollArea_3.setWidget(self.scrollAreaWidgetContents_3)

        self.verticalLayout_4.addWidget(self.scrollArea_3)

        self.verticalSpacer_3 = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_3)

        self.tabWidget.addTab(self.tabLog, "")

        self.verticalLayout_2.addWidget(self.tabWidget)

        self.buttonBox = QDialogButtonBox(preferenceWindow)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout_2.addWidget(self.buttonBox)


        self.retranslateUi(preferenceWindow)

        self.tabWidget.setCurrentIndex(0)
        self.choiceIconsTheme.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(preferenceWindow)
    # setupUi

    def retranslateUi(self, preferenceWindow):
        preferenceWindow.setWindowTitle(QCoreApplication.translate("preferenceWindow", u"preferenceWindow", None))
        self.label_4.setText(QCoreApplication.translate("preferenceWindow", u"Hide documentation pane", None))
        self.checkDocPane.setText("")
        self.label_5.setText(QCoreApplication.translate("preferenceWindow", u"Hide log pane", None))
        self.checkLogPane.setText("")
        self.label_3.setText(QCoreApplication.translate("preferenceWindow", u"Tests selection available", None))
        self.checkBoxTest.setText("")
        self.label_6.setText(QCoreApplication.translate("preferenceWindow", u"Show step time column (requires restart)", None))
        self.checkShowTime.setText("")
        self.label_7.setText(QCoreApplication.translate("preferenceWindow", u"Test tree item double click enabled", None))
        self.checkDblClick.setText("")
        self.choiceIconsTheme.setItemText(0, QCoreApplication.translate("preferenceWindow", u"Colored icons", None))
        self.choiceIconsTheme.setItemText(1, QCoreApplication.translate("preferenceWindow", u"Black icons", None))

        self.label_10.setText(QCoreApplication.translate("preferenceWindow", u"Icons theme", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabInterfaceParams), QCoreApplication.translate("preferenceWindow", u"Interface parameters", None))
        self.label.setText(QCoreApplication.translate("preferenceWindow", u"Default log files path", None))
        self.butLogPath.setText(QCoreApplication.translate("preferenceWindow", u"...", None))
        self.label_2.setText(QCoreApplication.translate("preferenceWindow", u"Default reports path", None))
        self.butReportPath.setText(QCoreApplication.translate("preferenceWindow", u"...", None))
        self.labelgit.setText(QCoreApplication.translate("preferenceWindow", u"git supported", None))
        self.checkGitSupported.setText("")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabTestParams), QCoreApplication.translate("preferenceWindow", u"Tests parameters", None))
        self.label_8.setText(QCoreApplication.translate("preferenceWindow", u"Font", None))
        self.label_9.setText(QCoreApplication.translate("preferenceWindow", u"Font size", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabLog), QCoreApplication.translate("preferenceWindow", u"Log", None))
    # retranslateUi

