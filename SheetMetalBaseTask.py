# -*- coding: utf-8 -*-
###############################################################################
#
#  SheetMetalBaseTask.py
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
from PySide import QtGui
from SheetMetalUtil import iconPath
from SheetMetalBaseSolid import smBase


class SMBaseTaskPanel:
    def __init__(self, feature, isNewFeature):
        self.feature = feature
        self.isNewFeature = isNewFeature
        # encode current state so we can reset if the operation is cancelled
        oldState = {}
        trackedProperties = [
            "BendSide",
            "MidPlane",
            "Reverse",
            "length",
            "radius",
            "thickness",
        ]
        featureExprs = {k: v for (k, v) in feature.ExpressionEngine}
        for p in feature.PropertiesList:
            if p in trackedProperties:
                expr = featureExprs[p] if p in featureExprs else None
                oldState[p] = (feature.getPropertyByName(p), expr)
        self.oldState = oldState
        # import UI form from file
        d = os.path.realpath(__file__)
        d = os.path.dirname(d)
        uiPath = os.path.join(d, "UI/TaskBaseBendParameters.ui")
        loader = Gui.UiLoader()
        self.form = loader.load(uiPath)
        self.setupUI()

    def setupUI(self):
        # set window title and icon
        self.form.setWindowTitle("BaseBend Parameters")
        self.form.setWindowIcon(
            QtGui.QIcon(os.path.join(iconPath, "SheetMetal_AddBase.svg"))
        )
        # initialize UI fields to feature parameter values
        self.form.checkMidPlane.setChecked(self.feature.MidPlane)
        self.form.checkReversed.setChecked(self.feature.Reverse)
        self.form.materialThickness.setProperty("unit", "mm")
        self.form.flangeLength.setProperty("unit", "mm")
        self.form.bendRadius.setProperty("unit", "mm")
        self.form.materialThickness.setProperty(
            "rawValue", self.feature.thickness.Value
        )
        self.form.flangeLength.setProperty("rawValue", self.feature.length.Value)
        self.form.bendRadius.setProperty("rawValue", self.feature.radius.Value)
        # connect expression bindings
        Gui.ExpressionBinding(self.form.materialThickness).bind(
            self.feature, "thickness"
        )
        Gui.ExpressionBinding(self.form.flangeLength).bind(self.feature, "length")
        Gui.ExpressionBinding(self.form.bendRadius).bind(self.feature, "radius")
        self.form.bendSide.setCurrentText(self.feature.BendSide)
        # connect signals and slots
        self.form.checkMidPlane.toggled.connect(self.checkMidPlane)
        self.form.checkReversed.toggled.connect(self.checkReversed)
        self.form.materialThickness.valueChanged.connect(self.spinMaterialThickness)
        self.form.flangeLength.valueChanged.connect(self.spinFlangeLength)
        self.form.bendRadius.valueChanged.connect(self.spinBendRadius)
        self.form.bendSide.currentIndexChanged.connect(self.comboBendSide)
        self.form.checkUpdateView.toggled.connect(self.checkUpdateView)
        # hide the error message indicator by default
        self.form.errLabel.setVisible(False)
        self.updateUI()

    def checkMidPlane(self, checked):
        self.feature.MidPlane = checked
        self.updateUI()

    def checkReversed(self, checked):
        self.feature.Reverse = checked
        self.updateUI()

    def spinMaterialThickness(self, val):
        self.feature.thickness = val
        self.updateUI()

    def spinFlangeLength(self, val):
        self.feature.length = val
        self.updateUI()

    def spinBendRadius(self, val):
        self.feature.radius = val
        self.updateUI()

    def comboBendSide(self, index):
        self.feature.BendSide = str(self.form.bendSide.itemText(index))
        self.updateUI()

    def checkUpdateView(self, checked):
        self.updateUI()

    def updateUI(self):
        # enable/disable UI fields based on object state
        self.form.checkReversed.setEnabled(not self.feature.MidPlane)
        profileClosed = self.feature.BendSketch.Shape.Wires[0].isClosed()
        self.form.bendParameters.setEnabled(not profileClosed)
        # set a text field to indicate whether the profile is closed
        if profileClosed:
            self.form.labelBaseStatus.setText("Base object is a closed profile")
        else:
            self.form.labelBaseStatus.setText("Base object is an open profile")
        # recompute the features geometry if 'Update view' is checked
        if self.form.checkUpdateView.isChecked():
            error = False
            try:
                self.feature.Shape = smBase(
                    thk=self.feature.thickness.Value,
                    length=self.feature.length.Value,
                    radius=self.feature.radius.Value,
                    Side=self.feature.BendSide,
                    midplane=self.feature.MidPlane,
                    reverse=self.feature.Reverse,
                    MainObject=self.feature.BendSketch,
                )
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
        return True

    def reject(self):
        # reset the object to its old state
        for p, (val, expr) in self.oldState.items():
            self.feature.setExpression(p, expr)
            setattr(self.feature, p, val)
        # delete the object if it was just created
        if self.isNewFeature:
            # make the base profile visible again
            self.feature.BendSketch.Visibility = True
            FreeCAD.ActiveDocument.removeObject(self.feature.Name)
        else:
            self.feature.touch()
        FreeCAD.ActiveDocument.recompute()
        Gui.ActiveDocument.resetEdit()
        return True

    def focusUiStart(self):
        self.form.materialThickness.setFocus()
        self.form.materialThickness.selectAll()
