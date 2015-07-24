#!/usr/bin/python

import sys
import os
import platform
import argparse
import subprocess
import json

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtSlot, Qt


class LauncherMenuModel:

    """Parse configuration and build menu model.

    LauncherMenuModel parses the configuration file and builds the list of
    menu items. Each LauncherMenuModel object holds only a list of items
    defined in its configuration file. If submenu is needed, new
    LauncherMenuModel object is created and its reference is stored on the
    calling object list menuItems.

    Each menu has:
        _items
        mainTitle: holding the title of the menu
        list of menuItems: list of all LauncherMenuModelItems
        TODO: in future it will also hold the styles, levels and list of
        possible pictures on the buttons
    """

    def __init__(self, menuFile, launcherCfg):

        # Parses comma separated files of defined format. Parser adds menu
        # objects to self.menuItems list.

        self.menuItems = list()
        self._parseMenuJson(menuFile, launcherCfg)

    def getItemsOfType(self, itemsType):
        """Returns a list of all items of specified type."""

        return filter(lambda x: x.__class__.__name__ ==
                      itemsType, self.menuItems)

    def _parseMenuJson(self, menuFile, launcherCfg):
        """Parse JSON type menu config file."""

        _menu = json.load(menuFile)
        self.mainTitle = _menu.get("menu-title",
                                   os.path.basename(menuFile.name))
        # Get list of possible views (e.g. expert, user)

        _listOfViews = _menu.get("file-choice", list())
        self.fileChoices = list()
        for _view in _listOfViews:
            self._checkItemFormatJson(_view, ["text", "file"])  # exits if not
            _text = _view.get("text").strip()
            _fileName = _view.get("file").strip()
            # Do not open file just check if exists. Will be opened, in
            # LauncherWindow._buildMenuModel

            _filePath = os.path.join(launcherCfg.get("launcher_base"),
                                     _fileName)
            _filePath = os.path.normpath(_filePath)
            if not os.path.isfile(_filePath):
                _errMsg = "ParseErr: " + menuFile.name + ": File \"" +\
                    _fileName + "\" not found."
                sys.exit(_errMsg)
            self.fileChoices.append(LauncherFileChoiceItem(launcherCfg, _text,
                                                           _fileName))
        # Build menu model. Report error if menu is not defined.

        _listOfMenuItems = _menu.get("menu", list())
        if not _listOfMenuItems:
            errMsg = "ParseErr: " + menuFile.name + ": Launcher menu is not "\
                "defined."
            sys.exit(_errMsg)
        for _item in _listOfMenuItems:
            _type = _item.get("type", "")
            # For each check mandatory parameters and exit if not all.

            if _type == "cmd":
                self._checkItemFormatJson(_item, ["text", "param"])
                _text = _item.get("text").strip()
                _param = _item.get("param").strip()
                _menuItem = LauncherCmdItem(launcherCfg, _text, _param)
            elif _type == "menu":
                self._checkItemFormatJson(_item, ["text", "file"])
                _text = _item.get("text").strip()
                _fileName = _item.get("file").strip()
                try:
                    _file = open(launcherCfg.get("launcher_base") + _fileName)
                except IOError:
                    _errMsg = "ParseErr: " + menuFile.name + ": File \"" + \
                              _fileName + "\" not found."
                    sys.exit(_errMsg)
                _menuItem = LauncherSubMenuItem(launcherCfg, _text, _file)
                _file.close()
            elif _type == "title":
                self._checkItemFormatJson(_item, ["text"])
                _text = _item.get("text").strip()
                _menuItem = LauncherTitleItem(_text)

            elif _type == "separator":
                _menuItem = LauncherItemSeparator()

            else:
                _errMsg = "ParseErr:" + menuFile.name + " (line " + \
                    str(_i) + "): Unknown type \"" + _item[0].strip() + \
                    "\"."
                sys.exit(_errMsg)

            self.menuItems.append(_menuItem)

    def _checkItemFormatJson(self, item, mandatoryParam):
        """Check dictionary for mandatory keys.

        Check item (dictionary) if it holds all mandatory keys. If any key is
        missing, exit the program and report error.
        """

        for _param in mandatoryParam:
            if not item.get(_param):
                _errMsg = "ParseErr: Parameter \"" + _param + \
                    "\" is mandatory in configuration \"" + item + "\"."
                sys.exit(_errMsg)


class LauncherMenuModelItem:

    """Super class for all items in menu model.

    LauncherMenuModelItem is a parent super class for menu items that needs
    to be visualized, such as menu buttons, separators, titles. It implements
    methods and parameters common to many subclasses.
    """

    def __init__(self, text=None, style=None, helpLink=None, key=None):
        self.text = text
        self.style = style
        self.helpLink = helpLink
        self.key = key


class LauncherItemSeparator(LauncherMenuModelItem):

    """Special LauncherMenuModelItem, with no text, style or help."""

    def __init__(self, key=None):
        LauncherMenuModelItem.__init__(self, text=None, style=None, key=key)


class LauncherCmdItem(LauncherMenuModelItem):

    """LauncherCmdItem holds the whole shell command."""

    def __init__(self, launcherCfg, text=None, cmd=None, style=None,
                 helpLink=None, key=None):
        LauncherMenuModelItem.__init__(self, text, style, key)
        _itemCfg = launcherCfg.get("cmd")
        _prefix = _itemCfg.get("command")
        self.cmd = _prefix + " " + cmd


class LauncherSubMenuItem(LauncherMenuModelItem):

    """Menu item with reference to submenu model.

    LauncherSubMenuItem builds new menu which is defined in subMenuFile.
    If detach == True this sub-menu should be automatically detached if
    detachment is supported in view.
    """

    def __init__(self, launcherCfg, text=None, subMenuFile=None, style=None,
                 helpLink=None, detach=False, key=None):
        LauncherMenuModelItem.__init__(self, text, style, key)
        self.subMenu = LauncherMenuModel(subMenuFile, launcherCfg)


class LauncherFileChoiceItem(LauncherMenuModelItem):

    """Holds new root menu config file.

    Launcher can be "rebuild" from new root menu file. LauncherFileChoiceItem
    holds the file of the new root menu (rootMenuFile).
    """

    def __init__(self, launcherCfg, text=None, rootMenuFile=None, style=None,
                 helpLink=None, key=None):
        LauncherMenuModelItem.__init__(self, text, style, key)
        self.rootMenuFile = launcherCfg.get("launcher_base") + rootMenuFile


class LauncherTitleItem(LauncherMenuModelItem):

    """Text menu separator."""

    def __init__(self, text=None, style=None, helpLink=None, key=None):
        LauncherMenuModelItem.__init__(self, text, style, key)


class LauncherWindow(QtGui.QMainWindow):

    """Launcher main window.

    Main launcher window. At initialization recursively builds visualization
    of launcher menus, builds menu bar, ...
    """

    def __init__(self, rootFilePath, cfgFilePath, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        try:
            _cfgFile = open(cfgFilePath)
        except IOError:
            _errMsg = "Err: Configuration file \"" + cfgFilePath + \
                "\" not found."
            sys.exit(_errMsg)
        _cfg = json.load(_cfgFile)
        _cfgFile.close()
        # Get configuration for current system.

        self.launcherCfg = _cfg.get(platform.system())

        # Build menu model from rootMenuFile and set general parameters.
        self._menuModel = self._buildMenuModel(rootFilePath)

        self.setWindowTitle(self._menuModel.mainTitle)
        # QMainWindow has predefined layout. Content should be in the central
        # widget. Create widget with a QVBoxLayout and set it as central.

        _mainWidget = QtGui.QWidget(self)
        self._mainLayout = QtGui.QVBoxLayout(_mainWidget)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(_mainWidget)
        # Main window consist of filter/serach entry and a main button which
        # pops up the root menu. Create a layout and add the items.

        self.mainButton = QtGui.QPushButton(self._menuModel.mainTitle, self)
        # Visualize the menus by recursively creating LauncherSubMenu objects
        # for each LauncherMenuModel from model. Append it to the button.

        self._launcherMenu = LauncherSubMenu(self._menuModel, self.mainButton)
        self.mainButton.setMenu(self._launcherMenu)

        # Create Filter/search item. Add it and main button to the layout.
        self._searchInput = LauncherSearchWidget(self._launcherMenu, self)
        self._mainLayout.addWidget(self._searchInput)
        self._mainLayout.addWidget(self.mainButton)
        # Create menu bar. In current visualization menu bar also exposes all
        # LauncherFileChoiceItem items from the model. They are exposed in
        # File menu.
        _menuBar = self.menuBar()
        self._fileMenu = QtGui.QMenu("&File", _menuBar)
        for item in self._menuModel.fileChoices:
            _button = LauncherFileChoiceButton(item, self._fileMenu)
            _buttonAction = QtGui.QWidgetAction(self._fileMenu)
            _buttonAction.setDefaultWidget(_button)
            self._fileMenu.addAction(_buttonAction)
        _menuBar.addMenu(self._fileMenu)

    def setNewView(self, rootMenuFile):
        """Rebuild launcher from new config file.

        Destroy previous model and create new one. Build menus and edit main
        window elements.
        """

        del self._menuModel
        self._menuModel = self._buildMenuModel(rootMenuFile)
        self.setWindowTitle(self._menuModel.mainTitle)
        self.mainButton.setText(self._menuModel.mainTitle)
        self._launcherMenu = LauncherSubMenu(self._menuModel, self.mainButton)
        self.mainButton.setMenu(self._launcherMenu)

    def changeEvent(self, changeEvent):
        """Catch when main window is selected and set focus to search."""

        if changeEvent.type() == QtCore.QEvent.ActivationChange and \
                self.isActiveWindow():
            self._searchInput.setFocus()

    def _buildMenuModel(self, rootMenuPath):
        """Return model of a menu defined in rootMenuFile."""
        _rootMeniFullPath = os.path.join(self.launcherCfg.get("launcher_base"),
                                         rootMenuPath)
        _rootMeniFullPath = os.path.normpath(_rootMeniFullPath)
        try:
            _rootMenuFile = open(_rootMeniFullPath)
        except IOError:
            _errMsg = "Err: File \"" + rootMenuPath + "\" not found."
            sys.exit(_errMsg)
        _rootMenu = LauncherMenuModel(_rootMenuFile, self.launcherCfg)
        _rootMenuFile.close()
        return _rootMenu


class LauncherMenu(QtGui.QMenu):

    """Super class of all menu visualizations.

    Is a parent super class which takes the model of menu as an argument and
    builds a "vital" part of the menu. It also implements methods for menu
    manipulation.
    """

    def __init__(self, menuModel, parent=None):
        QtGui.QMenu.__init__(self, parent)
        self.filterTerm = ""
        self.menuModel = menuModel
        # menuModel has a list of menuItems with models of items. Build buttons
        # from it and add them to the menu.

        for item in self.menuModel.menuItems:
            if item.__class__.__name__ == "LauncherCmdItem":
                self.appendToMenu(LauncherCmdButton(item, self))
            elif item.__class__.__name__ == "LauncherSubMenuItem":
                self.appendToMenu(LauncherMenuButton(item, self))
            elif item.__class__.__name__ == "LauncherTitleItem":
                self.appendToMenu(LauncherMenuTitle(item, self))
            elif item.__class__.__name__ == "LauncherItemSeparator":
                self.addAction(LauncherSeparator(item, self))

    def appendToMenu(self, widget):
        """Append action to menu.

        Create widget action for widget. Pair them and add to the menu."""

        self._action = LauncherMenuWidgetAction(widget, self)
        self.addAction(self._action)

    def insertToMenu(self, widget, index):
        """Insert action to specified position in menu.

        Create widget action for widget. Pair them and insert them to the
        specified position in menu.
        """

        self._action = LauncherMenuWidgetAction(widget, self)
        if self.actions()[index]:
            self.insertAction(self.actions()[index], self._action)
        else:
            self.addAction(self._action)

    def filterMenu(self, filterTerm=None):
        """Filter menu items with filterTerm

        Shows/hides action depending on filterTerm. Returns true if has
        visible active (buttons) items.
        """

        self.filterTerm = filterTerm
        _hasVisible = False
        _visible_count = 0
        _last_title = None
        # Skip first item since it is either search entry or detach button.

        for action in self.actions()[1:len(self.actions())]:
            if action.__class__.__name__ == "LauncherMenuWidgetAction":
                _widget = action.defaultWidget()
                _type = _widget.__class__.__name__

            if not filterTerm:
                # Empty filter. Show all.
                action.setVisibility(True)

            elif _type == "LauncherMenuTitle":
                # Visible actions below title are counted. If count > 0 then
                # show last title. Then reset counter and store current title
                # as last.

                if _last_title:
                    _last_title.setVisibility(_visible_count != 0)
                _visible_count = 0
                _last_title = action

            elif _type == "LauncherMenuButton":
                # Recursively filter menus. Show only sub-menus that have
                # visible items.

                _subMenu = action.defaultWidget().menu()
                _subHasVisible = _subMenu.filterMenu(filterTerm)
                action.setVisibility(_subHasVisible)
                if _subHasVisible:
                    _visible_count += 1
                _hasVisible = _hasVisible or _subHasVisible

            elif filterTerm in _widget.text():
                # Filter term is found in the button text. For now filter only
                # cmd buttons.

                action.setVisibility(True)
                _hasVisible = True
                _visible_count += 1
            else:
                action.setVisibility(False)

            if _last_title:  # Handle last title if exists
                _last_title.setVisibility(_visible_count != 0)

        return _hasVisible

    def showEvent(self, showEvent):
        """Catch event when menu is shown and move it by side of parent.

        Whenever show(), popup(), exec() are called this method is called.
        Move the menu to the left side of the button (default is bellow)
        """
        # TODO handle cases when to close to the edge of screen.
        position = self.pos()
        position.setX(position.x()+self.parent().width())
        position.setY(position.y()-self.parent().height())
        self.move(position)

        # Set focus on first button (skip detach button and titles)
        _i = 1
        while isinstance(self.actions()[_i].defaultWidget(),
                         LauncherMenuTitle):
            _i += 1
        self.actions()[_i].defaultWidget().setFocus()
        self.setActiveAction(self.actions()[_i])

    def _getRootAncestor(self):
        """Return mainButton from which all menus expand.

        All LauncherMenu menus visualized from the same root menu model
        have lowest common ancestor which is a mainButton of the
        LauncherWindow. If this button is destroyed all menus are also
        destroyed, and all detached menus are closed. Because each Qt element
        holds reference to its parent, mainButton of LauncherWindow can be
        recursively determined.
        """

        _object = self
        while type(_object) is not LauncherWindow:
            _object = _object.parent()
        return _object.mainButton


class LauncherSubMenu(LauncherMenu):

    """Visualization of sub-menu.

    Implements a visualization of the menu when used as a sub menu. Popuped
    from the main menu or button.

    Creates detach button and adds it to the menu.
    """

    def __init__(self, menuModel, parent=None):
        LauncherMenu.__init__(self, menuModel, parent)
        self.detachButton = LauncherDetachButton(self)
        self.insertToMenu(self.detachButton, 0)

    def detach(self):
        """Open menu in new window.

        Creates  new menu and opens it as new window. Menu parent should be
        mainButton on launcherWindow. This way it will be closed only if the
        launcher is close or the root menu is changed.
        """

        _launcherWindow = self._getRootAncestor()
        _detachedMenu = LauncherDetachedMenu(self.menuModel, _launcherWindow)
        # Put an existing filter to it and set property to open it as new
        # window.

        _detachedMenu.searchInput.setText(self.filterTerm)
        _detachedMenu.setWindowFlags(Qt.Window | Qt.Tool)
        _detachedMenu.setAttribute(Qt.WA_DeleteOnClose, True)
        _detachedMenu.setAttribute(Qt.WA_X11NetWmWindowTypeMenu, True)
        _detachedMenu.setEnabled(True)
        _detachedMenu.show()
        _detachedMenu.move(self.pos().x(), self.pos().y())
        self.hide()


class LauncherDetachedMenu(LauncherMenu):

    """Visualization of detached menu.

    Creates detached menu. Adds find/search input to menu. Also overrides the
    hide() method of the menu, because it should not be hidden  when action
    is performed.

    Removes detach button and filter/search widget but do not add them to
    the menu.
    """

    def __init__(self, menuModel, parent=None):
        LauncherMenu.__init__(self, menuModel, parent)
        self.searchInput = LauncherSearchWidget(self, self)
        self.insertToMenu(self.searchInput, 0)

    def hide(self):
        pass  # Detached menu should not be hidden by left arrow.

    def changeEvent(self, changeEvent):
        """Catch when menu window is selected and focus to search."""

        if changeEvent.type() == QtCore.QEvent.ActivationChange and \
                self.isActiveWindow():
            self.searchInput.setFocus()

    def keyPressEvent(self, event):
        """Catch escape (originally closes the window) and skip actions."""

        if event.key() == Qt.Key_Escape:
            pass
        else:
            LauncherMenu.keyPressEvent(self, event)


class LauncherMenuWidgetAction(QtGui.QWidgetAction):

    """Wrap widgets to be added to menu.

    When QWidget needs to be appended to QMenu it must be "wrapped" into
    QWidgetAction. This class "wraps" LauncherButton in the same way.
    Further it also implements method to control the visibility of the menu
    item (both action and widget).
    """

    def __init__(self, widget, parent=None):
        QtGui.QWidgetAction.__init__(self, parent)
        self.setDefaultWidget(widget)
        widget.setMyAction(self)  # Let widget know about action.

    def setVisibility(self, visibility):
        """Set visibility of both the widget action and the widget."""

        self._widget = self.defaultWidget()
        self.setVisible(visibility)
        self._widget.setVisible(visibility)


class LauncherSearchWidget(QtGui.QLineEdit):

    """Filter/search menu widget.

    LauncherSearchWidget is QLineEdit which does filtering of menu items
    recursively by putting the filter  to child menus. When enter button is
    pressed a search window with results is opened (TODO).
    """

    def __init__(self, menu, parent=None):
        QtGui.QLineEdit.__init__(self, parent)
        self.textChanged.connect(lambda: menu.filterMenu(self.text()))
        self._myAction = None

    def setMyAction(self, action):
        self._myAction = action


class LauncherSeparator(QtGui.QAction):

    """Normal menu separator with a key option (key TODO)."""

    def __init__(self, itemModel, parent=None):
        QtGui.QAction.__init__(self, parent)
        self.setSeparator(True)

    def setVisibility(self, visibility):
        self.setVisible(visibility)


class LauncherMenuTitle(QtGui.QLabel):

    """Passive element with no action and no key focus."""

    def __init__(self, itemModel, parent=None):
        QtGui.QLabel.__init__(self, itemModel.text, parent)
        self.setStyleSheet("QLabel { color: blue; }")
        self._myAction = None

    def setMyAction(self, action):
        self._myAction = action


class LauncherButton(QtGui.QPushButton):

    """Super class for active menu items (buttons).

    Parent class for all active menu items. To recreate the native menu
    behavior (when QActions are used) this class also handles keyboard
    events to navigate through the menu.

    Parent of any LauncherButton must be a QMenu and it must be paired with
    a LauncherMenuWidgetAction.
    """

    def __init__(self, parent=None):
        QtGui.QPushButton.__init__(self, parent)
        self.setMouseTracking(True)
        self._parent = parent
        self._myAction = None

    def setMyAction(self, action):
        self._myAction = action

    def keyPressEvent(self, event):
        """Catch key pressed event.

        Catch return and enter key pressed. Send clicked command to execute
        action.

        Catch left arrow button pressed on any of the menu buttons, to hide
        the whole menu (parent) and return to previous level menu.

        Catch right arrow button and skip it.
        """

        if (event.key() == Qt.Key_Return) or (event.key() == Qt.Key_Enter):
            self.click()
        elif event.key() == Qt.Key_Left:
            self.parent().hide()
        elif event.key() == Qt.Key_Right:
            pass
        elif event.key() == Qt.Key_Down:
            _candidate = self.nextInFocusChain()
            while isinstance(_candidate, LauncherMenuTitle):
                _candidate.focusNextChild()
                _candidate = _candidate.nextInFocusChain()
            _candidate.focusNextChild()
        elif event.key() == Qt.Key_Up:
            _candidate = self.previousInFocusChain()
            while isinstance(_candidate, LauncherMenuTitle):
                _candidate.focusPreviousChild()
                _candidate = _candidate.previousInFocusChain()
            _candidate.focusPreviousChild()
        else:
            QtGui.QPushButton.keyPressEvent(self, event)

    def mouseMoveEvent(self, event):
        self.setFocus()
        self._parent.setActiveAction(self._myAction)


class LauncherDetachButton(LauncherButton):

    """Button to detach menu and show it in new window.

    LauncherDetachButton is always shown as first item of popup menu. It
    builds new LauncherMenu from the model of parent menu and opens it in
    a new window.
    """

    def __init__(self, parent=None):
        LauncherButton.__init__(self, parent)
        self.setStyleSheet("""
            QPushButton{
                height: 2px;
                background-color: #666666
            }
            QPushButton:focus {
                background-color: #bdbdbd;
                outline: none
            }
        """)
        self.clicked.connect(parent.detach)


class LauncherNamedButton(LauncherButton):

    """Parent class to all buttons with text."""

    def __init__(self, itemModel, parent=None):
        LauncherButton.__init__(self, parent)
        self.setText(itemModel.text)


class LauncherFileChoiceButton(LauncherNamedButton):

    """Button to change the root menu of the launcher.

    LauncherFileChoiceButton causes the launcher to change the root menu and
    sets new view.
    """

    def __init__(self, itemModel, parent=None):
        LauncherNamedButton.__init__(self, itemModel, parent)
        self._itemModel = itemModel
        self.clicked.connect(self._changeView)

    @pyqtSlot()
    def _changeView(self):
        """Find LauncherWindow and set new view."""

        _candidate = self
        while _candidate.__class__.__name__ is not "LauncherWindow":
            _candidate = _candidate.parent()
        _candidate.setNewView(self._itemModel.rootMenuFile)
        self.parent().hide()  # When done hide popuped menu.


class LauncherCmdButton(LauncherNamedButton):

    """LauncherCmdButton executes shell command. """

    def __init__(self, itemModel, parent=None):
        LauncherNamedButton.__init__(self, itemModel, parent)
        self._cmd = itemModel.cmd
        self.clicked.connect(self._executeCmd)

    @pyqtSlot()
    def _executeCmd(self):
        subprocess.Popen(self._cmd, stdout=subprocess.PIPE, shell=True)
        self.parent().hide()  # When done hide popuped menu.


class LauncherMenuButton(LauncherNamedButton):

    """Builds a new model from a view.

    LauncherMenuButton builds new menu from model. When pressed the menu is
    popped up.
    """

    def __init__(self, itemModel, parent=None):
        LauncherNamedButton.__init__(self, itemModel, parent)
        _menu = LauncherSubMenu(itemModel.subMenu, self)
        self.setMenu(_menu)

    def keyPressEvent(self, event):
        """Submenu can be opened and closed with carrow keys."""

        if event.key() == Qt.Key_Right:
            self.click()
        elif event.key() == Qt.Key_Left:
            self.menu().hide()
        else:
            LauncherNamedButton.keyPressEvent(self, event)


if __name__ == '__main__':

    # Usage: launcher.py menu config
    argsPars = argparse.ArgumentParser()
    argsPars.add_argument('launcher',
                          help="Launcher menu file.")
    argsPars.add_argument('config',
                          help='Launcher configuration file')

    args = argsPars.parse_args()

    app = QtGui.QApplication(sys.argv)
    # With no style applied detached menu does not get window frame on SL6

    app.setStyle("cleanlooks")
    app.setStyleSheet("""
            QPushButton{
                background-color: #e9e9e9;
                border-image: none;
                border: none;
                padding: 4px;
                text-align:left;
            }
            QPushButton:focus {
                background-color: #bdbdbd;
                outline: none
            }
            QPushButton:menu-indicator {
                image: url(./images/arrow_bc.png);
                subcontrol-position: right center;
            }
            QLabel{
                background-color: #e9e9e9;
                padding: 4px;
                text-align:left;
            }
            QMenu {
                background-color: #e9e9e9
            }
            QMenu::separator {
                height: 1px;
                background: #b0b0b0;
            }
        """)

    rootMenuFile = sys.argv[1]
    cfgFile = os.path.normpath(sys.argv[2])

    launcherWindow = LauncherWindow(rootMenuFile, cfgFile)
    launcherWindow.setGeometry(0, 0, 150, 0)
    launcherWindow.show()
    sys.exit(app.exec_())
