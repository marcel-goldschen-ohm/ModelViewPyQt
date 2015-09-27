""" ObjectListTableModelViewQt.py: Qt model/view for editing specified attributes from a dynamic list of objects.

For when you have a list of objects all of the same type, and you want to view and/or edit specified attributes
in a table where each row is an object and each column an attribute (or optionally vice-versa).

Right clicking in the view's row or column headers brings up a context menu for inserting/deleting/moving objects
in the list (optional), or setting an attribute's value for all objects simultaneously.

Displayed properties are specified as a list of dicts. For example:
    properties = [
        {'attr': "name",        'header': "Person", 'isReadOnly': True},  # Read only column of object.name strings.
        {'attr': "age",         'header': "Age"                       },  # Read/Write column of object.age integers.
        {'attr': "birthday",    'header': "D.O.B.", 'text': "%x"      },  # Read/Write column of object.birthday datetimes (format="%x").
        {'attr': "friend.name", 'header': "Friend"                    }]  # Read/Write column of object.friend.name strings.

author: Marcel Goldschen-Ohm
email: <marcel.goldschen@gmail.com>
"""


import copy
from datetime import datetime
try:
    from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QT_VERSION_STR
    from PyQt5.QtWidgets import QTableView, QMenu, QInputDialog, QErrorMessage, QDialog, QDialogButtonBox, QVBoxLayout
except ImportError:
    try:
        from PyQt4.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QT_VERSION_STR, QString
        from PyQt4.QtGui import QTableView, QMenu, QInputDialog, QErrorMessage, QDialog, QDialogButtonBox, QVBoxLayout
    except ImportError:
        raise ImportError("ObjectListTableModelViewQt: Requires PyQt5 or PyQt4.")
from CheckBoxDelegateQt import CheckBoxDelegateQt
from FloatEditDelegateQt import FloatEditDelegateQt
from DateTimeEditDelegateQt import DateTimeEditDelegateQt
from ComboBoxDelegateQt import ComboBoxDelegateQt
from PushButtonDelegateQt import PushButtonDelegateQt
from FileDialogDelegateQt import FileDialogDelegateQt


__author__ = "Marcel Goldschen-Ohm <marcel.goldschen@gmail.com>"


def getAttrRecursive(obj, attr):
    """ Recursive introspection (i.e. get the member 'b' of a member 'a' by name as 'a.b').
    """
    try:
        p = attr.index(".")
        obj = getattr(obj, attr[0:p])
        return getAttrRecursive(obj, attr[p+1:])
    except ValueError:
        return getattr(obj, attr)


def setAttrRecursive(obj, attr, value):
    """ Recursive introspection (i.e. set the member 'b' of a member 'a' by name as 'a.b').
    """
    try:
        p = attr.index(".")
        obj = getattr(obj, attr[0:p])
        setAttrRecursive(obj, attr[p+1:], value)
    except ValueError:
        setattr(obj, attr, value)


class ObjectListTableModelQt(QAbstractTableModel):
    """ Qt model interface for specified attributes from a dynamic list of arbitrary objects.

    All objects in the list should be of the same type.
    Default is objects are rows and properties are columns.

    Displayed properties are specified as a list of dicts whose keys may include:
    'attr': Name of an object attribute. If specified, data() and setData() will get/set the attribute's value
        for the associated object.
        - May be a path to a child attribute such as "path.to.a.child.attr".
    'header': Text to display in the table's property header.
    'dtype': Attribute type. If not specified, this is inferred either from the templateObject or an object in the list.
    'mode': "Read/Write" or "Read Only". If not specified, defaults to "Read/Write".
    'choices': List of values or (key, value) tuples. If specified, the values (or their keys if they exist) are presented in a combo box.
    'action': Name of a special action associated with this cell. Actions include:
        "button": Clicking on the cell is treated as a button press.
            - setData() calls the object's method specified by the property's 'attr' key.
        "fileDialog": Double clicking on the cell pops up a file dialog.
            - setData() sets the property's 'attr' value to the "path/to/filename" returned form the dialog.
            - If you want some file loading script to run each time the file name is set, set 'attr' to the object
              @property.setter that set's the file name and runs the script.
    'text': String used by certain properties. For example, used to specify a datetime's format or a button's text.

    By specifying each object property (or action) displayed in the model/view as a dict,
    it is easy to simply add new key:value pairs for new custom delegates, and extend the model/view
    code to check for these properties. Furthermore, specifying properties in this way makes for
    easily readable code when adding properties to a model/view. For example:
        properties = [
            {'attr': "name",        'header': "Person", 'isReadOnly': True},  # Read only column of object.name strings.
            {'attr': "age",         'header': "Age"                       },  # Read/Write column of object.age integers.
            {'attr': "birthday",    'header': "D.O.B.", 'text': "%x"      },  # Read/Write column of object.birthday datetimes (format="%x").
            {'attr': "friend.name", 'header': "Friend"                    }]  # Read/Write column of object.friend.name strings.

    :param objects (list): List of objects.
    :param properties (list): List of property dicts {'attr'=str, 'header'=str, 'isReadOnly'=bool, 'choices'=[], ...}
    :param isRowObjects (bool): If True, objects are rows and properties are columns, otherwise vice-versa.
    :param isDynamic (bool): If True, objects can be inserted/deleted, otherwise not.
    :param templateObject (object): Object that will be deep copied to create new objects when inserting into the list.
    """
    def __init__(self, objects=None, properties=None, isRowObjects=True, isDynamic=True, templateObject=None, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.objects = objects if (objects is not None) else []
        self.properties = properties if (properties is not None) else []
        self.isRowObjects = isRowObjects
        self.isDynamic = isDynamic
        self.templateObject = templateObject

    def getObject(self, index):
        if not index.isValid():
            return None
        objectIndex = index.row() if self.isRowObjects else index.column()
        try:
            return self.objects[objectIndex]
        except IndexError:
            return None

    def getProperty(self, index):
        if not index.isValid():
            return None
        propertyIndex = index.column() if self.isRowObjects else index.row()
        try:
            return self.properties[propertyIndex]
        except IndexError:
            return None

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self.objects) if self.isRowObjects else len(self.properties)

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self.properties) if self.isRowObjects else len(self.objects)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        obj = self.getObject(index)
        prop = self.getProperty(index)
        if (obj is None) or (prop is None):
            return None
        try:
            if role in [Qt.DisplayRole, Qt.EditRole]:
                return getAttrRecursive(obj, prop['attr'])
        except:
            return None
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        obj = self.getObject(index)
        prop = self.getProperty(index)
        if (obj is None) or (prop is None):
            return None
        try:
            action = prop.get('action', None)
            if action is not None:
                if action == "button":
                    getAttrRecursive(obj, prop['attr'])()  # Call obj.attr()
                    return True
                elif action == "fileDialog":
                    pass  # File loading handled via @property.setter obj.attr below. Otherwise just sets the file name text.
            if role == Qt.EditRole:
                if type(value) == QVariant:
                    value = value.toPyObject()
                if (QT_VERSION_STR[0] == '4') and (type(value) == QString):
                    value = str(value)
                setAttrRecursive(obj, prop['attr'], value)
                return True
        except:
            return False
        return False

    def flags(self, index):
        flags = QAbstractTableModel.flags(self, index)
        if not index.isValid():
            return flags
        prop = self.getProperty(index)
        if prop is None:
            return flags
        flags |= Qt.ItemIsEnabled
        flags |= Qt.ItemIsSelectable
        mode = prop.get('mode', "Read/Write")
        if "Write" in mode:
            flags |= Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if ((orientation == Qt.Horizontal) and self.isRowObjects) or ((orientation == Qt.Vertical) and not self.isRowObjects):
            # Display property headers.
            try:
                return self.properties[section]['header']  # Property header.
            except (IndexError, KeyError):
                return None
        else:
            # Display object indices (1-based).
            return (section + 1) if (0 <= section < len(self.objects)) else None

    def insertObjects(self, i, num=1):
        if ((len(self.objects) == 0) and (self.templateObject is None)) or (num <= 0):
            return False
        i = min([max([0, i]), len(self.objects)])  # Clamp i to within [0, # of objects].
        if self.isRowObjects:
            self.beginInsertRows(QModelIndex(), i, i + num - 1)
        else:
            self.beginInsertColumns(QModelIndex(), i, i + num - 1)
        for objectIndex in range(i, i + num):
            if self.templateObject is not None:
                self.objects.insert(objectIndex, copy.deepcopy(self.templateObject))
            elif len(self.objects):
                copyIndex = min([max([0, objectIndex]), len(self.objects) - 1])  # Clamp objectIndex to a valid object index.
                self.objects.insert(objectIndex, copy.deepcopy(self.objects[copyIndex]))
        if self.isRowObjects:
            self.endInsertRows()
        else:
            self.endInsertColumns()
        return True

    def removeObjects(self, i, num=1):
        if (len(self.objects) == 0) or (num <= 0):
            return False
        i = min([max([0, i]), len(self.objects) - 1])  # Clamp i to a valid object index.
        num = min([num, len(self.objects) - i])  # Clamp num to a valid number of objects.
        if num == len(self.objects):
            # Make sure we have a template for inserting objects later.
            if self.templateObject is None:
                self.templateObject = self.objects[0]
        if self.isRowObjects:
            self.beginRemoveRows(QModelIndex(), i, i + num - 1)
            del self.objects[i:i+num]
            self.endRemoveRows()
        else:
            self.beginRemoveColumns(QModelIndex(), i, i + num - 1)
            del self.objects[i:i+num]
            self.endRemoveColumns()
        return True

    def moveObjects(self, indices, moveToIndex):
        if len(self.objects) <= 1:
            return False
        try:
            if type(indices) is not list:
                indices = list(indices)
            for i, idx in enumerate(indices):
                indices[i] = min([max([0, idx]), len(self.objects) - 1])  # Clamp indices to valid object indices.
            moveToIndex = min([max([0, moveToIndex]), len(self.objects) - 1])  # Clamp moveToIndex to a valid object index.
            self.beginResetModel()
            objectsToMove = []
            for i in indices:
                objectsToMove.append(self.objects[i])
            for i in reversed(indices):
                del self.objects[i]
            for i, obj in enumerate(objectsToMove):
                j = moveToIndex + i
                j = min([max([0, j]), len(self.objects)])  # Clamp j to within [0, # of objects].
                self.objects.insert(j, obj)
            self.endResetModel()
            return True
        except:
            return False

    def clearObjects(self):
        if len(self.objects):
            if self.templateObject is None:
                self.templateObject = self.objects[0]
            self.beginResetModel()
            del self.objects[:]
            self.endResetModel()

    def propertyType(self, propertyIndex):
        try:
            prop = self.properties[propertyIndex]
            if 'dtype' in prop.keys():
                return prop['dtype']
            elif 'attr' in prop.keys():
                if self.templateObject is not None:
                    return type(getAttrRecursive(self.templateObject, prop['attr']))
                elif len(self.objects) > 0:
                    return type(getAttrRecursive(self.objects[0], prop['attr']))
        except:
            return None
        return None


class ObjectListTableViewQt(QTableView):
    """ Qt view for a ObjectListTableModelQt model.

    Right clicking in the view's row or column headers brings up a context menu for inserting/deleting/moving objects
    in the list (optional), or setting an attribute's value for all objects simultaneously.

    Delegates:
    bool: CheckBoxWithoutLabelDelegateQt() - centered check box (no label)
    float: FloatEditDelegateQt() - allows arbitrary precision and scientific notation
    datetime: DateTimeEditDelegateQt("date format") - datetime displayed according to "date format"
    combobox: ComboBoxDelegateQt([choice values or (key, value) tuples]) - list of choice values (or keys if they exist)
    buttons: PushButtonDelegateQt("button text") - clickable button, model's setData() handles the click
    files: FileDialogDelegateQt() - popup a file dialog, model's setData(pathToFileName) handles the rest
    """
    def __init__(self, model, parent=None):
        QTableView.__init__(self, parent)

        # Custom delegates.
        self._checkBoxDelegate = CheckBoxDelegateQt()
        self._floatEditDelegate = FloatEditDelegateQt()
        self._dateTimeEditDelegates = []  # Each of these can have different formats.
        self._comboBoxDelegates = []  # Each of these can have different choices.
        self._pushButtonDelegates = []  # Each of these can have different text.
        self._fileDialogDelegate = FileDialogDelegateQt()

        # Set the model.
        self.setModel(model)

    def setModel(self, model):
        if type(model) is not ObjectListTableModelQt:
            raise RuntimeError("ObjectListTableViewQt.setModel: Model type MUST be ObjectListTableModelQt.")

        QTableView.setModel(self, model)

        # Clear current delegate lists.
        self._dateTimeEditDelegates = []  # Each of these can have different formats.
        self._comboBoxDelegates = []  # Each of these can have different choices.
        self._pushButtonDelegates = []  # Each of these can have different text.

        # Assign custom delegates.
        for i, prop in enumerate(model.properties):
            dtype = model.propertyType(i)
            if 'choices' in prop.keys():
                self._comboBoxDelegates.append(ComboBoxDelegateQt(prop['choices']))
                if model.isRowObjects:
                    self.setItemDelegateForColumn(i, self._comboBoxDelegates[-1])
                else:
                    self.setItemDelegateForRow(i, self._comboBoxDelegates[-1])
            elif prop.get('action', "") == "fileDialog":
                if model.isRowObjects:
                    self.setItemDelegateForColumn(i, self._fileDialogDelegate)
                else:
                    self.setItemDelegateForRow(i, self._fileDialogDelegate)
            elif prop.get('action', "") == "button":
                self._pushButtonDelegates.append(PushButtonDelegateQt(prop.get('text', "")))
                if model.isRowObjects:
                    self.setItemDelegateForColumn(i, self._pushButtonDelegates[-1])
                else:
                    self.setItemDelegateForRow(i, self._pushButtonDelegates[-1])
            elif dtype is bool:
                if model.isRowObjects:
                    self.setItemDelegateForColumn(i, self._checkBoxDelegate)
                else:
                    self.setItemDelegateForRow(i, self._checkBoxDelegate)
            elif dtype is float:
                if model.isRowObjects:
                    self.setItemDelegateForColumn(i, self._floatEditDelegate)
                else:
                    self.setItemDelegateForRow(i, self._floatEditDelegate)
            elif dtype is datetime:
                self._dateTimeEditDelegates.append(DateTimeEditDelegateQt(prop.get('text', '%c')))
                if model.isRowObjects:
                    self.setItemDelegateForColumn(i, self._dateTimeEditDelegates[-1])
                else:
                    self.setItemDelegateForRow(i, self._dateTimeEditDelegates[-1])

        # Context menus for right click in header.
        # Objects header pops up insert/delete objects menu.
        # Properties header pops up properties menu.
        self.horizontalHeader().setContextMenuPolicy(Qt.NoContextMenu)
        self.verticalHeader().setContextMenuPolicy(Qt.NoContextMenu)
        if model.isDynamic:
            self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
            self.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
            if model.isRowObjects:
                self.horizontalHeader().customContextMenuRequested.connect(self.getPropertyHeaderContextMenu)
                self.verticalHeader().customContextMenuRequested.connect(self.getObjectHeaderContextMenu)
            else:
                self.horizontalHeader().customContextMenuRequested.connect(self.getObjectHeaderContextMenu)
                self.verticalHeader().customContextMenuRequested.connect(self.getPropertyHeaderContextMenu)
        else:
            if model.isRowObjects:
                self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
                self.horizontalHeader().customContextMenuRequested.connect(self.getPropertyHeaderContextMenu)
            else:
                self.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
                self.verticalHeader().customContextMenuRequested.connect(self.getPropertyHeaderContextMenu)

        # Resize columns to fit content.
        self.resizeColumnsToContents()

    def getObjectHeaderContextMenu(self, pos):
        menu = QMenu()
        rowOrColumn = "Row" if self.model().isRowObjects else "Column"
        aboveOrBefore = "Above" if self.model().isRowObjects else "Before"
        belowOrAfter = "Below" if self.model().isRowObjects else "After"
        menu.addAction("Insert " + rowOrColumn + " " + aboveOrBefore + " Selected", self.insertObjectBeforeSelectedObjects)
        menu.addAction("Insert " + rowOrColumn + " " + belowOrAfter + " Selected", self.insertObjectAfterSelectedObjects)
        menu.addSeparator()
        menu.addAction("Insert " + rowOrColumn + "s " + aboveOrBefore + " Selected", self.insertObjectsBeforeSelectedObjects)
        menu.addAction("Insert " + rowOrColumn + "s " + belowOrAfter + " Selected", self.insertObjectsAfterSelectedObjects)
        menu.addSeparator()
        menu.addAction("Move Selected " + rowOrColumn + "s", self.moveSelectedObjects)
        menu.addSeparator()
        menu.addAction("Delete Selected " + rowOrColumn + "s", self.removeSelectedObjects)
        header = self.verticalHeader() if self.model().isRowObjects else self.horizontalHeader()
        return menu.exec_(header.viewport().mapToGlobal(pos))

    def getPropertyHeaderContextMenu(self, pos):
        menu = QMenu()
        if len(self.model().objects) > 1:
            rowOrColumn = "Column" if self.model().isRowObjects else "Row"
            menu.addAction("Set All In Selected " + rowOrColumn, self.setPropertyForAllObjects)
        elif (len(self.model().objects) == 0) and (self.model().templateObject is not None):
            rowOrColumn = "Row" if self.model().isRowObjects else "Column"
            menu.addAction("Add Object " + rowOrColumn, self.appendObject)
        else:
            return
        header = self.horizontalHeader() if self.model().isRowObjects else self.verticalHeader()
        return menu.exec_(header.viewport().mapToGlobal(pos))

    def selectedRows(self):
        selectedIndexes = self.selectionModel().selection().indexes()
        rows = set()
        for index in selectedIndexes:
            rows.add(index.row())
        return sorted(list(rows))

    def selectedColumns(self):
        selectedIndexes = self.selectionModel().selection().indexes()
        columns = set()
        for index in selectedIndexes:
            columns.add(index.column())
        return sorted(list(columns))

    def insertObject(self, i):
        self.model().insertObjects(i, 1)

    def appendObject(self):
        self.insertObject(len(self.model().objects))

    def removeObject(self, i):
        self.model().removeObjects(i, 1)

    def insertObjectBeforeSelectedObjects(self):
        selectedObjectIndices = self.selectedRows() if self.model().isRowObjects else self.selectedColumns()
        self.model().insertObjects(selectedObjectIndices[0], 1)

    def insertObjectAfterSelectedObjects(self):
        selectedObjectIndices = self.selectedRows() if self.model().isRowObjects else self.selectedColumns()
        self.model().insertObjects(selectedObjectIndices[-1] + 1, 1)

    def insertObjectsBeforeSelectedObjects(self):
        num, ok = QInputDialog.getInt(self, "Insert", "Number of objects to insert.", 1, 1)
        if ok:
            selectedObjectIndices = self.selectedRows() if self.model().isRowObjects else self.selectedColumns()
            self.model().insertObjects(selectedObjectIndices[0], num)

    def insertObjectsAfterSelectedObjects(self):
        num, ok = QInputDialog.getInt(self, "Insert", "Number of objects to insert.", 1, 1)
        if ok:
            selectedObjectIndices = self.selectedRows() if self.model().isRowObjects else self.selectedColumns()
            self.model().insertObjects(selectedObjectIndices[-1] + 1, num)

    def removeSelectedObjects(self):
        selectedObjectIndices = self.selectedRows() if self.model().isRowObjects else self.selectedColumns()
        for i in reversed(selectedObjectIndices):
            self.model().removeObjects(i, 1)

    def moveSelectedObjects(self):
        moveToIndex, ok = QInputDialog.getInt(self, "Move", "Move to index.", 1, 1, len(self.model().objects))
        if ok:
            moveToIndex -= 1  # From 1-based to 0-based.
            moveToIndex = min([max([0, moveToIndex]), len(self.model().objects)])  # Clamp moveToIndex to a valid object index.
            selectedObjectIndices = self.selectedRows() if self.model().isRowObjects else self.selectedColumns()
            self.model().moveObjects(selectedObjectIndices, moveToIndex)

    def clearObjects(self):
        self.model().clearObjects()

    def setPropertyForAllObjects(self):
        selectedPropertyIndices = self.selectedColumns() if self.model().isRowObjects else self.selectedRows()
        if len(selectedPropertyIndices) != 1:
            errorDialog = QErrorMessage(self)
            rowOrColumn = "column" if self.model().isRowObjects else "row"
            errorDialog.showMessage("Must select a single property " + rowOrColumn + ".")
            errorDialog.exec_()
            return
        try:
            propertyIndex = selectedPropertyIndices[0]
            dtype = self.model().propertyType(propertyIndex)
            if dtype is None:
                return
            obj = self.model().objects[0]
            prop = self.model().properties[propertyIndex]
            if "Write" not in prop.get('mode', "Read/Write"):
                return
            model = ObjectListTableModelQt([obj], [prop], self.model().isRowObjects, False)
            view = ObjectListTableViewQt(model)
            dialog = QDialog(self)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            vbox = QVBoxLayout(dialog)
            vbox.addWidget(view)
            vbox.addWidget(buttons)
            dialog.setWindowModality(Qt.WindowModal)
            dialog.exec_()
            for objectIndex, obj in enumerate(self.model().objects):
                row = objectIndex if self.model().isRowObjects else propertyIndex
                col = propertyIndex if self.model().isRowObjects else objectIndex
                index = self.model().index(row, col)
                if objectIndex == 0:
                    value = self.model().data(index)
                else:
                    if prop.get('action', '') == "fileDialog":
                        try:
                            getAttrRecursive(obj, prop['attr'])(value)
                            self.model().dataChanged.emit(index, index)  # Tell model to update cell display.
                        except:
                            self.model().setData(index, value)
                            self.model().dataChanged.emit(index, index)  # Tell model to update cell display.
                    else:
                        self.model().setData(index, value)
                        self.model().dataChanged.emit(index, index)  # Tell model to update cell display.
        except:
            pass


if __name__ == "__main__":
    import sys
    try:
        from PyQt5.QtCore import QT_VERSION_STR
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        try:
            from PyQt4.QtCore import QT_VERSION_STR
            from PyQt4.QtGui import QApplication
        except ImportError:
            raise ImportError("ObjectListTableModelViewQt: Requires PyQt5 or PyQt4.")
    print('ObjectListTableModelViewQt: Using Qt ' + QT_VERSION_STR)


    # We'll create a table model/view for a list of these objects.
    class MyObject(object):
        def __init__(self, name="New Obj", s="", i=0, f=0.0, b=True, hasChild=True):
            self.name = name
            self.strValue = s
            self.intValue = i
            self.floatValue = f
            self.boolValue = b
            self.dateValue = datetime.now()
            self._fileName = ""
            if hasChild:
                self.child = MyObject(name, s, i, f, b, False)

        # We'll have the model/view access the fileName property
        # rather than the _fileName attribute so that we
        # run our custom code whenever the fileName is changed.
        @property
        def fileName(self):
            return self._fileName

        @fileName.setter
        def fileName(self, fileName):
            if len(fileName) and (fileName != self._fileName):
                print("Setting file name for " + self.name + " to " + fileName + ".")
                self._fileName = fileName

        # We'll have the model/view call this
        # when a button is clicked in the object's row/column.
        def clicked(self):
            print(self.name + " was clicked.")


    # Create the QApplication.
    app = QApplication(sys.argv)

    # Create our object list.
    a = MyObject("obj A", "a str", 3, 0.042, True)
    b = MyObject("obj B", "b str", -1, -10.069, False)
    objects = [a, b]

    # Specify the properties to display in the model/view.
    properties = [
        {'attr': "name",           'header': "Read Only Name",      'mode': "Read Only"},
        {'attr': "strValue",       'header': "String"},
        {'attr': "intValue",       'header': "Integer"},
        {'attr': "floatValue",     'header': "Float"},
        {'attr': "boolValue",      'header': "Bool"},
        {'attr': "dateValue",      'header': "Date/Time",           'text': "%c"},
        {'attr': "fileName",       'header': "File Name",           'action': "fileDialog"},
        {'attr': "clicked",        'header': "Button",              'action': "button", 'text': "Click Me!"},
        {'attr': "child.intValue", 'header': "Child Int"},
        {'attr': "strValue",       'header': "String Combo Box",    'choices': ['First Choice', 'Second Choice']},
        {'attr': "child.intValue", 'header': "Child Int Combo Box", 'choices': [42, 82]},
        {'attr': "floatValue",     'header': "Float Combo Box",     'choices': [('PI', 3.14), ('-PI', -3.14)]}]

    # Print property names/values/types prior to editing.
    print("---------- BEFORE EDITING ----------")
    for obj in objects:
        for prop in properties:
            attr = prop['attr']
            try:
                value = getattr(obj, attr)
                print(attr, value, type(value))
            except:
                pass

    # Create the model/view.
    model = ObjectListTableModelQt(objects, properties, isRowObjects=True, isDynamic=True, templateObject=MyObject())
    view = ObjectListTableViewQt(model)

    # Show the model/view and run the application.
    view.setAttribute(Qt.WA_DeleteOnClose)
    view.show()
    status = app.exec_()

    # Print property names/values/types post editing.
    print("---------- AFTER EDITING ----------")
    for obj in objects:
        for prop in properties:
            attr = prop['attr']
            try:
                value = getattr(obj, attr)
                print(attr, value, type(value))
            except:
                pass
    sys.exit(status)
