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

import Part


def reliefMakeFace(vertex, face, edges, relief):
    if edges[0].Vertexes[0].isSame(vertex):
        Edgedir1 = edges[0].Vertexes[1].Point - edges[0].Vertexes[0].Point
    else:
        Edgedir1 = edges[0].Vertexes[0].Point - edges[0].Vertexes[1].Point
    Edgedir1.normalize()

    if edges[1].Vertexes[0].isSame(vertex):
        Edgedir2 = edges[1].Vertexes[1].Point - edges[1].Vertexes[0].Point
    else:
        Edgedir2 = edges[1].Vertexes[0].Point - edges[1].Vertexes[1].Point
    Edgedir2.normalize()
    normal = face.normalAt(0, 0)
    Edgedir3 = normal.cross(Edgedir1)
    Edgedir4 = normal.cross(Edgedir2)

    p1 = vertex.Point
    p2 = p1 + relief * Edgedir1
    p3 = p2 + relief * Edgedir3
    if not (face.isInside(p3, 0.0, True)):
        p3 = p2 + relief * Edgedir3 * -1
    p6 = p1 + relief * Edgedir2
    p5 = p6 + relief * Edgedir4
    if not (face.isInside(p5, 0.0, True)):
        p5 = p6 + relief * Edgedir4 * -1
    # print([p1,p2,p3,p5,p6,p1])

    e1 = Part.makeLine(p2, p3)
    # Part.show(e1,'e1')
    e2 = Part.makeLine(p5, p6)
    # Part.show(e2,'e2')
    section = e1.section(e2)
    # Part.show(section1,'section1')

    if section.Vertexes:
        wire = Part.makePolygon([p1, p2, p3, p6, p1])
    else:
        p41 = p3 + relief * Edgedir1 * -1
        p42 = p5 + relief * Edgedir2 * -1
        e1 = Part.Line(p3, p41).toShape()
        # Part.show(e1,'e1')
        e2 = Part.Line(p42, p5).toShape()
        # Part.show(e2,'e2')
        section = e1.section(e2)
        # Part.show(section1,'section1')
        p4 = section.Vertexes[0].Point
        wire = Part.makePolygon([p1, p2, p3, p4, p5, p6, p1])

    extface = Part.Face(wire)
    return extface


def reliefMakeSolid(relief=2.0, selVertexNames=" ", MainObject=None):
    resultSolid = MainObject
    for selVertexName in selVertexNames:
        vertex = MainObject.getElement(selVertexName)
        facelist = MainObject.ancestorsOfType(vertex, Part.Face)

        extsolidlist = []
        for face in facelist:
            # Part.show(face,'face')
            edgelist = face.ancestorsOfType(vertex, Part.Edge)
            # for edge in edgelist :
            # Part.show(edge,'edge')
            extface = reliefMakeFace(vertex, face, edgelist, relief)
            # Part.show(extface,'extface')
            extsolid = extface.extrude(relief * face.normalAt(0, 0) * -1)
            extsolidlist.append(extsolid)

        cutsolid = extsolidlist[0].multiFuse(extsolidlist[1:])
        # Part.show(cutsolid,'cutsolid')
        cutsolid = cutsolid.removeSplitter()
        resultSolid = resultSolid.cut(cutsolid)
        # Part.show(resultsolid,'resultsolid')

    return resultSolid
