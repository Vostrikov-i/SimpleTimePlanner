import datetime
import sys
import time
from datetime import datetime
from PySide2.QtCore import QDate, SIGNAL, QObject
from PySide2.QtWidgets import (QTableView, QApplication, QDateEdit, QHeaderView, QCheckBox, QSystemTrayIcon, QStyle)
from PySide2.QtWidgets import (QWidget, QGridLayout, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout, QLabel)
import ClassesPlanner as cPl

buttonData = ["Start", "Pause", "Finish"]
buttonDataFinish = ["Delete"]
TimeZone = (datetime.fromtimestamp(time.time()) - datetime.utcfromtimestamp(time.time())).total_seconds()  #


# Unix Time stamp in hh:mm:ss
def dateFormatFunction(dateUTC):
    if dateUTC is not None:
        date = (int(float(dateUTC) + float(TimeZone)))
        return datetime.utcfromtimestamp(date).strftime('%d-%m-%Y %H:%M:%S')
    return ""


# Seconds to hh:mm:ss format
# f.e. In: workTime = 5400 -> Out: 01:30:00
def workTimeFormat(workTime):
    hours = int((workTime) / 3600)
    minutes = int((workTime - (hours * 3600)) / 60)
    seconds = int(workTime - (hours * 3600 + minutes * 60))
    result = f"{hours}:{minutes}:{seconds}"
    return result


# Mapping for Active Task view
ormMapping = (
    cPl.OrmSettings("id", "taskId", cPl.FieldType.all, "INTEGER", [cPl.dbTypeField.PKEY, cPl.dbTypeField.NOTNULL]),
    cPl.OrmSettings("Name", "taskName", cPl.FieldType.constructor, "STRING", [cPl.dbTypeField.NONE],
                    cPl.ViewMapping.SHOW,
                    "Task Name"),
    cPl.OrmSettings("DateStart", "dateStart", cPl.FieldType.constructor, "INTEGER", [cPl.dbTypeField.NONE],
                    cPl.ViewMapping.SHOW, "Date Add", dateFormatFunction),
    cPl.OrmSettings("DateEnd", "dateEnd", cPl.FieldType.all, "INTEGER", [cPl.dbTypeField.NONE]),
    cPl.OrmSettings("State", "state", cPl.FieldType.all, "STRING", [cPl.dbTypeField.NONE], cPl.ViewMapping.SHOW,
                    "Task State"),
    cPl.OrmSettings("WorkTime", "workTime", cPl.FieldType.constructor, "INTEGER", [cPl.dbTypeField.NONE],
                    cPl.ViewMapping.SHOW, "Work Time", workTimeFormat)
)

# Mapping for Finished Task View
ormMappingFinished = (
    cPl.OrmSettings("id", "taskId", cPl.FieldType.all, "INTEGER", [cPl.dbTypeField.PKEY]),
    cPl.OrmSettings("Name", "taskName", cPl.FieldType.constructor, "STRING", [cPl.dbTypeField.NONE],
                    cPl.ViewMapping.SHOW,
                    "Task Name"),
    cPl.OrmSettings("DateStart", "dateStart", cPl.FieldType.constructor, "INTEGER", [cPl.dbTypeField.NONE],
                    cPl.ViewMapping.SHOW, "Date Add", dateFormatFunction),
    cPl.OrmSettings("DateEnd", "dateEnd", cPl.FieldType.all, "INTEGER", [cPl.dbTypeField.NONE], cPl.ViewMapping.SHOW,
                    "Date End", dateFormatFunction),
    cPl.OrmSettings("State", "state", cPl.FieldType.getter, "STRING", [cPl.dbTypeField.NONE]),
    cPl.OrmSettings("WorkTime", "workTime", cPl.FieldType.constructor, "INTEGER", [cPl.dbTypeField.NONE],
                    cPl.ViewMapping.SHOW, "Work Time", workTimeFormat)
)



class MainWin(QWidget):
    def __init__(self):
        super().__init__()
        self.dbConnector = cPl.DBConnector("timePlanner.db", "Task", ormMapping)
        self.taskStorage = cPl.TaskStorage(self.dbConnector, ormMapping);
        self.currentView = "Work"
        self.check_box = QCheckBox('Minimize to Tray')
        self.check_box.setChecked(True)
        self.createModels()
        self.grid = QGridLayout()
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        traySignal = "activated(QSystemTrayIcon::ActivationReason)"
        QObject.connect(self.tray_icon, SIGNAL(traySignal), self.__icon_activated)
        self.initUI()
        workTimeFormat(86400)

    def hideEvent(self, event):
        if self.check_box.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.show()

    def __icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()

    def __resizeView(self):
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        if self.currentView == "Work":
            self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
            self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
            self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.view.setColumnWidth(1, 140)
            self.view.setColumnWidth(2, 70)
        else:
            self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
            self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
            self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.view.setColumnWidth(1, 140)
            self.view.setColumnWidth(2, 140)

    def initUI(self):
        self.taskStorage.Model = self.model
        grid = self.grid

        self.setLayout(grid)

        buttonCurrent = QPushButton('Current Task')
        buttonCurrent.setCheckable(True)
        buttonFinished = QPushButton('Finished Task')
        buttonFinished.setCheckable(True)
        buttonCurrent.setMaximumWidth(100)
        buttonFinished.setMaximumWidth(100)

        self.move(300, 150)
        self.setMinimumWidth(1100)
        self.setMinimumHeight(400)
        self.setWindowTitle('Time Planner')
        top_Panel = self.createTop()
        grid.addWidget(top_Panel, 0, 0)

        self.view = QTableView();
        self.view.setModel(self.model)
        stylesheet = "QHeaderView::section{color: grey; border: 2px solid #6c6c6c; border-width: 0px 0px 2px 0px; " \
                     "border-style: dotted; border-color: black} "
        self.view.setStyleSheet(stylesheet)
        self.__resizeView()
        self.buttonStart = cPl.StartButtonDelegate(self.taskStorage, "taskId")
        self.buttonPause = cPl.PauseButtonDelegate(self.taskStorage, "taskId")
        self.buttonFinish = cPl.FinishButtonDelegate(self.taskStorage, "taskId")
        self.buttonDelete = cPl.DeleteButtonDelegate(self.taskStorage, "taskId")

        if self.currentView == "Work":
            self.view.setItemDelegateForColumn(self.model.getHeaderLenght(), self.buttonStart)
            self.view.setItemDelegateForColumn(self.model.getHeaderLenght() + 1, self.buttonPause)
            self.view.setItemDelegateForColumn(self.model.getHeaderLenght() + 2, self.buttonFinish)
            buttonCurrent.setChecked(True)
            buttonFinished.setChecked(False)
        else:
            self.view.setItemDelegateForColumn(self.model.getHeaderLenght(), self.buttonDelete)
            buttonCurrent.setChecked(False)
            buttonFinished.setChecked(True)

        viewPanel = self.createTaskView(self.view)
        grid.addWidget(viewPanel, 1, 0)
        buttonPanel = self.createButtonView(self)
        grid.addWidget(buttonPanel, 1, 1)

        grid.addWidget(self.check_box, 2,0)
        self.show()

    # Top panel - LineEdit for task name  + Add new task button
    def createTop(self):
        topPanel = QWidget()
        topPanel.setContentsMargins(0, 0, 0, 0)
        hBox = QHBoxLayout()
        vBox = QVBoxLayout()
        lineEdit = QLineEdit('')
        lineEdit.setPlaceholderText("Enter new task name")
        buttonAdd = QPushButton('Add Task')
        buttonAdd.clicked.connect(self.add_newTask(lineEdit))
        hBox.addWidget(lineEdit)
        lineEdit.setMinimumWidth(250)
        hBox.addWidget(buttonAdd)
        hBox.addStretch(1)
        vBox.addLayout(hBox)
        topPanel.setLayout(vBox)
        return topPanel

    def createTaskView(self, view):
        hBox = QHBoxLayout()
        viewPanel = QWidget()
        hBox.addWidget(view)
        viewPanel.setLayout(hBox)
        return viewPanel

    def createButtonView(self, mainWin):
        buttons = []
        datePickers = []
        buttonPanel = QWidget()
        buttonPanel.setContentsMargins(0, 0, 0, 0)
        buttonCurrent = QPushButton('Current tasks')
        buttonCurrent.setCheckable(True)
        buttonFinished = QPushButton('Finished tasks')
        buttonFinished.setCheckable(True)
        buttonFilter = QPushButton("Filter by end date")
        buttonApply = QPushButton("Apply")
        buttonFilter.setCheckable(True)
        buttonCurrent.setMaximumWidth(100)
        buttonFinished.setMaximumWidth(100)
        buttonFilter.setMaximumWidth(100)
        buttonApply.setMaximumWidth(100)
        buttonCurrent.setMinimumWidth(100)
        buttonFinished.setMinimumWidth(100)
        buttonFilter.setMinimumWidth(100)
        buttonApply.setMinimumWidth(100)
        buttons.append(buttonFilter)

        #
        labelStart = QLabel("Date start")
        datePickers.append(labelStart)
        dateStart = QDateEdit()
        dateStart.setDisplayFormat('dd/MM/yyyy')
        dateStart.setCalendarPopup(True)
        dateStart.setDate(QDate.currentDate())

        datePickers.append(dateStart)
        labelEnd = QLabel("Date end")
        datePickers.append(labelEnd)
        dateEnd = QDateEdit()
        dateEnd.setDisplayFormat('dd/MM/yyyy')
        dateEnd.setCalendarPopup(True)
        dateEnd.setDate(QDate.currentDate())
        datePickers.append(dateEnd)
        datePickers.append(buttonApply)

        buttonCurrent.clicked.connect(self.switchCurrentTask(buttonFinished, buttonCurrent, buttons))
        buttonFinished.clicked.connect(self.switchFinishedTask(buttonCurrent, buttonFinished, buttons))
        buttonFilter.clicked.connect(self.openDatePickerFilter(datePickers, buttonFilter))
        buttonApply.clicked.connect(self.ApplyDateFilterArchive(dateStart, dateEnd))
        buttonCurrent.setChecked(True)

        vBox = QVBoxLayout()
        vBox.addWidget(buttonCurrent)
        vBox.addWidget(buttonFinished)
        vBox.addSpacing(30)
        for bnt in buttons:
            bnt.setVisible(False)
            vBox.addWidget(bnt)
        for datePicker in datePickers:
            datePicker.setVisible(False)
            vBox.addWidget(datePicker)

        vBox.addStretch(1)
        buttonPanel.setLayout(vBox)
        return buttonPanel

    def add_newTask(self, lineEdit):
        def call_sql():
            if lineEdit.text() != "":
                self.taskStorage.addTask(lineEdit.text())
                self.model.update()

        return call_sql

    def openDatePickerFilter(self, filterElements, clickBtn):
        def call():
            if not clickBtn.isChecked():
                for filterElement in filterElements:
                    filterElement.setVisible(False)
                    self.taskStorage.viewAllFinishedTask()
                    self.finishedModel.update()
            else:
                for filterElement in filterElements:
                    filterElement.setVisible(True)

        return call

    def ApplyDateFilterArchive(self, dateStart, dateEnd):
        def call():
            start = datetime.combine(dateStart.date().toPython(), datetime.min.time())
            end = datetime.combine(dateEnd.date().toPython(), datetime.min.time())
            startUTC = int(float(start.timestamp()))
            endUTC = int(float(end.timestamp()))
            self.finishedModel.switchToFilterData(startUTC, endUTC)
            self.finishedModel.update()

        return call

    def switchCurrentTask(self, buttonInAct, btnAct, btnsFilter):
        def call():
            if self.currentView != "Work":
                self.model.setAllTaskView()
                self.view.setModel(self.model)
                self.view.setItemDelegateForColumn(self.model.getHeaderLenght(), self.buttonStart)
                self.view.setItemDelegateForColumn(self.model.getHeaderLenght() + 1, self.buttonPause)
                self.view.setItemDelegateForColumn(self.model.getHeaderLenght() + 2, self.buttonFinish)
                btnAct.setChecked(True)
                buttonInAct.setChecked(False)
                for btn in btnsFilter:
                    btn.setVisible(False)
                self.currentView = "Work"
                self.__resizeView()

        return call

    def switchFinishedTask(self, buttonInAct, btnAct, btnsFilter):
        def call():
            if self.currentView != "Archive":
                self.finishedModel.switchToAllDataView()
                self.view.setModel(self.finishedModel)
                self.view.setItemDelegateForColumn(self.model.getHeaderLenght(), self.buttonDelete)
                btnAct.setChecked(True)
                buttonInAct.setChecked(False)
                for btn in btnsFilter:
                    btn.setVisible(True)
                self.currentView = "Archive"
                self.__resizeView()

        return call

    def createModels(self):
        self.model = cPl.TaskModel(self.taskStorage, ormMapping, buttonData)  # передаем хранилище задач в модель
        self.finishedModel = cPl.FinishedTaskModel(self.taskStorage, ormMappingFinished, buttonDataFinish)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWin()
    sys.exit(app.exec_())
