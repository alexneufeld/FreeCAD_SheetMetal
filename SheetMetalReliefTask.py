# -*- coding: utf-8 -*-
###############################################################################
#
#  SheetMetalReliefTask.py
#
#  Copyright 2022 Alex Neufeld <alex.d.neufeld@gmail.com>
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

import FreeCADGui as Gui
import FreeCAD
import os.path
from PySide import QtCore
from PySide import QtGui
from SheetMetalCmd import iconPath
from SheetMetalUtil import selectionFilter


class SMReliefTaskPanel:
    def __init__(self, feature, isNewFeature):
        self.feature = feature
        self.isNewFeature = isNewFeature
        # encode current state so we can reset if the operation is cancelled
        trackedProperties = ["relief"]
        oldState = {}
        featureExprs = {k: v for (k, v) in feature.ExpressionEngine}
        for p in feature.PropertiesList:
            if p in trackedProperties:
                expr = featureExprs[p] if p in featureExprs else None
                oldState[p] = (feature.getPropertyByName(p), expr)
        self.oldState = oldState
        '''
        # also save transparency setting
        self.initTransparency = self.feature.ViewObject.Transparency
        self.initBaseVisible = self.feature.baseObject[0].ViewObject.Visibility
        '''
        # import UI form from file
        d = os.path.realpath(__file__)
        d = os.path.dirname(d)
        uiPath = os.path.join(d, "UI/TaskReliefParameters.ui")
        loader = Gui.UiLoader()
        self.form = loader.load(uiPath)
        self.setupUI()

    def setupUI(self):
        # set window title and icon
        self.form.setWindowTitle("Relief Parameters")
        self.form.setWindowIcon(
            QtGui.QIcon(os.path.join(iconPath, "SheetMetal_AddRelief.svg"))
        )
        # initialize UI fields to feature parameter values
        self.form.relief.setProperty("unit", "mm")
        self.form.relief.setProperty("rawValue", self.feature.relief.Value)
        # connect expression bindings
        Gui.ExpressionBinding(self.form.relief).bind(self.feature, "relief")
        # connect signals and slots
        self.form.relief.valueChanged.connect(self.relief)
        self.form.updateView.toggled.connect(self.updateView)
        # custom context menu setup
        self.form.listWidgetReferences.setContextMenuPolicy(
            QtGui.Qt.CustomContextMenu
        )
        self.form.listWidgetReferences.customContextMenuRequested.connect(
            self.showRefContextMenu
        )
        # add selected geometry to the list widget
        for geom in self.feature.baseObject[1]:
            self.form.listWidgetReferences.addItem(geom)
        # some widgets should be hidden by default
        self.form.errLabel.setVisible(False)
        # set up selection behaviour changes
        Gui.Selection.clearSelection()
        self.selectionObserver = selectionFilter(
            self.feature.baseObject[0], "Vertex"
        )
        Gui.Selection.addObserver(self.selectionObserver)
        self.selectionObserver.selection.connect(self.addReference)
        '''
        # toggle some view properties so that the base feature is easily
        # selectable. This makes editing the picked geometry easier
        self.feature.ViewObject.Selectable = False
        self.feature.ViewObject.Transparency = 50
        self.feature.baseObject[0].ViewObject.Visibility = True
        '''
        self.updateUI()

    def relief(self, val):
        self.feature.relief = val
        self.updateUI()

    def listWidgetReferences(self, item):
        pass

    def updateView(self, checked):
        self.updateUI()

    def updateUI(self):
        # enable/disable UI fields based on object state
        # recompute the features geometry if 'Update view' is checked
        if self.form.updateView.isChecked():
            error = False
            try:
                self.feature.recompute()
                self.form.errLabel.setVisible(False)
            except ValueError as E:
                errMsg = str(E)
                error = True
            except FreeCAD.Base.FreeCADError as E:
                # E.args[0] may either be a string or dict,
                # depending on FC version
                if type(E.args[0]) == str:
                    errMsg = E.args[0]
                elif type(E.args[0]) == dict:
                    errMsg = E.args[0]["sErrMsg"]
                else:
                    errMsg = str(E)  # this should never happen
                error = True
            if error:
                # show the error in both our task panel and in the report view
                FreeCAD.Console.PrintError(
                    (
                        "Failed to recompute "
                        f"{FreeCAD.ActiveDocument.Name}#"
                        f"{self.feature.Name}: {errMsg}\n"
                    )
                )
                self.form.errLabel.setText(f"Recompute failed\n {errMsg}")
                self.form.errLabel.setVisible(True)

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Cancel | QtGui.QDialogButtonBox.Ok)

    def accept(self):
        self.feature.touch()
        FreeCAD.ActiveDocument.recompute()
        Gui.ActiveDocument.resetEdit()
        Gui.Selection.removeObserver(self.selectionObserver)
        '''
        self.feature.ViewObject.Selectable = True
        self.feature.ViewObject.Transparency = self.initTransparency
        self.feature.baseObject[0].ViewObject.Visibility = self.initBaseVisible
        '''
        return True

    def reject(self):
        # reset the object to its old state
        for p, (val, expr) in self.oldState.items():
            self.feature.setExpression(p, expr)
            setattr(self.feature, p, val)
        # delete the object if it was just created
        if self.isNewFeature:
            # make the base profile visible again
            FreeCAD.ActiveDocument.removeObject(self.feature.Name)
        else:
            self.feature.touch()
        FreeCAD.ActiveDocument.recompute()
        Gui.ActiveDocument.resetEdit()
        Gui.Selection.removeObserver(self.selectionObserver)
        '''
        self.feature.ViewObject.ViewObject.Selectable = True
        self.feature.ViewObject.Transparency = self.initTransparency
        self.feature.baseObject[0].ViewObject.Visibility = self.initBaseVisible
        '''
        return True

    def focusUiStart(self):
        self.form.relief.setFocus()
        self.form.relief.selectAll()

    def showRefContextMenu(self, QPos):
        self.contextMenu = QtGui.QMenu()
        menu_item_remove_selected = self.contextMenu.addAction(
            "Remove"
        )
        menu_item_remove_selected.setShortcut(QtGui.QKeySequence.Delete)
        if not self.feature.baseObject[1]:
            menu_item_remove_selected.setDisabled(True)
        self.form.listWidgetReferences.connect(
            menu_item_remove_selected,
            QtCore.SIGNAL("triggered()"),
            self.removeReference
        )
        parentPosition = self.form.listWidgetReferences.mapToGlobal(
            QtCore.QPoint(0, 0)
        )
        self.contextMenu.move(parentPosition + QPos)
        self.contextMenu.show()

    def removeReference(self):
        deletedRef = self.form.listWidgetReferences.takeItem(
            self.form.listWidgetReferences.currentIndex().row()
        ).text()
        newList = list(self.feature.baseObject[1])
        newList.remove(deletedRef)
        self.feature.baseObject = (self.feature.baseObject[0], newList)
        self.updateUI()

    def addReference(self, text):
        if text not in self.feature.baseObject[1]:
            newList = list(self.feature.baseObject[1])
            newList.append(text)
            self.feature.baseObject = (self.feature.baseObject[0], newList)
            self.form.listWidgetReferences.addItem(text)
            self.updateUI()
