import sqlite3
import datetime
import time, threading
from collections import OrderedDict
from PySide2.QtGui import *
from PySide2.QtCore import *
from PySide2.QtWidgets import QStyledItemDelegate, QStyleOptionButton, QStyle, QApplication


class FilteredState:
    NoFilter = 0,
    FilterApply = 1


class FieldType:
    getter = 1
    setter = 2
    all = 3  # getter + setter
    constructor = 4


class dbTypeField:
    NONE = ""
    PKEY = "PRIMARY KEY"
    FKEY = "FOREIGN KEY"
    UNIQ = "UNIQUE"
    NOTNULL = "NOT NULL"


class ViewMapping:
    SHOW = 0
    IGNORE = 1


colorBindings = ("state", QBrush(QColor(229, 229, 229)),
                 ("RUN", QBrush(Qt.green)))

class Task:
    def __init__(self, taskName, dateStart, workTime, observer):
        self.__taskName = taskName
        self.__dateStart = dateStart
        self.__dateEnd = None
        self.__taskID = -1
        self.__workTime = workTime
        self.__state = "PAUSED"
        self.__timeout = 10  # frequency refresh work time
        self.__observer = observer
        self.__Timer = None

    @property
    def dateStart(self):
        return self.__dateStart

    @property
    def dateEnd(self):
        return self.__dateEnd

    @property
    def state(self):
        return self.__state

    @property
    def taskId(self):
        if self.__taskID > 0:
            return self.__taskID
        else:
            return -1

    @property
    def taskName(self):
        return self.__taskName

    @dateEnd.setter
    def dateEnd(self, dateEnd):
        if dateEnd is not None and isinstance(dateEnd, int):
            if dateEnd > self.__dateStart:
                self.__dateEnd = dateEnd

    @state.setter
    def state(self, state):
        if state == "" or state == "RUN" or state == "STOP" or state == "PAUSED":
            self.__state = state

    @taskId.setter
    def taskId(self, taskId):
        if (self.__taskID == -1):
            self.__taskID = taskId

    @property
    def workTime(self):
        return self.__workTime

    def startTask(self):
        self.__workTime += self.__timeout
        if self.state != "RUN":
            self.state = "RUN"
            self.__observer.notify(self, ["state"])  # notify storage once
        self.__observer.notify(self, ["workTime"]) # notify storage
        self.__Timer = threading.Timer(self.__timeout, self.startTask)
        self.__Timer.start()

    def pauseTask(self):
        if self.state == "RUN" and self.__Timer is not None and self.__Timer.is_alive():
            self.__Timer.cancel()
        self.state = "PAUSED"
        self.__observer.notify(self, ["state"]) # notify storage

    def stopTask(self):
        if self.__Timer is not None and self.__Timer.is_alive():
            self.__Timer.cancel()
        self.state = "STOP"
        self.__dateEnd = str(time.mktime(datetime.datetime.utcnow().timetuple()))
        self.__observer.notify(self, ["state", "dateEnd"])  # notify storage


class DBConnector:
    def __init__(self, dbPath, tableName, mapping):
        # For create database and table in database
        self.__dbPath = dbPath
        self.__tableName = tableName
        self.__mapping = mapping
        conn = sqlite3.connect(self.__dbPath)
        createFields = ""
        if self.__mapping is not None:
            for element in self.__mapping:
                columnType = ""
                for colType in element.dbFieldType:
                    if colType != dbTypeField.NONE:
                        columnType = str(columnType) + " " + colType
                createFields = createFields + f" {element.dbFieldName} {element.dbFieldDataType} {columnType},"
        createFields = createFields[:-1]
        createQuery = f"CREATE TABLE IF NOT EXISTS {self.__tableName}({createFields});"
        c = conn.cursor()
        c.execute(createQuery)
        conn.commit()
        conn.close()

    def add(self, tableFields, taskValue):

        if len(tableFields) == len(taskValue) and len(tableFields) > 0 and len(taskValue) > 0:
            conn = sqlite3.connect(self.__dbPath)
            c = conn.cursor()
            insTableFields = ""
            for field in tableFields: # Fields to Insert
                insTableFields = insTableFields + field + ", "
            insTableFields=insTableFields[:-2] # Remove 2 last symbols
            tmp = len(taskValue)  # начали формировать значения для вставки в таблицу
            insTableValues = ""
            for value in taskValue: # Values to insert
                insTableValues = insTableValues + " ?, "
            insTableValues = insTableValues[:-2] # Remove 2 last symbols
            # закончили формировать значения для вставки в таблицу
            sqlQuery = f"INSERT INTO {self.__tableName} ({insTableFields}) VALUES({insTableValues})"
            print (sqlQuery)
            c.execute(sqlQuery, taskValue)
            conn.commit();
            id = c.lastrowid;  # получили ID вставленной задачи
            conn.close();  # закрыли соединение с бд
            return id
        else:
            raise ValueError("Not correct fields for insert")

        # values  - словарь, где ключ это название поля в БД, значение это новое значение

    def update(self, update, condition):
        conn = sqlite3.connect(self.__dbPath, timeout=10)
        c = conn.cursor()
        keys = list(update.keys())  # список с ключами
        updateValues = ""
        for key in keys:
            updateValues = updateValues + str(key) + "=\'" + str(update[key]) + "\', "
        updateValues=updateValues[:-2] # Remove 2 last symbols

        if condition != "":
            sqlQuery = f"UPDATE {str(self.__tableName)} SET {updateValues} WHERE {condition}"
        else:
            sqlQuery = f"UPDATE {str(self.__tableName)} SET {updateValues}"
        c.execute(sqlQuery)
        conn.commit()
        conn.close()

    # WARN: is private!!
    def __delete(self, condition):
        conn = sqlite3.connect(self.__dbPath)
        c = conn.cursor()
        if condition != "":
            sqlQuery = f"DELETE FROM {str(self.__tableName)} WHERE {condition}"
        else:
            sqlQuery = f"DELETE FROM {str(self.__tableName)}"  # WARN: delete all row
        c.execute(sqlQuery)
        conn.commit()
        conn.close()

    def deleteById(self, id):
        condition = f"id={id}"
        self.__delete(condition)

    # Get all data from the database matching the condition
    # Data will be returned only if the database contains all the fields described in the dbFields list
    # Returned data example: [[(id, 1), (name, 'name example')], [(id,2), (name, 'name exmple 2')]]
    def getData(self, condition, dbFields):
        conn = sqlite3.connect(self.__dbPath)
        c = conn.cursor()
        if condition != "":
            sqlQuery = f"SELECT * FROM {str(self.__tableName)} WHERE {condition}"
        else:
            sqlQuery = f"SELECT * FROM {str(self.__tableName)}"
        c.execute(sqlQuery)
        fields_names = [name[0] for name in c.description]  # list DB fields
        result_names = []  # временный список
        for field in dbFields:
            result_names.append(next((el for el in fields_names if el == field),
                                     None))  # checking that table contains all fields in dbFields
        if not (None in result_names):
            results = []
            for row in c: # c contain result rows for select query
                fields = [field for field in fields_names]
                values = [values for values in row]
                results.append(zip(fields, values))
            conn.close()
            return results
        else:
            conn.close()
            return None

class TaskStorage:
    def __init__(self, dBConnector, ormMapping):
        self.__taskList = OrderedDict()
        self.__dBConnector = dBConnector
        self.__ormMapping = ormMapping
        self.__Model = None
        self.__primaryObj = None
        self.__filterState = FilteredState.NoFilter
        self.__filteredList = OrderedDict()
        self.__applyedFilter = None;

        for obj in self.__ormMapping:
            for fieldType in obj.dbFieldType:
                if fieldType == dbTypeField.PKEY:  # Primary Key field name
                    self.__primaryObj = obj
        self.__initStorage()
        self.viewActiveTask()

    @property
    def filterState(self):
        return self.__filterState

    @property
    def Model(self):
        return self.__Model

    @Model.setter
    def Model(self, model):
        self.__Model = model

    def addTask(self, taskName):
        insertFields = ["Name", "DateStart", "State", "WorkTime"]
        startTime = str(time.mktime(datetime.datetime.utcnow().timetuple()))
        insertValues = [str(taskName), startTime, "", 0]
        task = Task(taskName, startTime, 0, self)
        task.taskId = self.__dBConnector.add(insertFields, insertValues)
        self.__taskList[
            getattr(task, self.__primaryObj.objectPropertyName)] = task
        if self.__applyedFilter != None:  # refresh filterList
            self.__applyFilter(self.__applyedFilter)

    def deleteTask(self, taskId):
        self.__dBConnector.deleteById(taskId)
        if taskId in self.__taskList:
            del self.__taskList[taskId]
        if self.__applyedFilter != None:  # refresh filterList
            self.__applyFilter(self.__applyedFilter)
        self.__Model.dataChangedInternaly()

    def getTaskFromId(self, taskId):
        return self.__taskList[taskId]

    def getTaskIdFromTask(self, task):
        id = -1
        for key, value in self.taskList.items():
            if value == task:
                id = key
        return id

    def getElementCount(self):
        return len(self.__filteredList)

    # get task from filteredlist (not database)
    def getTaskByNum(self, num):
        taskTuple = tuple(self.__filteredList.items())
        if (num < len(taskTuple)):  # 0 index is task id, 1 index is task
            return taskTuple[num][1]
        return None

    # read task from database and write this in tasklist and filteredlist
    def __initStorage(self):
        self.__taskList.clear()
        dbFieldList = []
        for obj in self.__ormMapping:
            dbFieldList.append(obj.dbFieldName)
        taskDataList = self.__dBConnector.getData("", dbFieldList)  # get data from database
        taskPropDict = OrderedDict()
        # create task
        for taskEl in taskDataList:
            for taskField in taskEl:
                taskPropDict[taskField[0]] = taskField[1]  # data from database

            task = Task(taskPropDict['Name'], taskPropDict['DateStart'], taskPropDict['WorkTime'], self)
            # set other property
            for obj in self.__ormMapping:
                prop = obj.objectPropertyName
                type = obj.objectPropertyType
                if type == FieldType.setter or type == FieldType.all:  # if setter
                    if hasattr(task, prop):
                        setattr(task, prop, taskPropDict[obj.dbFieldName])
            self.__taskList[getattr(task, self.__primaryObj.objectPropertyName)] = task  # append task in tasklist
            for task in self.__taskList.values():
                if task.state == "RUN" or task.state == "":  # pause active task
                    task.pauseTask()

    def __applyFilter(self, filterCondition):
        self.__applyedFilter = filterCondition
        self.__filteredList = dict(filter(filterCondition, self.__taskList.items()))
        if self.__Model != None:
            self.__Model.dataChangedInternaly()
            self.__Model.update()

    # сбросить фильтр
    def clearFilter(self):
        self.__applyedFilter = None
        self.__filterState = FilteredState.NoFilter
        self.__filteredList = self.__taskList

    def viewActiveTask(self):
        self.__applyFilter(lambda task: task[1].state != "STOP")

    def viewAllFinishedTask(self):
        self.__applyFilter(lambda task: task[1].state == "STOP")

    def viewFinishedTaskBetweenDate(self, dateStart, dateEnd):
        self.__applyFilter(
            lambda task: task[1].dateEnd != None and int(float(task[1].dateEnd)) >= int(float(dateStart)) and int(
                float(task[1].dateEnd)) <= int(float(dateEnd)))

    # task notify taskStorage about change data
    def notify(self, object, propertyes):
        updates = dict()
        for property in propertyes:
            if (hasattr(object, property)):
                value = getattr(object, property)
                # UPDATE query for database
                for obj in self.__ormMapping:
                    if obj.objectPropertyName == property:
                        updates[obj.dbFieldName] = value
        if len(updates) > 0:
            if self.__primaryObj != None:
                value = getattr(object, self.__primaryObj.objectPropertyName)
                condition = f"{self.__primaryObj.dbFieldName}=\'{str(value)}\'"
                self.__dBConnector.update(updates, condition)
                if self.__applyedFilter != None:  # refresh __filteredList
                    self.__applyFilter(self.__applyedFilter)
                if self.__Model != None: # refresh model
                    self.__Model.dataChangedInternaly()

class TaskModel(QAbstractTableModel):

    def __init__(self, taskStorage, ormMapping, buttonData=[]):
        super(TaskModel, self).__init__()
        self.__taskStorage = taskStorage
        self.__buttonData = buttonData
        self.__ormMapping = ormMapping
        # create header sign
        self.__taskProp = list(filter(lambda x: x.viewMappingType == ViewMapping.SHOW and type(x.viewHeaderSign) == str,
                                      self.__ormMapping))

    def rowCount(self, index=QModelIndex()):
        return self.__taskStorage.getElementCount()

    def columnCount(self, index=QModelIndex()):
        return len(self.__taskProp) + len(self.__buttonData)  # task column + action buttons

    def setAllTaskView(self):
        self.__taskStorage.viewActiveTask()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if not 0 <= index.row() < self.__taskStorage.getElementCount():
            return None

        i = index.row()
        j = index.column()
        task = self.__taskStorage.getTaskByNum(i)  # get task from storage
        if role == Qt.DisplayRole:
            if (j < len(self.__taskProp)):
                value = getattr(task, self.__taskProp[j].objectPropertyName, None)
                if (self.__taskProp[j].formatFunction != None): # apply format function
                    func = self.__taskProp[j].formatFunction
                    value = func(value)
                return value
            elif len(self.__taskProp) <= j < len(self.__taskProp) + len(self.__buttonData):
                return self.__buttonData[j - len(self.__taskProp)]
        if role == Qt.BackgroundRole:
            # colorBindings
            propetyColor = colorBindings[0]  # header for change color
            defaultColor = colorBindings[1]  #
            dictColors = dict()
            for color in colorBindings:
                if type(color) is tuple:
                    dictColors[color[0]] = color[1]

            for key in dictColors.keys():
                if hasattr(task, propetyColor):
                    if getattr(task, propetyColor, None) == key:
                        return dictColors[key]
            return defaultColor
        return None

    def headerData(self, p_int, orientation, role=None):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if 0 <= p_int < len(self.__taskProp):
                return self.__taskProp[p_int].viewHeaderSign
        return None

    def update(self):
        self.layoutAboutToBeChanged.emit()
        self.layoutChanged.emit()

    def dataChangedInternaly(self):
        self.dataChanged.emit(QModelIndex, QModelIndex, (Qt.BackgroundRole or Qt.DisplayRole))

    # get clicked task id for delegate
    def getClickedTaskId(self, idsPropertyName, rowNum):
        task = self.__taskStorage.getTaskByNum(rowNum)
        value = getattr(task, idsPropertyName, None)  #  return id
        return value

    def getHeaderLenght(self):
        return len(self.__taskProp)


class FinishedTaskModel(QAbstractTableModel):
    # When subclassing QAbstractTableModel, you must implement rowCount(), columnCount(), and data().
    def __init__(self, taskStorage, ormMapping, buttonData=[], parent=None, ):
        super(FinishedTaskModel, self).__init__()
        self.__taskStorage = taskStorage
        self.__buttonData = buttonData
        self.__ormMapping = ormMapping
        self.__taskProp = list(filter(lambda x: x.viewMappingType == ViewMapping.SHOW and type(x.viewHeaderSign) == str,
                                      self.__ormMapping))

    def switchToAllDataView(self):
        self.__taskStorage.viewAllFinishedTask()

    def switchToFilterData(self, dateStart, dateEnd):
        self.__taskStorage.viewFinishedTaskBetweenDate(dateStart, dateEnd)

    def rowCount(self, index=QModelIndex()):
        return self.__taskStorage.getElementCount()

    def columnCount(self, index=QModelIndex()):
        return len(self.__taskProp) + len(self.__buttonData)  # поля задачи + кнопки для управления задачей

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if not 0 <= index.row() < self.__taskStorage.getElementCount():
            return None

        i = index.row()
        j = index.column()
        task = self.__taskStorage.getTaskByNum(i)

        if role == Qt.DisplayRole:
            if (j < len(self.__taskProp)):
                value = getattr(task, self.__taskProp[j].objectPropertyName, None)
                if (self.__taskProp[j].formatFunction != None):
                    func = self.__taskProp[j].formatFunction
                    value = func(value)
                return value
            elif len(self.__taskProp) <= j < len(self.__taskProp) + len(self.__buttonData):
                return self.__buttonData[j - len(self.__taskProp)]
        if role == Qt.BackgroundRole:

            propetyColor = colorBindings[0]
            defaultColor = colorBindings[1]
            dictColors = dict()
            for color in colorBindings:
                if type(color) is tuple:
                    dictColors[color[0]] = color[1]

            for key in dictColors.keys():
                if hasattr(task, propetyColor):
                    if getattr(task, propetyColor, None) == key:
                        return dictColors[key]
            return defaultColor
        return None

    def headerData(self, p_int, orientation, role=None):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if 0 <= p_int < len(self.__taskProp):
                return self.__taskProp[p_int].viewHeaderSign
        return None

    def update(self):
        self.layoutAboutToBeChanged.emit()
        self.layoutChanged.emit()

    def dataChangedInternaly(self):
        self.dataChanged.emit(QModelIndex, QModelIndex, (Qt.BackgroundRole or Qt.DisplayRole))

    def getClickedTaskId(self, idsPropertyName, rowNum):
        task = self.__taskStorage.getTaskByNum(rowNum)
        value = getattr(task, idsPropertyName, None)
        return value

    def getHeaderLenght(self):
        return len(self.__taskProp)


class StartButtonDelegate(QStyledItemDelegate):

    def __init__(self, taskStorage, idPropertyName, parent=None):
        super(StartButtonDelegate, self).__init__(parent)
        self._pressed = None
        self.__taskStorage = taskStorage
        self.__idPropertyName = idPropertyName
        self.__btn = QStyleOptionButton()

    def paint(self, painter, option, index):
        painter.save()
        opt = QStyleOptionButton()
        opt.text = str(index.data())
        opt.rect = option.rect
        opt.palette = option.palette
        task = self.__taskStorage.getTaskByNum(index.row())
        if task.state!="RUN":
            opt.state = QStyle.State_Enabled | QStyle.State_Raised
        else:
            opt.state = QStyle.State_Enabled |  QStyle.State_Sunken
        QApplication.style().drawControl(QStyle.CE_PushButton, opt, painter)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonPress:
            id = model.getClickedTaskId(self.__idPropertyName, index.row())
            task = self.__taskStorage.getTaskFromId(id)

            if self._pressed == (index.row(), index.column()):
                self._pressed = None
            else:
                self._pressed = (index.row(), index.column())
                task.startTask()
            return True
        elif event.type() == QEvent.MouseButtonRelease:
            return True
        else:
            return super(StartButtonDelegate, self).editorEvent(event, model, option, index)


class PauseButtonDelegate(QStyledItemDelegate):

    def __init__(self, taskStorage, idPropertyName, parent=None):
        super(PauseButtonDelegate, self).__init__(parent)
        self._pressed = None
        self.__taskStorage = taskStorage
        self.__idPropertyName = idPropertyName
        self.__btn = QStyleOptionButton()

    def paint(self, painter, option, index):
        painter.save()
        opt = QStyleOptionButton()
        opt.text = str(index.data())
        opt.rect = option.rect
        opt.palette = option.palette
        opt.state = QStyle.State_Enabled | QStyle.State_Raised
        QApplication.style().drawControl(QStyle.CE_PushButton, opt, painter)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonPress:
            id = model.getClickedTaskId(self.__idPropertyName, index.row())
            task = self.__taskStorage.getTaskFromId(id)

            if self._pressed == (index.row(), index.column()):
                self._pressed = None
            else:
                self._pressed = (index.row(), index.column())
                task.pauseTask()
            return True
        elif event.type() == QEvent.MouseButtonRelease:
            return True
        else:
            return super(PauseButtonDelegate, self).editorEvent(event, model, option, index)


class FinishButtonDelegate(QStyledItemDelegate):

    def __init__(self, taskStorage, idPropertyName, parent=None):
        super(FinishButtonDelegate, self).__init__(parent)
        self._pressed = None
        self.__taskStorage = taskStorage
        self.__idPropertyName = idPropertyName
        self.__btn = QStyleOptionButton()

    def paint(self, painter, option, index):
        painter.save()
        opt = QStyleOptionButton()
        opt.text = str(index.data())
        opt.rect = option.rect
        opt.palette = option.palette
        opt.state = QStyle.State_Enabled | QStyle.State_Raised
        QApplication.style().drawControl(QStyle.CE_PushButton, opt, painter)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonPress:
            id = model.getClickedTaskId(self.__idPropertyName, index.row())
            task = self.__taskStorage.getTaskFromId(id)

            if self._pressed == (index.row(), index.column()):
                self._pressed = None
            else:
                self._pressed = (index.row(), index.column())
                task.stopTask()
                model.update()
            return True
        elif event.type() == QEvent.MouseButtonRelease:
            return True
        else:
            return super(FinishButtonDelegate, self).editorEvent(event, model, option, index)


class DeleteButtonDelegate(QStyledItemDelegate):

    def __init__(self, taskStorage, idPropertyName, parent=None):
        super(DeleteButtonDelegate, self).__init__(parent)
        self._pressed = None
        self.__taskStorage = taskStorage
        self.__idPropertyName = idPropertyName
        self.__btn = QStyleOptionButton()

    def paint(self, painter, option, index):
        painter.save()
        opt = QStyleOptionButton()
        opt.text = str(index.data())
        opt.rect = option.rect
        opt.palette = option.palette
        opt.state = QStyle.State_Enabled | QStyle.State_Raised
        QApplication.style().drawControl(QStyle.CE_PushButton, opt, painter)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonPress:
            id = model.getClickedTaskId(self.__idPropertyName, index.row())

            if self._pressed == (index.row(), index.column()):
                self._pressed = None
            else:
                self._pressed = (index.row(), index.column())
                self.__taskStorage.deleteTask(id)
                model.update()
            return True
        elif event.type() == QEvent.MouseButtonRelease:
            return True
        else:
            return super(DeleteButtonDelegate, self).editorEvent(event, model, option, index)



class OrmSettings:
    def __init__(self, dbFieldName, objectPropertyName, objectPropertyType, dbFieldDataType, dbFieldType,
                 viewMappingType=ViewMapping.IGNORE, viewHeaderSign="", formatFunction=None):
        self.__dbFieldName = dbFieldName  # Field Name in DataBase
        self.__objectPropertyName = objectPropertyName  # Property Name in Task object
        self.__objectPropertyType = objectPropertyType  # (getter/setter)
        self.__dbFieldType = dbFieldType  #  PRIMARY_KEY, UNIQ, FOREIGN_KEY
        self.__viewMappingType = viewMappingType  # SHOW or IGNORE this field in View
        self.__viewHeaderSign = viewHeaderSign  # Sign for header this column
        self.__formatFunction = formatFunction  # format function for display data in View
        self.__dbFieldDataType = dbFieldDataType  # Data type for column database

    @property
    def dbFieldName(self):
        return self.__dbFieldName

    @property
    def objectPropertyName(self):
        return self.__objectPropertyName

    @property
    def objectPropertyType(self):
        return self.__objectPropertyType

    @property
    def dbFieldType(self):
        return self.__dbFieldType

    @property
    def viewMappingType(self):
        return self.__viewMappingType

    @property
    def viewHeaderSign(self):
        return self.__viewHeaderSign

    @property
    def formatFunction(self):
        return self.__formatFunction

    @property
    def dbFieldDataType(self):
        return self.__dbFieldDataType