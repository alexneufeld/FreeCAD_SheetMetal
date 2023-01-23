# -*- coding: utf-8 -*-
###############################################################################
#
#  SheetMetalWallCmd.py
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

from PySide import QtCore
import FreeCAD
import FreeCADGui as Gui
import FreeCADGui
import Part
import os
from SheetMetalUtil import smElementMapVersion
from SheetMetalWallCmd import smRestrict
from SheetMetalWallCmd import sheet_thk
from SheetMetalWallCmd import getSketchDetails
from SheetMetalWallCmd import smBend
from SheetMetalWallCmd import smGetFace
from SheetMetalWallCmd import smIsOperationLegal
from SheetMetalWallCmd import smIsPartDesign
from SheetMetalUtil import iconPath
from SheetMetalWallTask import SMBendWallTaskPanel


class SMBendWall:
    def __init__(self, obj):
        '''"Add Wall with radius bend"'''
        selobj = Gui.Selection.getSelectionEx()[0]

        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Bend Radius")
        obj.addProperty(
            "App::PropertyLength", "radius", "Parameters", _tip_
        ).radius = 1.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Length of Wall")
        obj.addProperty(
            "App::PropertyLength", "length", "Parameters", _tip_
        ).length = 10.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Gap from Left Side")
        obj.addProperty("App::PropertyDistance", "gap1", "Parameters", _tip_).gap1 = 0.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Gap from Right Side")
        obj.addProperty("App::PropertyDistance", "gap2", "Parameters", _tip_).gap2 = 0.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Invert Bend Direction")
        obj.addProperty(
            "App::PropertyBool", "invert", "Parameters", _tip_
        ).invert = False
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Bend Type")
        obj.addProperty(
            "App::PropertyEnumeration", "BendType", "Parameters", _tip_
        ).BendType = [
            "Material Outside",
            "Material Inside",
            "Thickness Outside",
            "Offset",
        ]
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Bend Angle")
        obj.addProperty("App::PropertyAngle", "angle", "Parameters", _tip_).angle = 90.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Relief Type")
        obj.addProperty(
            "App::PropertyEnumeration", "reliefType", "ParametersRelief", _tip_
        ).reliefType = ["Rectangle", "Round"]
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Use Relief Factor")
        obj.addProperty(
            "App::PropertyBool", "UseReliefFactor", "ParametersRelief", _tip_
        ).UseReliefFactor = False
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Relief Factor")
        obj.addProperty(
            "App::PropertyFloat", "ReliefFactor", "ParametersRelief", _tip_
        ).ReliefFactor = 0.7
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Relief Width")
        obj.addProperty(
            "App::PropertyLength", "reliefw", "ParametersRelief", _tip_
        ).reliefw = 0.8
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Relief Depth")
        obj.addProperty(
            "App::PropertyLength", "reliefd", "ParametersRelief", _tip_
        ).reliefd = 1.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Minimum Gap to Relief Cut")
        obj.addProperty(
            "App::PropertyLength", "minReliefGap", "ParametersRelief", _tip_
        ).minReliefGap = 1.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Base Object")
        obj.addProperty(
            "App::PropertyLinkSub", "baseObject", "Parameters", _tip_
        ).baseObject = (selobj.Object, selobj.SubElementNames)
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Extend from Left Side")
        obj.addProperty(
            "App::PropertyDistance", "extend1", "ParametersEx", _tip_
        ).extend1 = 0.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Extend from Right Side")
        obj.addProperty(
            "App::PropertyDistance", "extend2", "ParametersEx", _tip_
        ).extend2 = 0.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Enable Auto Miter")
        obj.addProperty(
            "App::PropertyBool", "AutoMiter", "ParametersEx", _tip_
        ).AutoMiter = True
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Auto Miter Minimum Gap")
        obj.addProperty(
            "App::PropertyLength", "minGap", "ParametersEx", _tip_
        ).minGap = 0.1
        _tip_ = QtCore.QT_TRANSLATE_NOOP(
            "App::Property", "Auto Miter maximum Extend Distance"
        )
        obj.addProperty(
            "App::PropertyLength", "maxExtendDist", "ParametersEx", _tip_
        ).maxExtendDist = 5.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP(
            "App::Property", "Bend Miter Angle from Left Side"
        )
        obj.addProperty(
            "App::PropertyAngle", "miterangle1", "ParametersEx", _tip_
        ).miterangle1 = 0.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP(
            "App::Property", "Bend Miter Angle from Right Side"
        )
        obj.addProperty(
            "App::PropertyAngle", "miterangle2", "ParametersEx", _tip_
        ).miterangle2 = 0.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Offset Bend")
        obj.addProperty(
            "App::PropertyDistance", "offset", "ParametersEx", _tip_
        ).offset = 0.0
        _tip_ = QtCore.QT_TRANSLATE_NOOP(
            "App::Property", "Shows Unfold View of Current Bend"
        )
        obj.addProperty(
            "App::PropertyBool", "unfold", "ParametersEx", _tip_
        ).unfold = False
        _tip_ = QtCore.QT_TRANSLATE_NOOP(
            "App::Property",
            "Location of Neutral Line. Caution: Using ANSI standards, not DIN.",
        )
        obj.addProperty(
            "App::PropertyFloatConstraint", "kfactor", "ParametersEx", _tip_
        ).kfactor = (0.5, 0.0, 1.0, 0.01)
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Sketch Object")
        obj.addProperty("App::PropertyLink", "Sketch", "ParametersEx2", _tip_)
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Flip Sketch Direction")
        obj.addProperty(
            "App::PropertyBool", "sketchflip", "ParametersEx2", _tip_
        ).sketchflip = False
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Invert Sketch Start")
        obj.addProperty(
            "App::PropertyBool", "sketchinvert", "ParametersEx2", _tip_
        ).sketchinvert = False
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Length of Wall List")
        obj.addProperty("App::PropertyFloatList", "LengthList", "ParametersEx3", _tip_)
        _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Bend Angle List")
        obj.addProperty("App::PropertyFloatList", "bendAList", "ParametersEx3", _tip_)
        obj.Proxy = self

    def getElementMapVersion(self, _fp, ver, _prop, restored):
        if not restored:
            return smElementMapVersion + ver

    def execute(self, fp):
        '''"Print a short message when doing a recomputation, this method is mandatory"'''
        if not hasattr(fp, "miterangle1"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP(
                "App::Property", "Bend Miter Angle from Left Side"
            )
            fp.addProperty(
                "App::PropertyAngle", "miterangle1", "ParametersMiterangle", _tip_
            ).miterangle1 = 0.0
            _tip_ = QtCore.QT_TRANSLATE_NOOP(
                "App::Property", "Bend Miter Angle from Right Side"
            )
            fp.addProperty(
                "App::PropertyAngle", "miterangle2", "ParametersMiterangle", _tip_
            ).miterangle2 = 0.0

        if not hasattr(fp, "AutoMiter"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Enable Auto Miter")
            fp.addProperty(
                "App::PropertyBool", "AutoMiter", "ParametersEx", _tip_
            ).AutoMiter = True

        if not hasattr(fp, "reliefType"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Relief Type")
            fp.addProperty(
                "App::PropertyEnumeration", "reliefType", "ParametersRelief", _tip_
            ).reliefType = ["Rectangle", "Round"]

        if not hasattr(fp, "extend1"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Extend from Left Side")
            fp.addProperty(
                "App::PropertyDistance", "extend1", "Parameters", _tip_
            ).extend1 = 0.0
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Extend from Right Side")
            fp.addProperty(
                "App::PropertyDistance", "extend2", "Parameters", _tip_
            ).extend2 = 0.0

        if not hasattr(fp, "unfold"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP(
                "App::Property", "Shows Unfold View of Current Bend"
            )
            fp.addProperty(
                "App::PropertyBool", "unfold", "ParametersEx", _tip_
            ).unfold = False

        if not hasattr(fp, "kfactor"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP(
                "App::Property",
                "Location of Neutral Line. Caution: Using ANSI standards, not DIN.",
            )
            fp.addProperty(
                "App::PropertyFloatConstraint", "kfactor", "ParametersEx", _tip_
            ).kfactor = (0.5, 0.0, 1.0, 0.01)

        if not hasattr(fp, "BendType"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Bend Type")
            fp.addProperty(
                "App::PropertyEnumeration", "BendType", "Parameters", _tip_
            ).BendType = [
                "Material Outside",
                "Material Inside",
                "Thickness Outside",
                "Offset",
            ]
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Offset Bend")
            fp.addProperty(
                "App::PropertyDistance", "offset", "ParametersEx", _tip_
            ).offset = 0.0

        if not hasattr(fp, "ReliefFactor"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Use Relief Factor")
            fp.addProperty(
                "App::PropertyBool", "UseReliefFactor", "ParametersRelief", _tip_
            ).UseReliefFactor = False
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Relief Factor")
            fp.addProperty(
                "App::PropertyFloat", "ReliefFactor", "ParametersRelief", _tip_
            ).ReliefFactor = 0.7

        if not hasattr(fp, "Sketch"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Sketch Object")
            fp.addProperty("App::PropertyLink", "Sketch", "ParametersEx2", _tip_)
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Flip Sketch Direction")
            fp.addProperty(
                "App::PropertyBool", "sketchflip", "ParametersEx2", _tip_
            ).sketchflip = False
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Invert Sketch Start")
            fp.addProperty(
                "App::PropertyBool", "sketchinvert", "ParametersEx2", _tip_
            ).sketchinvert = False
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Length of Wall List")
            fp.addProperty(
                "App::PropertyFloatList", "LengthList", "ParametersEx3", _tip_
            )
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Bend Angle List")
            fp.addProperty(
                "App::PropertyFloatList", "bendAList", "ParametersEx3", _tip_
            )

        if not hasattr(fp, "minGap"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP("App::Property", "Auto Miter Minimum Gap")
            fp.addProperty(
                "App::PropertyLength", "minGap", "ParametersEx", _tip_
            ).minGap = 0.2
            _tip_ = QtCore.QT_TRANSLATE_NOOP(
                "App::Property", "Auto Miter maximum Extend Distance"
            )
            fp.addProperty(
                "App::PropertyLength", "maxExtendDist", "ParametersEx", _tip_
            ).maxExtendDist = 5.0

        if not hasattr(fp, "minReliefGap"):
            _tip_ = QtCore.QT_TRANSLATE_NOOP(
                "App::Property", "Minimum Gap to Relief Cut"
            )
            fp.addProperty(
                "App::PropertyLength", "minReliefGap", "ParametersEx", _tip_
            ).minReliefGap = 1.0

        # restrict some params
        fp.miterangle1.Value = smRestrict(fp.miterangle1.Value, -80.0, 80.0)
        fp.miterangle2.Value = smRestrict(fp.miterangle2.Value, -80.0, 80.0)

        # get LengthList, bendAList
        bendAList = [fp.angle.Value]
        LengthList = [fp.length.Value]
        # print face

        # pass selected object shape
        Main_Object = fp.baseObject[0].Shape.copy()
        face = fp.baseObject[1]
        thk = sheet_thk(Main_Object, face[0])

        if fp.Sketch:
            WireList = fp.Sketch.Shape.Wires[0]
            if not (WireList.isClosed()):
                LengthList, bendAList = getSketchDetails(
                    fp.Sketch, fp.sketchflip, fp.sketchinvert, fp.radius.Value, thk
                )
            else:
                if fp.Sketch.Support:
                    fp.baseObject = (fp.Sketch.Support[0][0], fp.Sketch.Support[0][1])
                LengthList = [10.0]
        fp.LengthList = LengthList
        fp.bendAList = bendAList
        # print(LengthList, bendAList)

        # extend value needed for first bend set only
        extend1_list = [0.0 for n in range(len(LengthList))]
        extend2_list = [0.0 for n in range(len(LengthList))]
        extend1_list[0] = fp.extend1.Value
        extend2_list[0] = fp.extend2.Value
        # print(extend1_list, extend2_list)

        # gap value needed for first bend set only
        gap1_list = [0.0 for n in range(len(LengthList))]
        gap2_list = [0.0 for n in range(len(LengthList))]
        gap1_list[0] = fp.gap1.Value
        gap2_list[0] = fp.gap2.Value
        # print(gap1_list, gap2_list)

        for i in range(len(LengthList)):
            s, f = smBend(
                thk,
                bendR=fp.radius.Value,
                bendA=bendAList[i],
                miterA1=fp.miterangle1.Value,
                miterA2=fp.miterangle2.Value,
                BendType=fp.BendType,
                flipped=fp.invert,
                unfold=fp.unfold,
                extLen=LengthList[i],
                reliefType=fp.reliefType,
                gap1=gap1_list[i],
                gap2=gap2_list[i],
                reliefW=fp.reliefw.Value,
                reliefD=fp.reliefd.Value,
                minReliefgap=fp.minReliefGap.Value,
                extend1=extend1_list[i],
                extend2=extend2_list[i],
                kfactor=fp.kfactor,
                offset=fp.offset.Value,
                ReliefFactor=fp.ReliefFactor,
                UseReliefFactor=fp.UseReliefFactor,
                automiter=fp.AutoMiter,
                selFaceNames=face,
                MainObject=Main_Object,
                sketch=fp.Sketch,
                mingap=fp.minGap.Value,
                maxExtendGap=fp.maxExtendDist.Value,
            )
            faces = smGetFace(f, s)
            face = faces
            Main_Object = s

        fp.Shape = s
        fp.baseObject[0].ViewObject.Visibility = False
        if fp.Sketch:
            fp.Sketch.ViewObject.Visibility = False


class SMViewProviderTree:
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
        objs = []
        if hasattr(self.Object, "baseObject"):
            objs.append(self.Object.baseObject[0])
        if hasattr(self.Object, "Sketch"):
            objs.append(self.Object.Sketch)
        return objs

    def getIcon(self):
        return os.path.join(iconPath, "SheetMetal_AddWall.svg")

    def setEdit(self, vobj, mode):
        taskd = SMBendWallTaskPanel()
        taskd.obj = vobj.Object
        taskd.update()
        self.Object.ViewObject.Visibility = False
        self.Object.baseObject[0].ViewObject.Visibility = True
        FreeCADGui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        FreeCADGui.Control.closeDialog()
        self.Object.baseObject[0].ViewObject.Visibility = False
        self.Object.ViewObject.Visibility = True
        return False


class SMViewProviderFlat:
    "A View provider that places objects flat under base object"

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
        if hasattr(self.Object, "Sketch"):
            objs.append(self.Object.Sketch)
        return objs

    def getIcon(self):
        return os.path.join(iconPath, "SheetMetal_AddWall.svg")

    def setEdit(self, vobj, mode):
        if mode == 0:
            taskd = SMBendWallTaskPanel()
            taskd.obj = vobj.Object
            taskd.update()
            self.Object.ViewObject.Visibility = False
            self.Object.baseObject[0].ViewObject.Visibility = True
            FreeCADGui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        if mode == 0:
            FreeCADGui.Control.closeDialog()
            self.Object.baseObject[0].ViewObject.Visibility = False
            self.Object.ViewObject.Visibility = True
        return False


class AddWallCommandClass:
    """Add Wall command"""

    def GetResources(self):
        return {
            "Pixmap": os.path.join(
                iconPath, "SheetMetal_AddWall.svg"
            ),  # the name of a svg file available in the resources
            "MenuText": QtCore.QT_TRANSLATE_NOOP("SheetMetal", "Make Wall"),
            "Accel": "W",
            "ToolTip": QtCore.QT_TRANSLATE_NOOP(
                "SheetMetal",
                "Extends one or more face, connected by a bend on existing sheet metal.\n"
                "1. Select edges or thickness side faces to create bends with walls.\n"
                "2. Use Property editor to modify other parameters",
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
        doc.openTransaction("Bend")
        if activeBody is None or not smIsPartDesign(selobj):
            a = doc.addObject("Part::FeaturePython", "Bend")
            SMBendWall(a)
            SMViewProviderTree(a.ViewObject)
        else:
            # FreeCAD.Console.PrintLog("found active body: " + activeBody.Name)
            a = doc.addObject("PartDesign::FeaturePython", "Bend")
            SMBendWall(a)
            SMViewProviderFlat(a.ViewObject)
            activeBody.addObject(a)
        FreeCADGui.Selection.clearSelection()
        doc.recompute()
        doc.commitTransaction()
        return

    def IsActive(self):
        if (
            len(Gui.Selection.getSelection()) < 1
            or len(Gui.Selection.getSelectionEx()[0].SubElementNames) < 1
        ):
            return False
        selobj = Gui.Selection.getSelection()[0]
        if selobj.isDerivedFrom("Sketcher::SketchObject"):
            return False
        for selFace in Gui.Selection.getSelectionEx()[0].SubObjects:
            if type(selFace) == Part.Vertex:
                return False
        return True


Gui.addCommand("SMMakeWall", AddWallCommandClass())
