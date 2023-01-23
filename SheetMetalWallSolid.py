# -*- coding: utf-8 -*-
###############################################################################
#
#  SheetMetalWallSolid.py
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

import FreeCAD
import Part
import math
from SheetMetalUtil import smEpsilon


def smStrEdge(e):
    return (
        "["
        + str(e.valueAt(e.FirstParameter))
        + " , "
        + str(e.valueAt(e.LastParameter))
        + "]"
    )


def smMakeReliefFace(edge, dir, gap, reliefW, reliefD, reliefType, op=""):
    p1 = edge.valueAt(edge.FirstParameter + gap)
    p2 = edge.valueAt(edge.FirstParameter + gap + reliefW)
    if reliefType == "Round" and reliefD > reliefW:
        p3 = edge.valueAt(edge.FirstParameter + gap + reliefW) + dir.normalize() * (
            reliefD - reliefW / 2
        )
        p34 = (
            edge.valueAt(edge.FirstParameter + gap + reliefW / 2)
            + dir.normalize() * reliefD
        )
        p4 = edge.valueAt(edge.FirstParameter + gap) + dir.normalize() * (
            reliefD - reliefW / 2
        )
        e1 = Part.makeLine(p1, p2)
        e2 = Part.makeLine(p2, p3)
        e3 = Part.Arc(p3, p34, p4).toShape()
        e4 = Part.makeLine(p4, p1)
    else:
        p3 = (
            edge.valueAt(edge.FirstParameter + gap + reliefW)
            + dir.normalize() * reliefD
        )
        p4 = edge.valueAt(edge.FirstParameter + gap) + dir.normalize() * reliefD
        e1 = Part.makeLine(p1, p2)
        e2 = Part.makeLine(p2, p3)
        e3 = Part.makeLine(p3, p4)
        e4 = Part.makeLine(p4, p1)

    w = Part.Wire([e1, e2, e3, e4])
    face = Part.Face(w)
    if hasattr(face, "mapShapes"):
        face.mapShapes([(edge, face)], [], op)
    return face


def smMakeFace(edge, dir, extLen, gap1=0.0, gap2=0.0, angle1=0.0, angle2=0.0, op=""):
    len1 = extLen * math.tan(math.radians(angle1))
    len2 = extLen * math.tan(math.radians(angle2))

    p1 = edge.valueAt(edge.LastParameter - gap2)
    p2 = edge.valueAt(edge.FirstParameter + gap1)
    p3 = edge.valueAt(edge.FirstParameter + gap1 + len1) + dir.normalize() * extLen
    p4 = edge.valueAt(edge.LastParameter - gap2 - len2) + dir.normalize() * extLen

    e2 = Part.makeLine(p2, p3)
    e4 = Part.makeLine(p4, p1)
    section = e4.section(e2)

    if section.Vertexes:
        p5 = section.Vertexes[0].Point
        w = Part.makePolygon([p1, p2, p5, p1])
    else:
        w = Part.makePolygon([p1, p2, p3, p4, p1])
    face = Part.Face(w)
    if hasattr(face, "mapShapes"):
        face.mapShapes([(edge, face)], None, op)
    return face


def smFace(selItem, obj):
    # find face, if Edge Selected
    if type(selItem) == Part.Edge:
        Facelist = obj.ancestorsOfType(selItem, Part.Face)
        if Facelist[0].Area < Facelist[1].Area:
            selFace = Facelist[0]
        else:
            selFace = Facelist[1]
    elif type(selItem) == Part.Face:
        selFace = selItem
    return selFace


def smModifiedFace(Face, obj):
    # find face Modified During loop
    for face in obj.Faces:
        face_common = face.common(Face)
        if face_common.Faces:
            if face.Area == face_common.Faces[0].Area:
                break
    return face


def smGetEdge(Face, obj):
    # find Edges that overlap
    for edge in obj.Edges:
        face_common = edge.common(Face)
        if face_common.Edges:
            break
    return edge


def LineAngle(edge1, edge2):
    # find angle between two lines
    if edge1.Orientation == edge2.Orientation:
        lineDir = edge1.valueAt(edge1.FirstParameter) - edge1.valueAt(
            edge1.LastParameter
        )
        edgeDir = edge2.valueAt(edge2.FirstParameter) - edge2.valueAt(
            edge2.LastParameter
        )
    else:
        lineDir = edge1.valueAt(edge1.FirstParameter) - edge1.valueAt(
            edge1.LastParameter
        )
        edgeDir = edge2.valueAt(edge2.LastParameter) - edge2.valueAt(
            edge2.FirstParameter
        )
    angle1 = edgeDir.getAngle(lineDir)
    angle = math.degrees(angle1)
    return angle


def smRestrict(var, fromVal, toVal):
    if var < fromVal:
        return fromVal
    if var > toVal:
        return toVal
    return var


def smGetFace(Faces, obj):
    # find face Name Modified obj
    faceList = []
    for Face in Faces:
        for i, face in enumerate(obj.Faces):
            face_common = face.common(Face)
            if face_common.Faces:
                faceList.append("Face" + str(i + 1))
    # print(faceList)
    return faceList


def LineExtend(edge, distance1, distance2):
    # Extend a ine by given distances
    return edge.Curve.toShape(
        edge.FirstParameter - distance1, edge.LastParameter + distance2
    )


def getParallel(edge1, edge2):
    # Get intersection between two lines
    e1 = edge1.Curve.toShape()
    # Part.show(e1,'e1')
    e2 = edge2.Curve.toShape()
    # Part.show(e2,'e2')
    section = e1.section(e2)
    if section.Vertexes:
        # Part.show(section,'section')
        return False
    else:
        return True


def getCornerPoint(edge1, edge2):
    # Get intersection between two lines
    # Part.show(edge1,'edge1')
    # Part.show(edge2,'edge21')
    e1 = edge1.Curve.toShape()
    # Part.show(e1,'e1')
    e2 = edge2.Curve.toShape()
    # Part.show(e2,'e2')
    section = e1.section(e2)
    if section.Vertexes:
        # Part.show(section,'section')
        cornerPoint = section.Vertexes[0].Point
    return cornerPoint


def getGap(line1, line2, maxExtendGap, mingap):
    # To find gap between two edges
    gaps = 0.0
    extgap = 0.0
    section = line1.section(line2)
    if section.Vertexes:
        cornerPoint = section.Vertexes[0].Point
        size1 = abs((cornerPoint - line2.Vertexes[0].Point).Length)
        size2 = abs((cornerPoint - line2.Vertexes[1].Point).Length)
        if size1 < size2:
            gaps = size1
        else:
            gaps = size2
        gaps = gaps + mingap
        # print(gaps)
    else:
        cornerPoint = getCornerPoint(line1, line2)
        line3 = LineExtend(line1, maxExtendGap, maxExtendGap)
        # Part.show(line1,'line1')
        line4 = LineExtend(line2, maxExtendGap, maxExtendGap)
        # Part.show(line2,'line2')
        section = line3.section(line4)
        if section.Vertexes:
            # cornerPoint = section.Vertexes[0].Point
            # p1 = Part.Vertex(cornerPoint)
            _ = line1.section(line4)
            size1 = abs((cornerPoint - line2.Vertexes[0].Point).Length)
            size2 = abs((cornerPoint - line2.Vertexes[1].Point).Length)
            #      dist = cornerPoint.distanceToLine(line2.Curve.Location, line2.Curve.Direction)
            # print(["gap",size1, size2, dist])
            #      if section1.Vertexes :
            #        extgap = 0.0
            if size1 < size2:
                extgap = size1
            else:
                extgap = size2
            #      if dist < smEpsilon :
            #        gaps = extgap
            #        extgap = 0.0
            if extgap > mingap:
                extgap = extgap - mingap
            # print(extgap)
    return gaps, extgap, cornerPoint


def getSketchDetails(Sketch, sketchflip, sketchinvert, radius, thk):
    # Convert Sketch lines to length. Angles between line
    LengthList, bendAList = ([], [])
    sketch_normal = Sketch.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    e0 = Sketch.Placement.Rotation.multVec(FreeCAD.Vector(1, 0, 0))
    WireList = Sketch.Shape.Wires[0]

    # Create filleted wire at centre of thickness
    wire_extr = WireList.extrude(sketch_normal * -50)
    # Part.show(wire_extr,"wire_extr")
    wire_extr_mir = WireList.extrude(sketch_normal * 50)
    # Part.show(wire_extr_mir,"wire_extr_mir")
    wire_extr = wire_extr.makeOffsetShape(thk / 2.0, 0.0, fill=False, join=2)
    # Part.show(wire_extr,"wire_extr")
    wire_extr_mir = wire_extr_mir.makeOffsetShape(-thk / 2.0, 0.0, fill=False, join=2)
    # Part.show(wire_extr_mir,"wire_extr_mir")
    if len(WireList.Edges) > 1:
        filleted_extr = wire_extr.makeFillet((radius + thk / 2.0), wire_extr.Edges)
        # Part.show(filleted_extr,"filleted_extr")
        filleted_extr_mir = wire_extr_mir.makeFillet(
            (radius + thk / 2.0), wire_extr_mir.Edges
        )
        # Part.show(filleted_extr_mir,"filleted_extr_mir")
    else:
        filleted_extr = wire_extr
        filleted_extr_mir = wire_extr_mir
    # Part.show(filleted_extr,"filleted_extr")
    sec_wirelist = filleted_extr_mir.section(filleted_extr)
    # Part.show(sec_wirelist,"sec_wirelist")

    for edge in sec_wirelist.Edges:
        if isinstance(edge.Curve, Part.Line):
            LengthList.append(edge.Length)

    for i in range(len(WireList.Vertexes) - 1):
        p1 = WireList.Vertexes[i].Point
        p2 = WireList.Vertexes[i + 1].Point
        e1 = p2 - p1
        #   LengthList.append(e1.Length)
        normal = e0.cross(e1)
        coeff = sketch_normal.dot(normal)
        if coeff >= 0:
            sign = 1
        else:
            sign = -1
        angle_rad = e0.getAngle(e1)
        if sketchflip:
            angle = sign * math.degrees(angle_rad) * -1
        else:
            angle = sign * math.degrees(angle_rad)
        bendAList.append(angle)
        e0 = e1
    if sketchinvert:
        LengthList.reverse()
        bendAList.reverse()
    # print(LengthList, bendAList)
    return LengthList, bendAList


def sheet_thk(MainObject, selFaceName):
    selItem = MainObject.getElement(selFaceName)
    selFace = smFace(selItem, MainObject)
    # find the narrow edge
    thk = 999999.0
    for edge in selFace.Edges:
        if abs(edge.Length) < thk:
            thk = abs(edge.Length)
    return thk


def smEdge(selFaceName, MainObject):
    # find Edge, if Face Selected
    selItem = MainObject.getElement(selFaceName)
    if type(selItem) == Part.Face:
        # find the narrow edge
        thk = 999999.0
        for edge in selItem.Edges:
            if abs(edge.Length) < thk:
                thk = abs(edge.Length)
                thkEdge = edge

        # find a length edge  =  revolve axis direction
        p0 = thkEdge.valueAt(thkEdge.FirstParameter)
        for lenEdge in selItem.Edges:
            p1 = lenEdge.valueAt(lenEdge.FirstParameter)
            p2 = lenEdge.valueAt(lenEdge.LastParameter)
            if lenEdge.isSame(thkEdge):
                continue
            if (p1 - p0).Length < smEpsilon:
                revAxisV = p2 - p1
                break
            if (p2 - p0).Length < smEpsilon:
                revAxisV = p1 - p2
                break
        seledge = lenEdge
        selFace = selItem
    elif type(selItem) == Part.Edge:
        thk = sheet_thk(MainObject, selFaceName)
        seledge = selItem
        selFace = smFace(selItem, MainObject)
        p1 = seledge.valueAt(seledge.FirstParameter)
        p2 = seledge.valueAt(seledge.LastParameter)
        revAxisV = p2 - p1
    return seledge, selFace, thk, revAxisV


def getBendetail(selFaceNames, MainObject, bendR, bendA, flipped, offset, gap1, gap2):
    mainlist = []
    edgelist = []
    nogap_edgelist = []
    for selFaceName in selFaceNames:
        lenEdge, selFace, thk, revAxisV = smEdge(selFaceName, MainObject)

        # find the large face connected with selected face
        list2 = MainObject.ancestorsOfType(lenEdge, Part.Face)
        for Cface in list2:
            if not (Cface.isSame(selFace)):
                break

        # main Length Edge
        revAxisV.normalize()
        thkDir = Cface.normalAt(0, 0) * -1
        FaceDir = selFace.normalAt(0, 0)

        # make sure the direction verctor is correct in respect to the normal
        if (thkDir.cross(revAxisV).normalize() - FaceDir).Length < smEpsilon:
            revAxisV = revAxisV * -1

        # restrict angle
        if bendA < 0:
            bendA = -bendA
            flipped = not flipped

        if not (flipped):
            revAxisP = lenEdge.valueAt(lenEdge.FirstParameter) + thkDir * (bendR + thk)
            revAxisV = revAxisV * -1
        else:
            revAxisP = lenEdge.valueAt(lenEdge.FirstParameter) + thkDir * -bendR
        # Part.show(lenEdge,'lenEdge')
        mainlist.append(
            [
                Cface,
                selFace,
                thk,
                lenEdge,
                revAxisP,
                revAxisV,
                thkDir,
                FaceDir,
                bendA,
                flipped,
            ]
        )
        if offset < 0.0:
            dist = lenEdge.valueAt(lenEdge.FirstParameter).distanceToPlane(
                FreeCAD.Vector(0, 0, 0), FaceDir
            )
            # print(dist)
            slice_wire = Cface.slice(FaceDir, dist + offset)
            # print(slice_wire)
            trimLenEdge = slice_wire[0].Edges[0]
        else:
            # Produce Offset Edge
            trimLenEdge = lenEdge.copy()
            trimLenEdge.translate(selFace.normalAt(0, 0) * offset)
        # Part.show(trimLenEdge,'trimLenEdge1')
        nogap_edgelist.append(trimLenEdge)
        trimLenEdge = LineExtend(trimLenEdge, -gap1, -gap2)
        # Part.show(trimLenEdge,'trimLenEdge2')
        edgelist.append(trimLenEdge)
    # print(mainlist)
    trimedgelist = InsideEdge(edgelist)
    nogaptrimedgelist = InsideEdge(nogap_edgelist)
    return mainlist, trimedgelist, nogaptrimedgelist


def InsideEdge(edgelist):
    import BOPTools.JoinFeatures

    newedgelist = []
    for i, e in enumerate(edgelist):
        for j, ed in enumerate(edgelist):
            if i != j:
                section = e.section(ed)
                if section.Vertexes:
                    edgeShape = BOPTools.JoinAPI.cutout_legacy(e, ed, tolerance=0.0)
                    e = edgeShape
        # Part.show(e,"newedge")
        newedgelist.append(e)
    return newedgelist


def smMiter(
    mainlist,
    trimedgelist,
    bendR=1.0,
    miterA1=0.0,
    miterA2=0.0,
    extLen=10.0,
    gap1=0.0,
    gap2=0.0,
    offset=0.0,
    reliefD=1.0,
    automiter=True,
    extend1=0.0,
    extend2=0.0,
    mingap=0.1,
    maxExtendGap=5.0,
):
    if not (automiter):
        miterA1List = [miterA1 for n in range(len(mainlist))]
        miterA2List = [miterA2 for n in range(len(mainlist))]
        gap1List = [gap1 for n in range(len(mainlist))]
        gap2List = [gap2 for n in range(len(mainlist))]
        extgap1List = [extend1 for n in range(len(mainlist))]
        extgap2List = [extend2 for n in range(len(mainlist))]
    else:
        miterA1List = [0.0 for n in range(len(mainlist))]
        miterA2List = [0.0 for n in range(len(mainlist))]
        gap1List = [gap1 for n in range(len(mainlist))]
        gap2List = [gap2 for n in range(len(mainlist))]
        extgap1List = [extend1 for n in range(len(mainlist))]
        extgap2List = [extend2 for n in range(len(mainlist))]

        facelist, tranfacelist = ([], [])
        extfacelist, exttranfacelist = ([], [])
        lenedgelist, tranedgelist = ([], [])
        for i, sublist in enumerate(mainlist):
            # find the narrow edge
            (
                Cface,
                selFace,
                thk,
                MlenEdge,
                revAxisP,
                revAxisV,
                thkDir,
                FaceDir,
                bendA,
                flipped,
            ) = sublist

            # Produce Offset Edge
            lenEdge = trimedgelist[i].copy()
            revAxisP = revAxisP + FaceDir * offset

            # narrow the wall, if we have gaps
            BendFace = smMakeFace(
                lenEdge, FaceDir, extLen, gap1 - extend1, gap2 - extend2, op="SMB"
            )
            if BendFace.normalAt(0, 0) != thkDir:
                BendFace.reverse()
            transBendFace = BendFace.copy()
            BendFace.rotate(revAxisP, revAxisV, bendA)
            # Part.show(BendFace,'BendFace')
            facelist.append(BendFace)
            transBendFace.translate(thkDir * thk)
            transBendFace.rotate(revAxisP, revAxisV, bendA)
            tranfacelist.append(transBendFace)

            # narrow the wall, if we have gaps
            BendFace = smMakeFace(
                lenEdge,
                FaceDir,
                extLen,
                gap1 - extend1 - maxExtendGap,
                gap2 - extend2 - maxExtendGap,
                op="SMB",
            )
            if BendFace.normalAt(0, 0) != thkDir:
                BendFace.reverse()
            transBendFace = BendFace.copy()
            BendFace.rotate(revAxisP, revAxisV, bendA)
            # Part.show(BendFace,'BendFace')
            extfacelist.append(BendFace)
            transBendFace.translate(thkDir * thk)
            transBendFace.rotate(revAxisP, revAxisV, bendA)
            exttranfacelist.append(transBendFace)

            #      edge_len = lenEdge.copy()
            edge_len = LineExtend(lenEdge, (-gap1 + extend1), (-gap2 + extend2))
            edge_len.rotate(revAxisP, revAxisV, bendA)
            lenedgelist.append(edge_len)
            # Part.show(edge_len,'edge_len')

            #      edge_len = lenEdge.copy()
            edge_len = LineExtend(lenEdge, (-gap1 + extend1), (-gap2 + extend2))
            edge_len.translate(thkDir * thk)
            edge_len.rotate(revAxisP, revAxisV, bendA)
            tranedgelist.append(edge_len)
            # Part.show(edge_len,'edge_len')

        # check faces intersect each other
        for i in range(len(facelist)):
            for j in range(len(lenedgelist)):
                if (
                    i != j
                    and facelist[i].isCoplanar(facelist[j])
                    and not (getParallel(lenedgelist[i], lenedgelist[j]))
                ):
                    # Part.show(lenedgelist[i],'edge_len1')
                    # Part.show(lenedgelist[j],'edge_len2')
                    gaps1, extgap1, cornerPoint1 = getGap(
                        lenedgelist[i], lenedgelist[j], maxExtendGap, mingap
                    )
                    gaps2, extgap2, cornerPoint2 = getGap(
                        tranedgelist[i], tranedgelist[j], maxExtendGap, mingap
                    )
                    # print([gaps1,gaps2, extgap1, extgap2])
                    gaps = max(gaps1, gaps2)
                    extgap = min(extgap1, extgap2)
                    p1 = lenedgelist[j].valueAt(lenedgelist[j].FirstParameter)
                    p2 = lenedgelist[j].valueAt(lenedgelist[j].LastParameter)
                    Angle = LineAngle(lenedgelist[i], lenedgelist[j])
                    # print(Angle)
                    if gaps > 0.0:
                        #            walledge_common = lenedgelist[j].section(lenedgelist[i])
                        #            vp1 = walledge_common.Vertexes[0].Point
                        dist1 = (p1 - cornerPoint1).Length
                        dist2 = (p2 - cornerPoint1).Length
                        if abs(dist1) < abs(dist2):
                            miterA1List[j] = Angle / 2.0
                            if gaps > 0.0:
                                gap1List[j] = gaps
                            else:
                                gap1List[j] = 0.0
                        elif abs(dist2) < abs(dist1):
                            miterA2List[j] = Angle / 2.0
                            if gaps > 0.0:
                                gap2List[j] = gaps
                            else:
                                gap2List[j] = 0.0
                    elif extgap != 0.0 and (extgap + mingap) < maxExtendGap:
                        wallface_common = facelist[j].common(facelist[i])
                        dist1 = (p1 - cornerPoint1).Length
                        dist2 = (p2 - cornerPoint1).Length
                        if abs(dist1) < abs(dist2):
                            if wallface_common.Faces:
                                miterA1List[j] = Angle / 2.0
                            else:
                                miterA1List[j] = -Angle / 2.0
                            if extgap > 0.0:
                                extgap1List[j] = extgap
                            else:
                                extgap1List[j] = 0.0
                        elif abs(dist2) < abs(dist1):
                            if wallface_common.Faces:
                                miterA2List[j] = Angle / 2.0
                            else:
                                miterA2List[j] = -Angle / 2.0
                            if extgap > 0.0:
                                extgap2List[j] = extgap
                            else:
                                extgap2List[j] = 0.0
                elif i != j and not (getParallel(lenedgelist[i], lenedgelist[j])):
                    # Part.show(lenedgelist[i],'edge_len1')
                    # Part.show(lenedgelist[j],'edge_len2')
                    # Part.show(tranedgelist[i],'edge_len1')
                    # Part.show(tranedgelist[j],'edge_len2')
                    gaps1, extgap1, cornerPoint1 = getGap(
                        lenedgelist[i], lenedgelist[j], maxExtendGap, mingap
                    )
                    gaps2, extgap2, cornerPoint2 = getGap(
                        tranedgelist[i], tranedgelist[j], maxExtendGap, mingap
                    )
                    # print([gaps1, gaps2, extgap1, extgap2])
                    gaps = max(gaps1, gaps2)
                    extgap = min(extgap1, extgap2)
                    p1 = lenedgelist[j].valueAt(lenedgelist[j].FirstParameter)
                    p2 = lenedgelist[j].valueAt(lenedgelist[j].LastParameter)
                    if gaps > 0.0:
                        wallface_common = facelist[j].section(facelist[i])
                        # Part.show(facelist[j],'facelist')
                        # Part.show(facelist[i],'facelist')
                        wallface_common1 = tranfacelist[j].section(tranfacelist[i])
                        # Part.show(tranfacelist[j],'tranfacelist')
                        # Part.show(tranfacelist[i],'tranfacelist')
                        # Part.show(wallface_common,'wallface_common')
                        if wallface_common.Edges:
                            vp1 = wallface_common.Vertexes[0].Point
                            vp2 = wallface_common.Vertexes[1].Point
                        elif wallface_common1.Edges:
                            vp1 = wallface_common1.Vertexes[0].Point
                            vp2 = wallface_common1.Vertexes[1].Point
                        dist1 = (p1 - vp1).Length
                        dist2 = (p2 - vp1).Length
                        if abs(dist1) < abs(dist2):
                            edgedir = (p1 - p2).normalize()
                            dist3 = (cornerPoint1 - vp1).Length
                            dist4 = (cornerPoint1 - vp2).Length
                            if dist4 < dist3:
                                lineDir = (vp2 - vp1).normalize()
                            else:
                                lineDir = (vp1 - vp2).normalize()
                            angle1 = edgedir.getAngle(lineDir)
                            Angle2 = math.degrees(angle1)
                            Angle = 90 - Angle2
                            # print([Angle, Angle2, 'ext'])
                            miterA1List[j] = Angle
                            if gaps > 0.0:
                                gap1List[j] = gaps
                            else:
                                gap1List[j] = 0.0
                        elif abs(dist2) < abs(dist1):
                            edgedir = (p2 - p1).normalize()
                            dist3 = (cornerPoint1 - vp1).Length
                            dist4 = (cornerPoint1 - vp2).Length
                            if dist4 < dist3:
                                lineDir = (vp2 - vp1).normalize()
                            else:
                                lineDir = (vp1 - vp2).normalize()
                            angle1 = edgedir.getAngle(lineDir)
                            Angle2 = math.degrees(angle1)
                            Angle = 90 - Angle2
                            # print([Angle, Angle2, 'ext'])
                            miterA2List[j] = Angle
                            if gaps > 0.0:
                                gap2List[j] = gaps
                            else:
                                gap2List[j] = 0.0
                    elif extgap != 0.0 and (extgap + mingap) < maxExtendGap:
                        wallface_common = extfacelist[j].section(extfacelist[i])
                        # Part.show(extfacelist[j],'extfacelist')
                        # Part.show(extfacelist[i],'extfacelist')
                        wallface_common1 = exttranfacelist[j].section(
                            exttranfacelist[i]
                        )
                        # Part.show(exttranfacelist[j],'exttranfacelist')
                        # Part.show(exttranfacelist[i],'exttranfacelist')
                        # Part.show(wallface_common,'wallface_common')
                        if wallface_common.Edges:
                            vp1 = wallface_common.Vertexes[0].Point
                            vp2 = wallface_common.Vertexes[1].Point
                        elif wallface_common1.Edges:
                            vp1 = wallface_common1.Vertexes[0].Point
                            vp2 = wallface_common1.Vertexes[1].Point
                        dist1 = (p1 - vp1).Length
                        dist2 = (p2 - vp1).Length
                        if abs(dist1) < abs(dist2):
                            edgedir = (p1 - p2).normalize()
                            dist3 = (cornerPoint1 - vp1).Length
                            dist4 = (cornerPoint1 - vp2).Length
                            if dist4 < dist3:
                                lineDir = (vp2 - vp1).normalize()
                            else:
                                lineDir = (vp1 - vp2).normalize()
                            angle1 = edgedir.getAngle(lineDir)
                            Angle2 = math.degrees(angle1)
                            Angle = 90 - Angle2
                            # print([Angle, Angle2, 'ext'])
                            miterA1List[j] = Angle
                            if extgap > 0.0:
                                extgap1List[j] = extgap
                            else:
                                extgap1List[j] = 0.0
                        elif abs(dist2) < abs(dist1):
                            edgedir = (p2 - p1).normalize()
                            dist3 = (cornerPoint1 - vp1).Length
                            dist4 = (cornerPoint1 - vp2).Length
                            if dist4 < dist3:
                                lineDir = (vp2 - vp1).normalize()
                            else:
                                lineDir = (vp1 - vp2).normalize()
                            angle1 = edgedir.getAngle(lineDir)
                            Angle2 = math.degrees(angle1)
                            Angle = 90 - Angle2
                            # print([Angle, Angle2, 'ext'])
                            miterA2List[j] = Angle
                            if extgap > 0.0:
                                extgap2List[j] = extgap
                            else:
                                extgap2List[j] = 0.0

    # print(miterA1List, miterA2List, gap1List, gap2List, extgap1List, extgap2List)
    return miterA1List, miterA2List, gap1List, gap2List, extgap1List, extgap2List


def smBend(
    thk,
    bendR=1.0,
    bendA=90.0,
    miterA1=0.0,
    miterA2=0.0,
    BendType="Material Outside",
    flipped=False,
    unfold=False,
    offset=0.0,
    extLen=10.0,
    gap1=0.0,
    gap2=0.0,
    reliefType="Rectangle",
    reliefW=0.8,
    reliefD=1.0,
    minReliefgap=1.0,
    extend1=0.0,
    extend2=0.0,
    kfactor=0.45,
    ReliefFactor=0.7,
    UseReliefFactor=False,
    selFaceNames="",
    MainObject=None,
    maxExtendGap=5.0,
    mingap=0.1,
    automiter=True,
    sketch=None,
    extendType="Simple",
):
    print("running smbend from SheetMetalCmd.py")
    # if sketch is as wall
    sketches = False
    if sketch:
        if sketch.Shape.Wires[0].isClosed():
            sketches = True
        else:
            pass

    # Add Bend Type details
    if BendType == "Material Outside":
        offset = 0.0
        inside = False
    elif BendType == "Material Inside":
        offset = -(thk + bendR)
        inside = True
    elif BendType == "Thickness Outside":
        offset = -bendR
        inside = True
    elif BendType == "Offset":
        if offset < 0.0:
            inside = True
        else:
            inside = False

    if not (sketches):
        mainlist, trimedgelist, nogaptrimedgelist = getBendetail(
            selFaceNames, MainObject, bendR, bendA, flipped, offset, gap1, gap2
        )
        (
            miterA1List,
            miterA2List,
            gap1List,
            gap2List,
            extend1List,
            extend2List,
        ) = smMiter(
            mainlist,
            trimedgelist,
            bendR=bendR,
            miterA1=miterA1,
            miterA2=miterA2,
            extLen=extLen,  # gap1 = gap1, gap2 = gap2,
            offset=offset,
            automiter=automiter,
            extend1=extend1,
            extend2=extend2,
            mingap=mingap,
            maxExtendGap=maxExtendGap,
        )

        # print(miterA1List, miterA2List, gap1List, gap2List, extend1List, extend2List)
    else:
        (
            miterA1List,
            miterA2List,
            gap1List,
            gap2List,
            extend1List,
            extend2List,
            reliefDList,
        ) = ([0.0], [0.0], [gap1], [gap2], [extend1], [extend2], [reliefD])
    agap1, agap2 = gap1, gap2
    # print([agap1,agap1])

    #  mainlist = getBendetail(selFaceNames, MainObject, bendR, bendA, flipped)
    thk_faceList = []
    resultSolid = MainObject
    for i, sublist in enumerate(mainlist):
        # find the narrow edge
        (
            Cface,
            selFace,
            thk,
            AlenEdge,
            revAxisP,
            revAxisV,
            thkDir,
            FaceDir,
            bendA,
            flipped,
        ) = sublist
        gap1, gap2 = (gap1List[i], gap2List[i])
        # print([gap1,gap2])
        extend1, extend2 = (extend1List[i], extend2List[i])
        # Part.show(lenEdge,'lenEdge1')
        selFace = smModifiedFace(selFace, resultSolid)
        # Part.show(selFace,'selFace')
        Cface = smModifiedFace(Cface, resultSolid)
        # Part.show(Cface,'Cface')
        # main Length Edge
        MlenEdge = smGetEdge(AlenEdge, resultSolid)
        # Part.show(MlenEdge,'MlenEdge')
        lenEdge = trimedgelist[i]
        noGap_lenEdge = nogaptrimedgelist[i]
        leng = lenEdge.Length
        # Part.show(lenEdge,'lenEdge')

        # Add as offset to set any distance
        if UseReliefFactor:
            reliefW = thk * ReliefFactor
            reliefD = thk * ReliefFactor

        # if sketch is as wall
        sketches = False
        if sketch:
            if sketch.Shape.Wires[0].isClosed():
                sketches = True
            else:
                pass

        if sketches:
            sketch_face = Part.makeFace(sketch.Shape.Wires, "Part::FaceMakerBullseye")
            sketch_face.translate(thkDir * -thk)
            if inside:
                sketch_face.translate(FaceDir * offset)
            sketch_Shape = lenEdge.common(sketch_face)
            sketch_Edge = sketch_Shape.Edges[0]
            gap1 = (
                lenEdge.valueAt(lenEdge.FirstParameter)
                - sketch_Edge.valueAt(sketch_Edge.FirstParameter)
            ).Length
            gap2 = (
                lenEdge.valueAt(lenEdge.LastParameter)
                - sketch_Edge.valueAt(sketch_Edge.LastParameter)
            ).Length

        # CutSolids list for collecting Solids
        CutSolids = []
        # remove relief if needed
        if reliefD > 0.0 and reliefW > 0.0:
            if agap1 > minReliefgap:
                reliefFace1 = smMakeReliefFace(
                    lenEdge,
                    FaceDir * -1,
                    gap1 - reliefW,
                    reliefW,
                    reliefD,
                    reliefType,
                    op="SMF",
                )
                reliefSolid1 = reliefFace1.extrude(thkDir * thk)
                # Part.show(reliefSolid1, "reliefSolid1")
                CutSolids.append(reliefSolid1)
                if inside:
                    reliefFace1 = smMakeReliefFace(
                        lenEdge,
                        FaceDir * -1,
                        gap1 - reliefW,
                        reliefW,
                        offset,
                        reliefType,
                        op="SMF",
                    )
                    reliefSolid1 = reliefFace1.extrude(thkDir * thk)
                    # Part.show(reliefSolid1, "reliefSolid1")
                    CutSolids.append(reliefSolid1)
            if agap2 > minReliefgap:
                reliefFace2 = smMakeReliefFace(
                    lenEdge,
                    FaceDir * -1,
                    lenEdge.Length - gap2,
                    reliefW,
                    reliefD,
                    reliefType,
                    op="SMFF",
                )
                reliefSolid2 = reliefFace2.extrude(thkDir * thk)
                # Part.show(reliefSolid2, "reliefSolid2")
                CutSolids.append(reliefSolid2)
                if inside:
                    reliefFace2 = smMakeReliefFace(
                        lenEdge,
                        FaceDir * -1,
                        lenEdge.Length - gap2,
                        reliefW,
                        offset,
                        reliefType,
                        op="SMFF",
                    )
                    reliefSolid2 = reliefFace2.extrude(thkDir * thk)
                    # Part.show(reliefSolid2,"reliefSolid2")
                    CutSolids.append(reliefSolid2)

        # remove bend face if present
        if inside:
            if (
                MlenEdge.Vertexes[0].Point - MlenEdge.valueAt(MlenEdge.FirstParameter)
            ).Length < smEpsilon:
                vertex0 = MlenEdge.Vertexes[0]
                vertex1 = MlenEdge.Vertexes[1]
            else:
                vertex1 = MlenEdge.Vertexes[0]
                vertex0 = MlenEdge.Vertexes[1]
            Noffset_1 = abs(
                (
                    MlenEdge.valueAt(MlenEdge.FirstParameter)
                    - noGap_lenEdge.valueAt(noGap_lenEdge.FirstParameter)
                ).Length
            )
            Noffset_2 = abs(
                (
                    MlenEdge.valueAt(MlenEdge.FirstParameter)
                    - noGap_lenEdge.valueAt(noGap_lenEdge.LastParameter)
                ).Length
            )
            Noffset1 = min(Noffset_1, Noffset_2)
            Noffset_1 = abs(
                (
                    MlenEdge.valueAt(MlenEdge.LastParameter)
                    - noGap_lenEdge.valueAt(noGap_lenEdge.FirstParameter)
                ).Length
            )
            Noffset_2 = abs(
                (
                    MlenEdge.valueAt(MlenEdge.LastParameter)
                    - noGap_lenEdge.valueAt(noGap_lenEdge.LastParameter)
                ).Length
            )
            Noffset2 = min(Noffset_1, Noffset_2)
            # print([Noffset1, Noffset1])
            if agap1 <= minReliefgap:
                Edgelist = selFace.ancestorsOfType(vertex0, Part.Edge)
                for ed in Edgelist:
                    if not (MlenEdge.isSame(ed)):
                        list1 = resultSolid.ancestorsOfType(ed, Part.Face)
                        for Rface in list1:
                            # print(type(Rface.Surface))
                            if not (selFace.isSame(Rface)):
                                for edge in Rface.Edges:
                                    # print(type(edge.Curve))
                                    if issubclass(
                                        type(edge.Curve),
                                        (Part.Circle or Part.BSplineSurface),
                                    ):
                                        RfaceE = Rface.makeOffsetShape(
                                            -Noffset1, 0.0, fill=True
                                        )
                                        # Part.show(RfaceE,"RfaceSolid1")
                                        CutSolids.append(RfaceE)
                                        break
            if agap2 <= minReliefgap:
                Edgelist = selFace.ancestorsOfType(vertex1, Part.Edge)
                for ed in Edgelist:
                    if not (MlenEdge.isSame(ed)):
                        list1 = resultSolid.ancestorsOfType(ed, Part.Face)
                        for Rface in list1:
                            # print(type(Rface.Surface))
                            if not (selFace.isSame(Rface)):
                                for edge in Rface.Edges:
                                    # print(type(edge.Curve))
                                    if issubclass(
                                        type(edge.Curve),
                                        (Part.Circle or Part.BSplineSurface),
                                    ):
                                        RfaceE = Rface.makeOffsetShape(
                                            -Noffset2, 0.0, fill=True
                                        )
                                        # Part.show(RfaceE,"RfaceSolid2")
                                        CutSolids.append(RfaceE)
                                        break

            # remove offset solid from sheetmetal, if inside offset
            Ref_lenEdge = lenEdge.copy().translate(FaceDir * -offset)
            cutgap_1 = (
                AlenEdge.valueAt(AlenEdge.FirstParameter)
                - Ref_lenEdge.valueAt(Ref_lenEdge.FirstParameter)
            ).Length
            cutgap_2 = (
                AlenEdge.valueAt(AlenEdge.FirstParameter)
                - Ref_lenEdge.valueAt(Ref_lenEdge.LastParameter)
            ).Length
            cutgap1 = min(cutgap_1, cutgap_2)
            dist = AlenEdge.valueAt(AlenEdge.FirstParameter).distanceToLine(
                Ref_lenEdge.Curve.Location, Ref_lenEdge.Curve.Direction
            )
            # print(dist)
            if dist < smEpsilon:
                cutgap1 = cutgap1 * -1.0
            cutgap_1 = (
                AlenEdge.valueAt(AlenEdge.LastParameter)
                - Ref_lenEdge.valueAt(Ref_lenEdge.FirstParameter)
            ).Length
            cutgap_2 = (
                AlenEdge.valueAt(AlenEdge.LastParameter)
                - Ref_lenEdge.valueAt(Ref_lenEdge.LastParameter)
            ).Length
            cutgap2 = min(cutgap_1, cutgap_2)
            dist = AlenEdge.valueAt(AlenEdge.LastParameter).distanceToLine(
                Ref_lenEdge.Curve.Location, Ref_lenEdge.Curve.Direction
            )
            # print(dist)
            if dist < smEpsilon:
                cutgap2 = cutgap2 * -1.0
            # print([cutgap1, cutgap2])
            CutFace = smMakeFace(AlenEdge, thkDir, thk, cutgap1, cutgap2, op="SMC")
            # Part.show(CutFace2,"CutFace2")
            CutSolid = CutFace.extrude(FaceDir * offset)
            # Part.show(CutSolid,"CutSolid")
            CfaceSolid = Cface.extrude(thkDir * thk)
            CutSolid = CutSolid.common(CfaceSolid)
            CutSolids.append(CutSolid)

        # Produce Main Solid for Inside Bends
        if CutSolids:
            if len(CutSolids) == 1:
                resultSolid = resultSolid.cut(CutSolids[0])
            else:
                Solid = CutSolids[0].multiFuse(CutSolids[1:])
                Solid.removeSplitter()
                # Part.show(Solid)
                resultSolid = resultSolid.cut(Solid)

        # Produce Offset Solid
        if offset > 0.0:
            # create wall
            offset_face = smMakeFace(lenEdge, FaceDir, -offset, op="SMO")
            OffsetSolid = offset_face.extrude(thkDir * thk)
            resultSolid = resultSolid.fuse(OffsetSolid)

        # Adjust revolving center to new point
        if not (flipped):
            revAxisP = lenEdge.valueAt(lenEdge.FirstParameter) + thkDir * (bendR + thk)
        else:
            revAxisP = lenEdge.valueAt(lenEdge.FirstParameter) + thkDir * -bendR

        # wallSolid = None
        if sketches:
            Wall_face = Part.makeFace(sketch.Shape.Wires, "Part::FaceMakerBullseye")
            if inside:
                Wall_face.translate(FaceDir * offset)
            FaceAxisP = sketch_Edge.valueAt(sketch_Edge.FirstParameter) + thkDir * thk
            FaceAxisV = sketch_Edge.valueAt(
                sketch_Edge.FirstParameter
            ) - sketch_Edge.valueAt(sketch_Edge.LastParameter)
            Wall_face.rotate(FaceAxisP, FaceAxisV, -90.0)
            wallSolid = Wall_face.extrude(thkDir * -thk)
            # Part.show(wallSolid)
            wallSolid.rotate(revAxisP, revAxisV, bendA)

        elif extLen > 0.0:
            # create wall
            Wall_face = smMakeFace(
                lenEdge,
                FaceDir,
                extLen,
                gap1 - extend1,
                gap2 - extend2,
                miterA1List[i],
                miterA2List[i],
                op="SMW",
            )
            wallSolid = Wall_face.extrude(thkDir * thk)
            # Part.show(wallSolid,"wallSolid")
            wallSolid.rotate(revAxisP, revAxisV, bendA)
            # Part.show(wallSolid.Faces[2])
            thk_faceList.append(wallSolid.Faces[2])

        # Produce bend Solid
        if not (unfold):
            if bendA > 0.0:
                # create bend
                # narrow the wall if we have gaps
                revFace = smMakeFace(lenEdge, thkDir, thk, gap1, gap2, op="SMR")
                if revFace.normalAt(0, 0) != FaceDir:
                    revFace.reverse()
                bendSolid = revFace.revolve(revAxisP, revAxisV, bendA)
                # Part.show(bendSolid)
                resultSolid = resultSolid.fuse(bendSolid)
            if wallSolid:
                resultSolid = resultSolid.fuse(wallSolid)
                # Part.show(resultSolid,"resultSolid")

        # Produce unfold Solid
        else:
            if bendA > 0.0:
                # create bend
                unfoldLength = (bendR + kfactor * thk) * bendA * math.pi / 180.0
                # narrow the wall if we have gaps
                unfoldFace = smMakeFace(lenEdge, thkDir, thk, gap1, gap2, op="SMR")
                if unfoldFace.normalAt(0, 0) != FaceDir:
                    unfoldFace.reverse()
                unfoldSolid = unfoldFace.extrude(FaceDir * unfoldLength)
                # Part.show(unfoldSolid)
                resultSolid = resultSolid.fuse(unfoldSolid)

            if extLen > 0.0:
                wallSolid.rotate(revAxisP, revAxisV, -bendA)
                # Part.show(wallSolid, "wallSolid")
                wallSolid.translate(FaceDir * unfoldLength)
                resultSolid = resultSolid.fuse(wallSolid)
    # Part.show(resultSolid, "resultSolid")
    return resultSolid, thk_faceList

