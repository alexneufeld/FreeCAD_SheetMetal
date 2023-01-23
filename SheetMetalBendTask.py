# -*- coding: utf-8 -*-
###############################################################################
#
#  SheetMetalBendTask.py
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
from SheetMetalCmd import iconPath


class SMBendTaskPanel:
    def __init__(self, feature, isNewFeature):
        self.feature = feature
        self.isNewFeature = isNewFeature
        # encode current state so we can reset if the operation is cancelled
        trackedProperties = [
            "AutoMiter",
            # "BaseFeature",
            "BendType",
            # "LengthList",
            "ReliefFactor",
            # "Sketch",
            "UseReliefFactor",
            "angle",
            # "baseObject",
            # "bendAList",
            "extend1",
            "extend2",
            "gap1",
            "gap2",
            "invert",
            "kfactor",
            "length",
            "maxExtendDist",
            "minGap",
            "minReliefGap",
            "miterangle1",
            "miterangle2",
            "offset",
            "radius",
            "reliefType",
            "reliefd",
            "reliefw",
            # "sketchflip",
            # "sketchinvert",
            "unfold",
        ]
        oldState = {}
        featureExprs = {k: v for (k, v) in feature.ExpressionEngine}
        for p in feature.PropertiesList:
            if p in trackedProperties:
                expr = featureExprs[p] if p in featureExprs else None
                oldState[p] = (feature.getPropertyByName(p), expr)
        self.oldState = oldState
        # import UI form from file
        d = os.path.realpath(__file__)
        d = os.path.dirname(d)
        uiPath = os.path.join(d, "UI/TaskBendParameters.ui")
        loader = Gui.UiLoader()
        self.form = loader.load(uiPath)
        self.setupUI()

    def setupUI(self):
        # set window title and icon
        self.form.setWindowTitle("Bend Parameters")
        self.form.setWindowIcon(
            QtGui.QIcon(os.path.join(iconPath, "SheetMetal_AddBend.svg"))
        )
        # initialize UI fields to feature parameter values
        self.form.AutoMiter.setChecked(self.feature.AutoMiter)
        self.form.BendType.setCurrentText(self.feature.BendType)
        self.form.ReliefFactor.setValue(self.feature.ReliefFactor.Value)
        self.form.UseReliefFactor.setChecked(self.feature.UseReliefFactor)
        self.form.angle.setProperty("rawValue", self.feature.angle)
        self.form.extend1.setProperty("rawValue", self.feature.extend1)
        self.form.extend2.setProperty("rawValue", self.feature.extend2)
        self.form.gap1.setProperty("rawValue", self.feature.gap1)
        self.form.gap2.setProperty("rawValue", self.feature.gap2)
        self.form.invert.setChecked(self.feature.invert)
        self.form.kfactor.setValue(self.feature.kfactor.Value)
        self.form.length.setProperty("rawValue", self.feature.length)
        self.form.maxExtendDist.setProperty("rawValue", self.feature.maxExtendDist)
        self.form.minGap.setProperty("rawValue", self.feature.minGap)
        self.form.minReliefGap.setProperty("rawValue", self.feature.minReliefGap)
        self.form.miterangle1.setProperty("rawValue", self.feature.miterangle1)
        self.form.miterangle2.setProperty("rawValue", self.feature.miterangle2)
        self.form.offset.setProperty("rawValue", self.feature.offset)
        self.form.bendRadius.setProperty("rawValue", self.feature.bendRadius)
        self.form.reliefType.setCurrentText(self.feature.reliefType)
        self.form.reliefd.setProperty("rawValue", self.feature.reliefd)
        self.form.reliefw.setProperty("rawValue", self.feature.reliefw)
        self.form.unfold.setChecked(self.feature.unfold)
        # connect expression bindings
        Gui.ExpressionBinding(self.form.ReliefFactor).bind(self.feature, "ReliefFactor")
        Gui.ExpressionBinding(self.form.angle).bind(self.feature, "angle")
        Gui.ExpressionBinding(self.form.extend1).bind(self.feature, "extend1")
        Gui.ExpressionBinding(self.form.extend2).bind(self.feature, "extend2")
        Gui.ExpressionBinding(self.form.gap1).bind(self.feature, "gap1")
        Gui.ExpressionBinding(self.form.gap2).bind(self.feature, "gap2")
        Gui.ExpressionBinding(self.form.kfactor).bind(self.feature, "kfactor")
        Gui.ExpressionBinding(self.form.length).bind(self.feature, "length")
        Gui.ExpressionBinding(self.form.maxExtendDist).bind(
            self.feature, "maxExtendDist"
        )
        Gui.ExpressionBinding(self.form.minGap).bind(self.feature, "minGap")
        Gui.ExpressionBinding(self.form.minReliefGap).bind(self.feature, "minReliefGap")
        Gui.ExpressionBinding(self.form.miterangle1).bind(self.feature, "miterangle1")
        Gui.ExpressionBinding(self.form.miterangle2).bind(self.feature, "miterangle2")
        Gui.ExpressionBinding(self.form.offset).bind(self.feature, "offset")
        Gui.ExpressionBinding(self.form.bendRadius).bind(self.feature, "bendRadius")
        Gui.ExpressionBinding(self.form.reliefd).bind(self.feature, "reliefd")
        Gui.ExpressionBinding(self.form.reliefw).bind(self.feature, "reliefw")
        # connect signals and slots
        self.form.AutoMiter.toggled.connect(self.AutoMiter)
        self.form.BendType.currentIndexChanged.connect(self.BendType)
        self.form.ReliefFactor.valueChanged.connect(self.ReliefFactor)
        self.form.UseReliefFactor.toggled.connect(self.UseReliefFactor)
        self.form.angle.valueChanged.connect(self.angle)
        self.form.extend1.valueChanged.connect(self.extend1)
        self.form.extend2.valueChanged.connect(self.extend2)
        self.form.gap1.valueChanged.connect(self.gap1)
        self.form.gap2.valueChanged.connect(self.gap2)
        self.form.invert.toggled.connect(self.invert)
        self.form.kfactor.valueChanged.connect(self.kfactor)
        self.form.length.valueChanged.connect(self.length)
        self.form.maxExtendDist.valueChanged.connect(self.maxExtendDist)
        self.form.minGap.valueChanged.connect(self.minGap)
        self.form.minReliefGap.valueChanged.connect(self.minReliefGap)
        self.form.miterangle1.valueChanged.connect(self.miterangle1)
        self.form.miterangle2.valueChanged.connect(self.miterangle2)
        self.form.offset.valueChanged.connect(self.offset)
        self.form.bendRadius.valueChanged.connect(self.bendRadius)
        self.form.reliefType.currentIndexChanged.connect(self.reliefType)
        self.form.reliefd.valueChanged.connect(self.reliefd)
        self.form.reliefw.valueChanged.connect(self.reliefw)
        self.form.unfold.toggled.connect(self.unfold)
        self.form.updateView.toggled.connect(self.updateView)
        self.form.showAdvanced.toggled.connect(self.showAdvanced)
        # some widgets should be hidden by default
        self.form.errLabel.setVisible(False)
        self.form.AdvancedOptions.setVisible(False)
        self.updateUI()

    def AutoMiter(self, checked):
        self.feature.AutoMiter = checked
        self.updateUI()

    def BendType(self, index):
        self.feature.BendType = str(self.form.BendType.itemText(index))
        self.updateUI()

    def ReliefFactor(self, val):
        self.feature.ReliefFactor = val
        self.updateUI()

    def UseReliefFactor(self, checked):
        self.feature.UseReliefFactor = checked
        self.updateUI()

    def angle(self, val):
        self.feature.angle = val
        self.updateUI()

    def extend1(self, val):
        self.feature.extend1 = val
        self.updateUI()

    def extend2(self, val):
        self.feature.extend2 = val
        self.updateUI()

    def gap1(self, val):
        self.feature.gap1 = val
        self.updateUI()

    def gap2(self, val):
        self.feature.gap2 = val
        self.updateUI()

    def invert(self, checked):
        self.feature.invert = checked
        self.updateUI()

    def kfactor(self, val):
        self.feature.kfactor = val
        self.updateUI()

    def length(self, val):
        self.feature.length = val
        self.updateUI()

    def maxExtendDist(self, val):
        self.feature.maxExtendDist = val
        self.updateUI()

    def minGap(self, val):
        self.feature.minGap = val
        self.updateUI()

    def minReliefGap(self, val):
        self.feature.minReliefGap = val
        self.updateUI()

    def miterangle1(self, val):
        self.feature.miterangle1 = val
        self.updateUI()

    def miterangle2(self, val):
        self.feature.miterangle2 = val
        self.updateUI()

    def offset(self, val):
        self.feature.offset = val
        self.updateUI()

    def bendRadius(self, val):
        self.feature.bendRadius = val
        self.updateUI()

    def reliefType(self, index):
        self.feature.reliefType = str(self.form.reliefType.itemText(index))
        self.updateUI()

    def reliefd(self, val):
        self.feature.reliefd = val
        self.updateUI()

    def reliefw(self, val):
        self.feature.reliefw = val
        self.updateUI()

    def unfold(self, checked):
        self.feature.unfold = checked
        self.updateUI()

    def updateView(self, checked):
        self.updateUI()

    def showAdvanced(self, checked):
        self.updateUI()

    def updateUI(self):
        # enable/disable UI fields based on object state
        self.form.advancedOptions.setVisible(self.form.showAdvanced.isChecked())
        self.form.offsetWidget.setEnabled(
            self.form.bendType.getCurrentText() == "Offset"
        )
        self.form.miterangle1.setEnabled(self.form.AutoMiter.isChecked())
        self.form.miterangle2.setEnabled(self.form.AutoMiter.isChecked())
        self.form.ReliefFactor.setEnabled(self.form.UseReliefFactor.isChecked())
        # recompute the features geometry if 'Update view' is checked
        if self.form.checkUpdateView.isChecked():
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
        self.form.length.setFocus()
        self.form.length.selectAll()
