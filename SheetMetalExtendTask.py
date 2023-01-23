# -*- coding: utf-8 -*-
###############################################################################
#
#  SheetMetalJunction.py
#
#  Copyright 2022 Shai Seger <shaise at gmail dot com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#
###############################################################################

from PySide import QtGui
import FreeCAD
import os
from PySide import QtCore
from SheetMetalUtil import iconPath
import FreeCADGui


class SMBendWallTaskPanel:
    """A TaskPanel for the Sheetmetal"""

    def __init__(self):

        self.obj = None
        self.form = QtGui.QWidget()
        self.form.setObjectName("SMBendWallTaskPanel")
        self.form.setWindowTitle("Binded faces/edges list")
        self.grid = QtGui.QGridLayout(self.form)
        self.grid.setObjectName("grid")
        self.title = QtGui.QLabel(self.form)
        self.grid.addWidget(self.title, 0, 0, 1, 2)
        self.title.setText("Select new face(s)/Edge(s) and press Update")

        # tree
        self.tree = QtGui.QTreeWidget(self.form)
        self.grid.addWidget(self.tree, 1, 0, 1, 2)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Name", "Subelement"])

        # buttons
        self.addButton = QtGui.QPushButton(self.form)
        self.addButton.setObjectName("addButton")
        self.addButton.setIcon(
            QtGui.QIcon(os.path.join(iconPath, "SheetMetal_Update.svg"))
        )
        self.grid.addWidget(self.addButton, 3, 0, 1, 2)

        QtCore.QObject.connect(
            self.addButton, QtCore.SIGNAL("clicked()"), self.updateElement
        )
        self.update()

    def isAllowedAlterSelection(self):
        return True

    def isAllowedAlterView(self):
        return True

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok)

    def update(self):
        "fills the treewidget"
        self.tree.clear()
        if self.obj:
            f = self.obj.baseObject
            if isinstance(f[1], list):
                for subf in f[1]:
                    # FreeCAD.Console.PrintLog("item: " + subf + "\n")
                    item = QtGui.QTreeWidgetItem(self.tree)
                    item.setText(0, f[0].Name)
                    item.setIcon(0, QtGui.QIcon(":/icons/Tree_Part.svg"))
                    item.setText(1, subf)
            else:
                item = QtGui.QTreeWidgetItem(self.tree)
                item.setText(0, f[0].Name)
                item.setIcon(0, QtGui.QIcon(":/icons/Tree_Part.svg"))
                item.setText(1, f[1][0])
        self.retranslateUi(self.form)

    def updateElement(self):
        if self.obj:
            sel = FreeCADGui.Selection.getSelectionEx()[0]
            if sel.HasSubObjects:
                obj = sel.Object
                for elt in sel.SubElementNames:
                    if "Face" in elt or "Edge" in elt:
                        face = self.obj.baseObject
                        found = False
                        if face[0] == obj.Name:
                            if isinstance(face[1], tuple):
                                for subf in face[1]:
                                    if subf == elt:
                                        found = True
                            else:
                                if face[1][0] == elt:
                                    found = True
                        if not found:
                            self.obj.baseObject = (sel.Object, sel.SubElementNames)
            self.update()

    def accept(self):
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.ActiveDocument.resetEdit()
        # self.obj.ViewObject.Visibility=True
        return True

    def retranslateUi(self, TaskPanel):
        self.addButton.setText(QtGui.QApplication.translate("draft", "Update", None))
