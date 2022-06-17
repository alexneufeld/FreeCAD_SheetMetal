# -*- coding: utf-8 -*-
###############################################################################
#
#  SheetMetalRelief.py
#
#  Copyright 2015 Shai Seger <shaise at gmail dot com>
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

from FreeCAD import Gui
from PySide import QtCore
import FreeCAD
import FreeCADGui
import Part
import os
from SheetMetalCmd import iconPath
from SheetMetalCmd import smElementMapVersion
from SheetMetalCmd import smIsPartDesign
from SheetMetalCmd import smIsOperationLegal
from SheetMetalReliefSolid import reliefMakeSolid
from SheetMetalReliefTask import SMReliefTaskPanel


class SMRelief:
    def __init__(self, obj):
        '''"Add Relief to Solid"'''
        selobj = Gui.Selection.getSelectionEx()[0]

        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Relief Size")
        obj.addProperty(
            "App::PropertyLength", "relief", "Parameters", _tip_
        ).relief = 2.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Base Object")
        obj.addProperty(
            "App::PropertyLinkSub", "baseObject", "Parameters", _tip_
        ).baseObject = (selobj.Object, selobj.SubElementNames)
        obj.Proxy = self

    def getElementMapVersion(self, _fp, ver, _prop, restored):
        if not restored:
            return smElementMapVersion + ver

    def execute(self, fp):
        # pass selected object shape
        Main_Object = fp.baseObject[0].Shape.copy()
        s = reliefMakeSolid(
            relief=fp.relief.Value,
            selVertexNames=fp.baseObject[1],
            MainObject=Main_Object,
        )
        fp.Shape = s


class SMReliefViewProviderTree:
    "A View provider that nests children objects under the created one"

    def __init__(self, obj):
        obj.Proxy = self
        self.Object = obj.Object

    def attach(self, obj):
        self.Object = obj.Object
        return

    def setupContextMenu(self, viewObject, menu):
        action = menu.addAction(
            FreeCAD.Qt.translate("QObject", "Edit %1").replace(
                "%1", viewObject.Object.Label
            )
        )
        action.triggered.connect(lambda: self.startDefaultEditMode(viewObject))
        return False

    def startDefaultEditMode(self, viewObject):
        document = viewObject.Document.Document
        if not document.HasPendingTransaction:
            text = FreeCAD.Qt.translate("QObject", "Edit %1").replace(
                "%1", viewObject.Object.Label
            )
            document.openTransaction(text)
        viewObject.Document.setEdit(viewObject.Object, 0)

    def updateData(self, fp, prop):
        return

    def getDisplayModes(self, obj):
        modes = []
        return modes

    def setDisplayMode(self, mode):
        return mode

    def onChanged(self, vp, prop):
        return

    def __getstate__(self):
        #        return {'ObjectName' : self.Object.Name}
        return None

    def __setstate__(self, state):
        if state is not None:
            import FreeCAD

            doc = FreeCAD.ActiveDocument  # crap
            self.Object = doc.getObject(state["ObjectName"])

    def claimChildren(self):
        objs = []
        if hasattr(self.Object, "baseObject"):
            objs.append(self.Object.baseObject[0])
        return objs

    def getIcon(self):
        return os.path.join(iconPath, "SheetMetal_AddRelief.svg")

    def setEdit(self, vobj, mode):
        taskd = SMReliefTaskPanel(vobj.Object, False)
        Gui.Control.showDialog(taskd)
        taskd.focusUiStart()
        return True

    def unsetEdit(self, vobj, mode):
        Gui.Control.closeDialog()
        return False


class SMReliefViewProviderFlat:
    "A View provider that nests children objects under the created one"

    def __init__(self, obj):
        obj.Proxy = self
        self.Object = obj.Object

    def attach(self, obj):
        self.Object = obj.Object
        return

    def updateData(self, fp, prop):
        return

    def getDisplayModes(self, obj):
        modes = []
        return modes

    def setDisplayMode(self, mode):
        return mode

    def onChanged(self, vp, prop):
        return

    def __getstate__(self):
        #        return {'ObjectName' : self.Object.Name}
        return None

    def __setstate__(self, state):
        if state is not None:
            import FreeCAD

            doc = FreeCAD.ActiveDocument  # crap
            self.Object = doc.getObject(state["ObjectName"])

    def claimChildren(self):

        return []

    def getIcon(self):
        return os.path.join(iconPath, "SheetMetal_AddRelief.svg")

    def setEdit(self, vobj, mode):
        if mode == 0:  # default edit mode
            taskd = SMReliefTaskPanel(vobj.Object, False)
            Gui.Control.showDialog(taskd)
            taskd.focusUiStart()
        return True

    def unsetEdit(self, vobj, mode):
        if mode == 0:
            Gui.Control.closeDialog()
        return False


class AddReliefCommandClass:
    """Add Relief command"""

    def GetResources(self):
        return {
            "Pixmap": os.path.join(
                iconPath, "SheetMetal_AddRelief.svg"
            ),  # the name of a svg file available in the resources
            "MenuText": QtCore.QT_TRANSLATE_NOOP("SheetMetal", "Make Relief"),
            "Accel": "S, R",
            "ToolTip": QtCore.QT_TRANSLATE_NOOP(
                "SheetMetal",
                "Modify an Individual solid corner to create Relief.\n"
                "1. Select Vertex(es) to create Relief on Solid corner Vertex(es).\n"
                "2. Use Property editor to modify default parameters",
            ),
        }

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        view = Gui.ActiveDocument.ActiveView
        activeBody = None
        selobj = Gui.Selection.getSelectionEx()[0].Object
        if hasattr(view, "getActiveObject"):
            activeBody = view.getActiveObject("pdbody")
        if not smIsOperationLegal(activeBody, selobj):
            return
        doc.openTransaction("Add Relief")
        if activeBody is None or not smIsPartDesign(selobj):
            a = doc.addObject("Part::FeaturePython", "Relief")
            SMRelief(a)
            SMReliefViewProviderTree(a.ViewObject)
        else:
            # FreeCAD.Console.PrintLog("found active body: " + activeBody.Name)
            a = doc.addObject("PartDesign::FeaturePython", "Relief")
            SMRelief(a)
            SMReliefViewProviderFlat(a.ViewObject)
            activeBody.addObject(a)
        FreeCADGui.Selection.clearSelection()
        doc.recompute()
        doc.commitTransaction()
        panel = SMReliefTaskPanel(a, True)
        Gui.Control.showDialog(panel)
        panel.focusUiStart()
        return

    def IsActive(self):
        if (
            len(Gui.Selection.getSelection()) < 1
            or len(Gui.Selection.getSelectionEx()[0].SubElementNames) < 1
        ):
            return False
        #    selobj = Gui.Selection.getSelection()[0]
        for selVertex in Gui.Selection.getSelectionEx()[0].SubObjects:
            if type(selVertex) != Part.Vertex:
                return False
        return True


Gui.addCommand("SMMakeRelief", AddReliefCommandClass())
