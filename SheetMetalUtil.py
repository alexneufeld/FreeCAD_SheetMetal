# -*- coding: utf-8 -*-
###############################################################################
#
#  SheetMetalUtil.py
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

from PySide import QtCore
from PySide import QtGui
import os

__dir__ = os.path.dirname(__file__)
iconPath = os.path.join(__dir__, "Resources", "icons")
smEpsilon = 0.0000001
# IMPORTANT: please remember to change the element map version in case of any
# changes in modeling logic
smElementMapVersion = "sm1."


def smWarnDialog(msg):
    diag = QtGui.QMessageBox(
        QtGui.QMessageBox.Warning, "Error in macro MessageBox", msg
    )
    diag.setWindowModality(QtCore.Qt.ApplicationModal)
    diag.exec_()


def smBelongToBody(item, body):
    if body is None:
        return False
    for obj in body.Group:
        if obj.Name == item.Name:
            return True
    return False


def smIsPartDesign(obj):
    return str(obj).find("<PartDesign::") == 0


def smIsOperationLegal(body, selobj):
    if smIsPartDesign(selobj) and not smBelongToBody(selobj, body):
        smWarnDialog(
            (
                "The selected geometry does not belong to the active Body.\n"
                "Please make the container of this item active by\n"
                "double clicking on it."
            )
        )
        return False
    return True


class selectionFilter(QtCore.QObject):
    """A selectionObserver that only emits signals when geometry that is
    part of baseFeature is selected. Allowable geometry can be restricted
    to only faces/edges/vertices by setting geomType to
    "Face", "Edge", or "Vertex"
    """

    selection = QtCore.Signal(str)

    def __init__(self, baseFeature, geomType="Any"):
        super().__init__()
        self.baseFeature = baseFeature
        if geomType not in ["Any", "Face", "Edge", "Vertex"]:
            raise ValueError(f"invalid geometry restrictor: {geomType}")
        self.geomType = geomType

    def addSelection(self, doc, obj, sub, pnt):
        print("p1")
        print(obj)
        print(self.baseFeature.Name)
        if obj == self.baseFeature.Name:
            print("p2")
            print(sub)
            if self.geomType == "Any" or sub.startswith(self.geomType):
                print("p3")
                self.selection.emit(sub)
