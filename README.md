# ModelViewPyQt

A collection of [PyQt](https://www.riverbankcomputing.com/software/pyqt/intro) (version 4 or 5) model/view interfaces. I plan on adding models/views (and their delegates) as they are needed for other projects.

### Models/Views

* **ObjectListTableModelViewQt**: For when you have a list of objects all of the same type (can be anything), and you want to view and/or edit specified object attributes in a table where each row is an object and each column an attribute (or optionally vice-versa). Optionally allows dynamic object insertion/deletion/rearrangement. Delegates are provided for *check boxes*, *date/times*, *combo boxes*, *buttons*, *file dialogs*, etc.

### Delegates

* **CheckBoxDelegateQt**: A centered check box without a label for boolean values.
* **FloatEditDelegateQt**: Editor for float values that handles arbitrary precision and scientific notation.
* **DateTimeEditDelegateQt**: Edit *datetime* objects in a specified format.
* **ComboBoxDelegateQt**: Cell editor is a combo box displaying the values in a specified list of choices. Alternatively, the choices may be a list of (key, value) tuples, in which case the   view and combo box display the keys whereas the model data is set to the values.
* **PushButtonDelegateQt**: Cell is drawn as a button. !!! Defers handling the button click action to the model's `setData()` method.
* **FileDialogDelegateQt**: Cell editor pops up a file dialog, for which the returned "path/to/filename" string is passed to the model's `setData()` method.

**Author**: Marcel Goldschen-Ohm  
**Email**:  <marcel.goldschen@gmail.com>  
**License**: MIT  
Copyright (c) 2015 Marcel Goldschen-Ohm  

## INSTALL

Just put the following files somewhere where your project can find them:

* `ObjectListTableModelViewQt.py`
* `CheckBoxDelegateQt.py`
* `FloatEditDelegateQt.py`
* `DateTimeEditDelegateQt.py`
* `ComboBoxDelegateQt.py`
* `PushButtonDelegateQt.py`
* `FileDialogDelegateQt.py`

### Requires:

* [PyQt](https://www.riverbankcomputing.com/software/pyqt/intro) (version 4 or 5)

On Mac OS X you can install Qt4 and PyQt4 via [Homebrew](http://brew.sh) as shown below:

    brew install qt
    brew install pyqt

## ObjectListTableModelViewQt

For when you have a list of objects all of the same type (can be anything), and you want to view and/or edit specified object attributes in a table where each row is an object and each column an attribute (or optionally vice-versa).

Right clicking in the view's row or column headers brings up a context menu for inserting/deleting/moving objects
in the list (optional), or setting an attribute's value for all objects simultaneously.

### Properties

The object properties displayed in the model/view are specified as a list of *dicts* whose keys may include any of the following:

* **'attr'**: Name of an object attribute. If specified, the model's `data()` and `setData()` methods will get/set the attribute's value for the associated object. *!!! May be a path to a child attribute such as* **"path.to.a.child.attr"** *.*
* **'header'**: Text to display in the table view's property header.
* **'dtype'**: Attribute type. If not specified, this is inferred either from the model's *templateObject* or an object in the list.
* **'mode'**: *"Read/Write"* or *"Read Only"*. If not specified, defaults to *"Read/Write"*.
* **'choices'**: List of values or (key, value) tuples. If specified, the values (or their keys if they exist) are presented in a combo box. *Note that you can offer a selection of complex objects that do not have simple string representations by entering them as (key, object) tuples. In this case the view will display the keys whereas the model will use the values.*
* **'action'**: Name of a special action associated with this cell. Actions include:
    * *"button"*: Cell is a clickable button. The model's `setData()` method calls the object's method specified by the property's **'attr'** item. The button text is set to the value of the property's **'text'** item.
    * *"fileDialog"*: Double clicking on the cell pops up a file dialog. The property's **'attr'** item should be the object's path/to/filename attribute or @property if you want a load script to run whenever the filename is changed.
* **'text'**: String used by certain properties. For example, used to specify a button's text or the format of a *datetime* object.

This property specification is easily extended to encompass new property types with new delegates, and also provides for easily readable code:

```python
# For each object in the list:
# Read Only  column of object.name strings.
# Read/Write column of object.age integers.
# Read/Write column of object.birth datetimes (format="%x").
# Read/Write column of object.friend.name strings.
properties = [
    {'attr': "name",        'header': "Name",   'mode': "Read Only"},
    {'attr': "age",         'header': "Age"},
    {'attr': "birth",       'header': "D.O.B.", 'text': "%x"},
    {'attr': "friend.name", 'header': "Friend"}]  
```

### A Simple Example

Use `ObjectListTableModelViewQt` to interface with a list of `MyObject` objects. Exposes a variety of attribute data types and object actions through various delegates.

```python
import sys
try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
except ImportError:
    try:
        from PyQt4.QtCore import Qt
        from PyQt4.QtGui import QApplication
    except ImportError:
        raise ImportError("Requires PyQt5 or PyQt4.")
from ObjectListTableModelViewQt import ObjectListTableModelQt, ObjectListTableViewQt


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
        return self. _fileName

    @fileName.setter
    def fileName(self, fileName):
        if len(fileName) and (fileName != self.fileName):
            print(self.name + " fileName set to " + fileName)
            self.fileName = fileName
    
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
    {'attr': "clicked",        'header': "Button",              'action': "button",  'text': "Click Me!"},
    {'attr': "child.intValue", 'header': "Child Int"},
    {'attr': "strValue",       'header': "String Combo Box",    'choices': ['First Choice', 'Second Choice']},
    {'attr': "child.intValue", 'header': "Child Int Combo Box", 'choices': [42, 82]},
    {'attr': "floatValue",     'header': "Float Combo Box",     'choices': [('Pi', 3.14), ('-Pi', -3.14)]}]

# Create the model/view.
model = ObjectListTableModelQt(objects, properties, isRowObjects=True, isDynamic=True, templateObject=MyObject())
view = ObjectListTableViewQt(model)
    
# Show the model/view and run the application.
view.setAttribute(Qt.WA_DeleteOnClose)
view.show()
sys.exit(app.exec_())
```
