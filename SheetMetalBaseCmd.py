# -*- coding: utf-8 -*-
###############################################################################
#
#  SheetMetalBaseCmd.py
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
import FreeCAD
import os.path
from PySide import QtCore
from SheetMetalBaseSolid import smBase
from SheetMetalBaseTask import SMBaseTaskPanel
from SheetMetalCmd import iconPath


class SMBaseBend:
    def __init__(self, obj):
        '''"Add wall or Wall with radius bend"'''
        selobj = Gui.Selection.getSelectionEx()[0]

        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Bend Radius")
        obj.addProperty(
            "App::PropertyLength", "radius", "Parameters", _tip_
        ).radius = 1.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Thickness of sheetmetal")
        obj.addProperty(
            "App::PropertyLength", "thickness", "Parameters", _tip_
        ).thickness = 1.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Relief Type")
        obj.addProperty(
            "App::PropertyEnumeration", "BendSide", "Parameters", _tip_
        ).BendSide = ["Outside", "Inside", "Middle"]
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Length of wall")
        obj.addProperty(
            "App::PropertyLength", "length", "Parameters", _tip_
        ).length = 100.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Wall Sketch object")
        obj.addProperty(
            "App::PropertyLink", "BendSketch", "Parameters", _tip_
        ).BendSketch = selobj.Object
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Extrude Symmetric to Plane")
        obj.addProperty(
            "App::PropertyBool", "MidPlane", "Parameters", _tip_
        ).MidPlane = False
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Reverse Extrusion Direction")
        obj.addProperty(
            "App::PropertyBool", "Reverse", "Parameters", _tip_
        ).Reverse = False
        obj.Proxy = self

    def execute(self, fp):
        s = smBase(
            thk=fp.thickness.Value,
            length=fp.length.Value,
            radius=fp.radius.Value,
            Side=fp.BendSide,
            midplane=fp.MidPlane,
            reverse=fp.Reverse,
            MainObject=fp.BendSketch,
        )

        fp.Shape = s
        obj = Gui.ActiveDocument.getObject(fp.BendSketch.Name)
        if obj:
            obj.Visibility = False


class SMBaseViewProvider:
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
        #    return {'ObjectName' : self.Object.Name}
        return None

    def __setstate__(self, state):
        if state is not None:
            import FreeCAD

            doc = FreeCAD.ActiveDocument  # crap
            self.Object = doc.getObject(state["ObjectName"])

    def setEdit(self, vobj, mode):
        taskd = SMBaseTaskPanel(vobj.Object, False)
        Gui.Control.showDialog(taskd)
        taskd.focusUiStart()
        return True

    def unsetEdit(self, vobj, mode):
        Gui.Control.closeDialog()
        # self.Object.baseObject[0].ViewObject.Visibility=False
        # self.Object.ViewObject.Visibility=True
        return False

    def claimChildren(self):
        objs = []
        if hasattr(self.Object, "BendSketch"):
            objs.append(self.Object.BendSketch)
        return objs

    def getIcon(self):
        return os.path.join(iconPath, "SheetMetal_AddBase.svg")


class AddBaseCommandClass:
    """Add Base Wall command"""

    def GetResources(self):
        return {
            "Pixmap": os.path.join(
                iconPath, "SheetMetal_AddBase.svg"
            ),  # the name of a svg file available in the resources
            "MenuText": QtCore.QT_TRANSLATE_NOOP("SheetMetal", "Make Base Wall"),
            "Accel": "C, B",
            "ToolTip": QtCore.QT_TRANSLATE_NOOP(
                "SheetMetal",
                "Create a sheetmetal wall from a sketch\n"
                "1. Select a Skech to create bends with walls.\n"
                "2. Use Property editor to modify other parameters",
            ),
        }

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        view = Gui.ActiveDocument.ActiveView
        activeBody = None
        #    selobj = Gui.Selection.getSelectionEx()[0].Object
        if hasattr(view, "getActiveObject"):
            activeBody = view.getActiveObject("pdbody")
        #    if not smIsOperationLegal(activeBody, selobj):
        #        return
        doc.openTransaction("BaseBend")
        if activeBody is None:
            a = doc.addObject("Part::FeaturePython", "BaseBend")
            SMBaseBend(a)
            SMBaseViewProvider(a.ViewObject)
        else:
            # FreeCAD.Console.PrintLog("found active body: " + activeBody.Name)
            a = doc.addObject("PartDesign::FeaturePython", "BaseBend")
            SMBaseBend(a)
            SMBaseViewProvider(a.ViewObject)
            activeBody.addObject(a)
        doc.recompute()
        doc.commitTransaction()
        panel = SMBaseTaskPanel(a, True)
        Gui.Control.showDialog(panel)
        panel.focusUiStart()
        return

    def IsActive(self):
        if len(Gui.Selection.getSelection()) != 1:
            return False
        selobj = Gui.Selection.getSelection()[0]
        if not (
            selobj.isDerivedFrom("Sketcher::SketchObject")
            or selobj.isDerivedFrom("PartDesign::ShapeBinder")
            or selobj.isDerivedFrom("PartDesign::SubShapeBinder")
        ):
            return False
        return True


Gui.addCommand("SMBase", AddBaseCommandClass())
