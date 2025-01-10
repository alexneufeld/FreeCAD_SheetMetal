###################################################################################
#
#  SheetMetalNewUnfolder.py
#
#  Copyright 2025 Alex Neufeld <alex.d.neufeld@gmail.com>
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#
###################################################################################

from enum import Enum, auto
from functools import reduce
from itertools import combinations
from math import degrees, log10, pi, radians, sin, tan
from operator import mul as multiply_operator
from statistics import StatisticsError, mode
from typing import Self

import FreeCAD
import Part
from Draft import makeSketch
from FreeCAD import Matrix, Placement, Rotation, Vector
from TechDraw import projectEx as project_shape_to_plane

try:
    import networkx as nx
except ImportError:
    FreeCAD.Console.PrintUserError(
        "The NetworkX Python package could not be imported. "
        "Consider checking that it is installed, "
        "or reinstalling the SheetMetal workbench using the addon manager\n"
    )

# used when comparing positions in 3D space
eps = FreeCAD.Base.Precision.approximation()
# used when comparing angles
eps_angular = FreeCAD.Base.Precision.angular()


class EstimateThickness:
    """This class provides helper functions to determine the sheet thickness
    of a solid-modelled sheet metal part."""

    @staticmethod
    def from_cylinders(shp: Part.Shape) -> float:
        """In a typical sheet metal part, the solid model has lots of bends, each
        bend having 2 concentric cylindrical faces. If we take the modal
        difference between all possible combinations of radii present in the
        subset of shape faces which are cylindrical, we will usually get the
        exact thickness of the sheet metal part."""
        num_places = abs(int(log10(eps)))
        curv_map = {}
        for face in shp.Faces:
            if face.Surface.TypeId == "Part::GeomCylinder":
                # normalize the axis and center-point
                normalized_axis = face.Surface.Axis.normalize()
                if normalized_axis.dot(FreeCAD.Vector(0, 0, -1)) < 0:
                    normalized_axis = normalized_axis.negative()
                cleaned_axis = FreeCAD.Vector(
                    *[round(d, num_places) for d in normalized_axis]
                )
                adjusted_center = face.Surface.Center.projectToPlane(
                    FreeCAD.Vector(), normalized_axis
                )
                cleaned_center = FreeCAD.Vector(
                    *[round(d, num_places) for d in adjusted_center]
                )
                key = (*cleaned_axis, *cleaned_center)
                if key in curv_map:
                    curv_map[key].append(face.Surface.Radius)
                else:
                    curv_map[key] = [
                        face.Surface.Radius,
                    ]
        combined_list_of_thicknesses = [
            val
            for radset in curv_map.values()
            if len(radset) > 1
            for r1, r2 in combinations(radset, 2)
            if (val := abs(r1 - r2)) > eps
        ]
        try:
            thickness_value = mode(combined_list_of_thicknesses)
            return thickness_value
        except StatisticsError:
            return 0.0

    @staticmethod
    def from_face(shape: Part.Shape, selected_face: int) -> float:
        ref_face = shape.Faces[selected_face]
        # find all planar faces that are parallel to the chosen face
        candidates = [
            f
            for f in shape.Faces
            if f.hashCode() != ref_face.hashCode()
            and f.Surface.TypeId == "Part::GeomPlane"
            and ref_face.Surface.Axis.isParallel(f.Surface.Axis, eps_angular)
        ]
        if not candidates:
            return 0.0
        opposite_face = sorted(candidates, key=lambda x: abs(x.Area - ref_face.Area))[0]
        return abs(
            opposite_face.valueAt(0, 0).distanceToPlane(
                ref_face.Surface.Position, ref_face.Surface.Axis
            )
        )

    @staticmethod
    def using_best_method(shape: Part.Shape, selected_face: int) -> float:
        thickness = EstimateThickness.from_cylinders(shape)
        if not thickness:
            thickness = EstimateThickness.from_face(shape, selected_face)
        if not thickness:
            errmsg = "Couldn't estimate thickness for shape!"
            raise RuntimeError(errmsg)
        return thickness


class TangentFaces:
    """This class provides functions to check if brep faces are tangent to
    each other. each compare_x_x function accepts two surfaces of a
    particular type, and returns a boolean value indicating tangency.
    The compare function accepts two faces and selects the correct
    compare_x_x function automatically,"""

    @staticmethod
    def compare_plane_plane(p1: Part.Plane, p2: Part.Plane) -> bool:
        # returns True if the two planes have similar normals and the base
        # point of the first plane is (nearly) coincident with the second plane
        return (
            p1.Axis.isParallel(p2.Axis, eps_angular)
            and p1.Position.distanceToPlane(p2.Position, p2.Axis) < eps
        )

    @staticmethod
    def compare_plane_cylinder(p: Part.Plane, c: Part.Cylinder) -> bool:
        # returns True if the cylinder is tangent to the plane
        # (there is 'line contact' between the surfaces)
        return (
            p.Axis.isNormal(c.Axis, eps_angular)
            and abs(abs(c.Center.distanceToPlane(p.Position, p.Axis)) - c.Radius) < eps
        )

    @staticmethod
    def compare_cylinder_cylinder(c1: Part.Cylinder, c2: Part.Cylinder) -> bool:
        # returns True if the two cylinders have parallel axis' and those axis'
        # are separated by a distance of approximately r1 + r2
        return (
            c1.Axis.isParallel(c2.Axis, eps_angular)
            and abs(
                c1.Center.distanceToLine(c2.Center, c2.Axis) - (c1.Radius + c2.Radius)
            )
            < eps
        )

    @staticmethod
    def compare_plane_torus(p: Part.Plane, t: Part.Toroid) -> bool:
        # Imagine a donut sitting flat on a table.
        # That's our tangency condition for a plane and a toroid.
        return (
            p.Axis.isParallel(t.Axis, eps_angular)
            and abs(abs(t.Center.distanceToPlane(p.Position, p.Axis)) - t.MinorRadius)
            < eps
        )

    @staticmethod
    def compare_cylinder_torus(c: Part.Cylinder, t: Part.Toroid) -> bool:
        # If the surfaces are tangent, either we have:
        # - a donut inside a circular container, with no gap at the container perimeter
        # - a donut shoved onto a shaft with no wiggle room
        # - a cylinder with an axis tangent to the central circle of the donut
        return (
            c.Axis.isParallel(t.Axis, eps_angular)
            and c.Center.distanceToLine(t.Center, t.Axis) < eps
            and (
                abs(c.Radius - abs(t.MajorRadius - t.MinorRadius)) < eps
                or abs(c.Radius - abs(t.MajorRadius + t.MinorRadius)) < eps
            )
        ) or (
            c.Axis.isNormal(t.Axis, eps_angular)
            and abs(abs(t.Center.distanceToLine(c.Center, c.Axis)) - t.MajorRadius)
            < eps
            and abs(c.Radius - t.MinorRadius) < eps
        )

    @staticmethod
    def compare_sphere_sphere(s1: Part.Sphere, s2: Part.Sphere) -> bool:
        # only segments of identical spheres are tangent to each other
        return (
            s1.Center.distanceToPoint(s2.Center) < eps
            and abs(s1.Radius - s2.Radius) < eps
        )

    @staticmethod
    def compare_plane_sphere(p: Part.Plane, s: Part.Sphere) -> bool:
        # This function will probably never actually return True,
        # because a plane and a sphere only ever share a vertex if
        # they are tangent to each other
        return abs(abs(s.Center.distanceToPlane(p.Position, p.Axis)) - s.Radius) < eps

    @staticmethod
    def compare_torus_sphere(t: Part.Toroid, s: Part.Sphere) -> bool:
        return (
            s.Center.distanceToPoint(t.Center) < eps
            and (
                abs(t.MajorRadius - t.MinorRadius - s.Radius) < eps
                or abs(t.MajorRadius + t.MinorRadius - s.Radius) < eps
            )
        ) or (
            abs(s.Radius - t.MinorRadius) < eps
            and t.Axis.isNormal(s.Center - t.Center, eps_angular)
            and abs(t.Center.distanceToPoint(s.Center) - t.MajorRadius) < eps
        )

    @staticmethod
    def compare_torus_torus(t1: Part.Toroid, t2: Part.Toroid) -> bool:
        return (
            t1.Center.distanceToLine(t2.Center, t2.Axis) < eps
            and t1.Axis.isParallel(t2.Axis, eps_angular)
            and abs(
                t1.Center.distanceToPoint(t2.Center) ** 2
                + (t1.MajorRadius - t2.MajorRadius) ** 2
                - (t1.MinorRadius + t2.MinorRadius) ** 2
            )
            < eps
        )

    @staticmethod
    def compare_cylinder_sphere(c: Part.Cylinder, s: Part.Sphere) -> bool:
        # the sphere must be sized/positioned like a ball sliding down a tube
        # with no wiggle room
        return (
            s.Center.distanceToLine(c.Center, c.Axis) < eps
            and abs(s.Radius - c.Radius) < eps
        ) or (
            # point contact case
            abs(s.Center.distanceToLine(c.Center, c.Axis) - s.Radius - c.Radius) < eps
        )

    @staticmethod
    def compare_plane_cone(p: Part.Plane, cn: Part.Cone) -> bool:
        return abs(cn.Apex.distanceToPlane(p.Position, p.Axis)) < eps and (
            abs(cn.Axis.getAngle(p.Axis) - abs(cn.SemiAngle) - pi / 2) < eps_angular
            or abs(cn.Axis.getAngle(p.Axis) + abs(cn.SemiAngle) - pi / 2) < eps_angular
        )

    @staticmethod
    def compare_cone_cone(cn1: Part.Cone, cn2: Part.Cone) -> bool:
        return (
            cn1.Apex.distanceToPoint(cn2.Apex) < eps
            and abs(cn1.Axis.getAngle(cn2.Axis) - cn1.SemiAngle - cn2.SemiAngle)
            < eps_angular
        )

    @staticmethod
    def compare_sphere_cone(s: Part.Sphere, cn: Part.Cone) -> bool:
        return (
            s.Center.distanceToLine(cn.Apex, cn.Axis) < eps
            and (cn.Apex.distanceToPoint(s.Center) * sin(cn.SemiAngle) - s.Radius) < eps
        )

    @staticmethod
    def compare_cylinder_cone(c: Part.Cylinder, cn: Part.Cone) -> bool:
        return abs(cn.Apex.distanceToLine(c.Center, c.Axis) - c.Radius) < eps and (
            abs(c.Axis.getAngle(cn.Axis) - cn.SemiAngle) < eps_angular
            or abs(pi - c.Axis.getAngle(cn.Axis) - abs(cn.SemiAngle)) < eps_angular
        )

    @staticmethod
    def compare_torus_cone(t: Part.Toroid, cn: Part.Cone) -> bool:
        return (
            t.Axis.isParallel(cn.Axis, eps_angular)
            and cn.Apex.distanceToLine(t.Center, t.Axis) < eps
            and (
                abs(
                    t.MajorRadius / tan(cn.SemiAngle)
                    - t.MinorRadius / sin(cn.SemiAngle)
                    - cn.Apex.distanceToPoint(t.Center)
                )
                < eps
                or abs(
                    t.MajorRadius / tan(cn.SemiAngle)
                    + t.MinorRadius / sin(cn.SemiAngle)
                    - cn.Apex.distanceToPoint(t.Center)
                )
                < eps
            )
        )

    @staticmethod
    def compare_plane_extrusion(p: Part.Plane, ex: Part.SurfaceOfExtrusion) -> bool:
        return False  # TODO

    @staticmethod
    def compare_cylinder_extrusion(
        c: Part.Cylinder, ex: Part.SurfaceOfExtrusion
    ) -> bool:
        return False  # TODO

    @staticmethod
    def compare_torus_extrusion(t: Part.Toroid, ex: Part.SurfaceOfExtrusion) -> bool:
        return False  # TODO

    @staticmethod
    def compare_sphere_extrusion(s: Part.Sphere, ex: Part.SurfaceOfExtrusion) -> bool:
        return False  # TODO

    @staticmethod
    def compare_extrusion_extrusion(
        ex1: Part.SurfaceOfExtrusion, ex2: Part.SurfaceOfExtrusion
    ) -> bool:
        return False  # TODO

    @staticmethod
    def compare_extrusion_cone(ex: Part.SurfaceOfExtrusion, cn: Part.Cone) -> bool:
        return False  # TODO

    @staticmethod
    def compare(face1: Part.Face, face2: Part.Face) -> bool:
        # order types to simplify pattern matching
        s1 = face1.Surface
        s2 = face2.Surface
        type1 = s1.TypeId
        type2 = s2.TypeId
        order = [
            "Part::GeomPlane",
            "Part::GeomCylinder",
            "Part::GeomToroid",
            "Part::GeomSphere",
            "Part::GeomSurfaceOfExtrusion",
            "Part::GeomCone",
        ]
        needs_swap = (
            type1 in order
            and type2 in order
            and order.index(type1) > order.index(type2)
        )
        if needs_swap:
            s2, s1 = s1, s2
        cls = TangentFaces
        match s1.TypeId, s2.TypeId:
            # plane
            case "Part::GeomPlane", "Part::GeomPlane":
                return cls.compare_plane_plane(s1, s2)
            case "Part::GeomPlane", "Part::GeomCylinder":
                return cls.compare_plane_cylinder(s1, s2)
            case "Part::GeomPlane", "Part::GeomToroid":
                return cls.compare_plane_torus(s1, s2)
            case "Part::GeomPlane", "Part::GeomSphere":
                return cls.compare_plane_sphere(s1, s2)
            case "Part::GeomPlane", "Part::GeomSurfaceOfExtrusion":
                return cls.compare_plane_extrusion(s1, s2)
            case "Part::GeomPlane", "Part::GeomCone":
                return cls.compare_plane_cone(s1, s2)
            # cylinder
            case "Part::GeomCylinder", "Part::GeomCylinder":
                return cls.compare_cylinder_cylinder(s1, s2)
            case "Part::GeomCylinder", "Part::GeomToroid":
                return cls.compare_cylinder_torus(s1, s2)
            case "Part::GeomCylinder", "Part::GeomSphere":
                return cls.compare_cylinder_sphere(s1, s2)
            case "Part::GeomCylinder", "Part::GeomSurfaceOfExtrusion":
                return cls.compare_cylinder_extrusion(s1, s2)
            case "Part::GeomCylinder", "Part::GeomCone":
                return cls.compare_cylinder_cone(s1, s2)
            # torus
            case "Part::GeomToroid", "Part::GeomToroid":
                return cls.compare_torus_torus(s1, s2)
            case "Part::GeomToroid", "Part::GeomSphere":
                return cls.compare_torus_sphere(s1, s2)
            case "Part::GeomToroid", "Part::SurfaceOfExtrusion":
                return cls.compare_torus_extrusion(s1, s2)
            case "Part::GeomToroid", "Part::GeomCone":
                return cls.compare_torus_cone(s1, s2)
            # sphere
            case "Part::GeomSphere", "Part::GeomSphere":
                return cls.compare_sphere_sphere(s1, s2)
            case "Part::GeomSphere", "Part.GeomSurfaceOfExtrusion":
                return cls.compare_sphere_extrusion(s1, s2)
            case "Part::GeomSphere", "Part.GeomCone":
                return cls.compare_sphere_cone(s1, s2)
            # extrusion
            case "Part::GeomSurfaceOfExtrusion", "Part::GeomSurfaceOfExtrusion":
                return cls.compare_extrusion_extrusion(s1, s2)
            case "Part::GeomSurfaceOfExtrusion", "Part::GeomCone":
                return cls.compare_extrusion_cone(s1, s2)
            # cone
            case "Part::GeomCone", "Part::GeomCone":
                return cls.compare_cone_cone(s1, s2)
            # all other cases
            case _:
                return False


class UVRef(Enum):
    """Describes reference corner for a rectangular-ish surface patch"""

    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()


class BendDirection(Enum):
    """Up is like a tray with a raised lip,
    down is like the rolled over edges of a table."""

    UP = auto()
    DOWN = auto()

    @staticmethod
    def from_face(bent_face: Part.Face) -> Self:
        """Cylindrical faces may be convex or concave, and the boundary
        representation can be forward or reversed. the bend direction may be
        determined according to these values."""
        curv_a, curv_b = bent_face.curvatureAt(0, 0)
        if curv_a < 0 and abs(curv_b) < eps:
            if bent_face.Orientation == "Forward":
                return BendDirection.DOWN
            else:
                return BendDirection.UP
        elif curv_b > 0 and abs(curv_a) < eps:
            if bent_face.Orientation == "Forward":
                return BendDirection.UP
            else:
                return BendDirection.DOWN
        else:
            errmsg = "Unable to determine bend direction from cylindrical face"
            raise RuntimeError(errmsg)


class SketchExtraction:
    """Helper functions to produce clean 2D geometry from unfolded shapes."""

    @staticmethod
    def edges_to_sketch_object(
        edges: list[Part.Edge], object_name: str
    ) -> FreeCAD.DocumentObject:
        """Uses functionality from the Draft API to convert a list of edges into a
        Sketch document object. This allows the user to more easily make small
        changes to the sheet metal cutting pattern when prepping it
        for fabrication."""
        cleaned_up_edges = Edge2DCleanup.cleanup_sketch(edges, 0.1)
        sk = makeSketch(
            # NOTE: in testing, using the autoconstraint feature
            # caused errors with some shapes
            cleaned_up_edges,
            autoconstraints=False,
            addTo=None,
            delete=False,
            name=object_name,
        )
        sk.Label = object_name
        return sk

    @staticmethod
    def wire_is_a_hole(w: Part.Wire) -> bool:
        return (
            len(w.Edges) == 1
            and w.Edges[0].Curve.TypeId == "Part::GeomCircle"
            and abs(w.Edges[0].Length - 2 * pi * w.Edges[0].Curve.Radius) < eps
        )

    @staticmethod
    def extract_manually(
        unfolded_shape: Part.Shape, normal: Vector
    ) -> tuple[Part.Shape]:
        """extract sketch lines from the topmost flattened face."""
        # Another approach would be to slice the flattened solid with a plane to
        # get a cross section of the middle of the unfolded shape.
        # This would probably be slower, but might be more robust in cases where
        # the outerwire is not cleanly defined.
        top_face = [
            f
            for f in unfolded_shape.Faces
            if f.normalAt(0, 0).getAngle(normal) < eps_angular
        ][0]
        sketch_profile = top_face.OuterWire
        inner_wires = []
        hole_wires = []
        for w in top_face.Wires:
            if w.hashCode() != sketch_profile.hashCode():
                if SketchExtraction.wire_is_a_hole(w):
                    hole_wires.append(w)
                else:
                    inner_wires.append(w)
        return sketch_profile, inner_wires, hole_wires

    @staticmethod
    def extract_with_techdraw(solid: Part.Shape, direction: Vector) -> Part.Shape:
        """Uses functionality from the TechDraw API to project
        a 3D shape onto a particular 2D plane."""
        # this is a slow but robust method of sketch profile extraction
        # ref: https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Draft/draftobjects/shape2dview.py
        raw_output = project_shape_to_plane(solid, direction)
        edges = [group for group in raw_output[:5] if not group.isNull()]
        compound = Part.makeCompound(edges)
        return compound

    @staticmethod
    def move_to_origin(sketch: Part.Compound, root_face: Part.Face) -> Matrix:
        """Given a 2d shape and a reference face, compute a transformation matrix
        that aligns the shape's bounding box to the origin of the XY-plane, with
        the reference face oriented Z-up and rotated square to the global
        coordinate system."""
        # find the orientation of the root face that aligns
        # the U-direction with the x-axis
        origin = root_face.valueAt(0, 0)
        x_axis = root_face.valueAt(1, 0) - origin
        z_axis = root_face.normalAt(0, 0)
        rotation = Rotation(x_axis, Vector(), z_axis, "ZXY")
        alignment_transform = Placement(origin, rotation).toMatrix().inverse()
        sketch_aligned_to_xy_plane = sketch.transformed(alignment_transform)
        # move in x and y so that the bounding box is entirely in the +x, +y quadrant
        mov_x = -1 * sketch_aligned_to_xy_plane.BoundBox.XMin
        mov_y = -1 * sketch_aligned_to_xy_plane.BoundBox.YMin
        mov_z = -1 * sketch_aligned_to_xy_plane.BoundBox.ZMin
        shift_transform = Placement(Vector(mov_x, mov_y, mov_z), Rotation()).toMatrix()
        overall_transform = Matrix()
        overall_transform.transform(Vector(), alignment_transform)
        overall_transform.transform(Vector(), shift_transform)
        return overall_transform


class BendAllowanceCalculator:
    def __init__(self) -> None:
        self.k_factor_standard = None
        self.radius_thickness_values = None
        self.k_factor_values = None

    @classmethod
    def from_single_value(cls, k_factor: float) -> Self:
        """one k-factor for all radius:thickness ratios"""
        instance = cls()
        instance.k_factor_standard = cls.KFactorStandard.ANSI
        instance.radius_thickness_values = [
            1.0,
        ]
        instance.k_factor_values = [
            k_factor,
        ]
        return instance

    def get_k_factor(self, radius: float, thickness: float) -> float:
        # if we are below the lowest tabulated value for the radius over
        # thickness relation, return the smallest noted k-factor
        r_over_t = radius / thickness
        if r_over_t <= self.radius_thickness_values[0]:
            kf_val = self.k_factor_values[0]
        # apply similar logic to radius:thickness values greater than
        # the largest available
        elif r_over_t >= self.radius_thickness_values[-1]:
            kf_val = self.k_factor_values[-1]
        # if we are within the range of specified radius:thickness values,
        # perform piecewise linear interpolation
        else:
            i = 0
            while r_over_t <= self.radius_thickness_values[i]:
                i += 1
            kf1 = self.k_factor_values[i]
            kf2 = self.k_factor_values[i + 1]
            rt1 = self.radius_thickness_values[i]
            rt2 = self.radius_thickness_values[i + 1]
            kf_val = kf1 + (kf2 - kf1) * ((r_over_t - rt1) / (rt2 - rt1))
        # we use the ansi definition of the k-factor everywhere internally
        return self._convert_to_ansi_kfactor(kf_val)

    def get_bend_allowance(
        self,
        bend_direction: BendDirection,
        radius: float,
        thickness: float,
        bend_angle: float,
    ) -> float:
        factor = self.get_k_factor(radius, thickness)
        if bend_direction == BendDirection.DOWN:
            factor -= 1
        bend_allowance = (radius + factor * thickness) * bend_angle
        return bend_allowance

    class KFactorStandard(Enum):
        ANSI = auto()
        DIN = auto()

    @classmethod
    def from_spreadsheet(cls, sheet: FreeCAD.DocumentObject) -> Self:
        instance = cls()
        r_t_header = sheet.getContents("A1")
        r_t_header = "".join(c for c in r_t_header if c not in "' ").lower()
        if r_t_header != "radius/thickness":
            errmsg = (
                "Cell A1 of material definition sheet must "
                'be exactly "Radius/Thickness"'
            )
            raise ValueError(errmsg)
        kf_header = sheet.getContents("B1")
        kf_header = "".join(c for c in kf_header if c not in "' -()").lower()
        if kf_header == "kfactoransi":
            instance.k_factor_standard = cls.KFactorStandard.ANSI
        elif kf_header == "kfactordin":
            instance.k_factor_standard = cls.KFactorStandard.DIN
        else:
            errmsg = (
                "Cell B1 of material definition sheet must be "
                'one of "K-factor (ANSI)" or "K-factor (DIN)"'
            )
            raise ValueError(errmsg)
        # read cells from the A column until we get to an empty cell
        number_of_columns = 0
        radius_thickness_list = []
        k_factor_list = []
        while next_rt_value := sheet.getContents("A" + str(number_of_columns + 2)):
            number_of_columns += 1
            radius_thickness_list.append(float(next_rt_value))
        # read corresponding k-factor values from the B column
        # and throw an error if we find an empty cell too early
        for i in range(number_of_columns):
            next_kf_value = sheet.getContents("B" + str(i + 2))
            if not next_kf_value:
                errmsg = (
                    "material definition sheet has an empty "
                    f"cell in the K-factors column (cell B{i+2})"
                )
                raise ValueError(errmsg)
            k_factor_list.append(float(next_kf_value))
        instance.radius_thickness_values = radius_thickness_list
        instance.k_factor_values = k_factor_list
        return instance

    def _convert_to_ansi_kfactor(self, k_factor: float) -> float:
        if self.k_factor_standard == self.KFactorStandard.DIN:
            return 2 * k_factor
        else:
            return k_factor


class Edge2DCleanup:
    """Many sheet metal fabrication suppliers, as well as CAM systems and
    laser cutting softwares, don't have good support for geometric
    primitives other than lines and arcs. This class features tools to
    replace bezier curves and other geometry types with lines and arcs"""

    @staticmethod
    def bspline_to_line(curve: Part.Edge) -> tuple[Part.Edge, float]:
        p1 = curve.firstVertex().Point
        p2 = curve.lastVertex().Point
        if p1.distanceToPoint(p2) < eps:
            return Part.Edge(), float("inf")
        line = Part.makeLine(p1, p2)
        max_err = Edge2DCleanup.check_err(curve, line)
        return line, max_err

    @staticmethod
    def check_err(curve1: Part.Edge, curve2: Part.Edge) -> float:
        n_points = 10
        max_err = 0.00
        for i in range(n_points):
            curve1_parameter = curve1.FirstParameter + (
                curve1.LastParameter - curve1.FirstParameter
            ) * (i + 1) / (n_points + 1)
            curve2_parameter = curve2.FirstParameter + (
                curve2.LastParameter - curve2.FirstParameter
            ) * (i + 1) / (n_points + 1)
            err = curve1.valueAt(curve1_parameter).distanceToPoint(
                curve2.valueAt(curve2_parameter)
            )
            if err > max_err:
                max_err = err
        return max_err

    @staticmethod
    def bspline_to_arc(curve: Part.Edge) -> tuple[Part.Edge, float]:
        point1 = curve.firstVertex().Point
        point2 = curve.valueAt(
            curve.FirstParameter + 0.5 * (curve.LastParameter - curve.FirstParameter)
        )
        point3 = curve.lastVertex().Point
        if point1.distanceToPoint(point3) < eps:
            # full circle
            point4 = curve.valueAt(
                curve.FirstParameter
                + 0.25 * (curve.LastParameter - curve.FirstParameter)
            )
            radius = point1.distanceToPoint(point2) / 2
            center = point1 + 0.5 * (point2 - point1)
            axis = (point1 - center).cross(point4 - center)
            arc = Part.makeCircle(radius, center, axis)
        else:
            # partial circle
            arc = Part.Arc(point1, point2, point3).toShape().Edges[0]
        max_err = Edge2DCleanup.check_err(curve, arc)
        return arc, max_err

    @staticmethod
    def cleanup_sketch(sketch: list[Part.Edge], tolerance: float) -> list[Part.Edge]:
        new_edge_list = []
        for edge in sketch:
            match edge.Curve.TypeId:
                case "Part::GeomLine" | "Part::GeomCircle":
                    new_edge_list.append(edge)
                case _:
                    if isinstance(edge.Curve, Part.BSplineCurve):
                        bspline = edge
                    else:
                        bspline = edge.toNurbs().Edges[0]
                    new_edge, max_err = Edge2DCleanup.bspline_to_line(bspline)
                    if max_err < tolerance:
                        new_edge_list.append(new_edge)
                        continue
                    new_edge, max_err = Edge2DCleanup.bspline_to_arc(bspline)
                    if max_err < tolerance:
                        new_edge_list.append(new_edge)
                        continue
                    new_edge_list.extend(
                        a.toShape().Edges[0] for a in bspline.Curve.toBiArcs(tolerance)
                    )
        return new_edge_list


def build_graph_of_tangent_faces(shp: Part.Shape, root: int) -> nx.Graph:
    # created a simple undirected graph object
    graph_of_shape_faces = nx.Graph()
    # track faces by their indices, because the underlying pointers to faces
    # may get changed around while building the graph.
    face_hashes = [f.hashCode() for f in shp.Faces]
    index_lookup = {h: i for i, h in enumerate(face_hashes)}
    # get pairs of faces that share the same edge
    candidates = [
        (i, shp.ancestorsOfType(e, Part.Face)) for i, e in enumerate(shp.Edges)
    ]
    # filter to remove seams on cylinders or other faces that wrap back onto themselves
    # other than self-adjacent faces, edges should always have 2 face ancestors
    # this assumption is probably only valid for watertight solids.
    for edge_index, faces in filter(lambda c: len(c[1]) == 2, candidates):
        face_a, face_b = faces
        if TangentFaces.compare(face_a, face_b):
            graph_of_shape_faces.add_edge(
                index_lookup[face_a.hashCode()],
                index_lookup[face_b.hashCode()],
                label=edge_index,  # store indexes in the label attr for debugging
            )
    # graph_of_shape_faces should have at least three connected subgraphs
    # (top side, bottom side, and sheet edge sides of the sheetmetal part).
    # We only care about the subgraph that includes the selected root face.
    for c in nx.connected_components(graph_of_shape_faces):
        if root in c:
            return graph_of_shape_faces.subgraph(c).copy()
    # raise and error if there is nothing tangent to the seed face
    errmsg = (
        "No faces were found that are tangent to the selected face. "
        "Try selecting a different face, and/"
        "or confirm that the shape is a watertight solid."
    )
    raise RuntimeError(errmsg)


def unroll_cylinder(
    cylindrical_face: Part.Face,
    refpos: UVRef,
    bac: BendAllowanceCalculator,
    thickness: float,
) -> tuple[Part.Face, Part.Shape]:
    """Given a cylindrical face and a reference corner, computes a flattened
    version of the face oriented with respect to the +x,+y quadrant of the
    2D plane."""
    umin, umax, vmin, vmax = cylindrical_face.ParameterRange
    bend_angle = umax - umin
    radius = cylindrical_face.Surface.Radius
    bend_direction = BendDirection.from_face(cylindrical_face)
    bend_allowance = bac.get_bend_allowance(
        bend_direction, radius, thickness, bend_angle
    )
    overall_height = abs(vmax - vmin)
    y_scale_factor = bend_allowance / bend_angle
    flattened_edges = []
    for e in cylindrical_face.Edges:
        edge_on_surface, e_param_min, e_param_max = cylindrical_face.curveOnSurface(e)
        if isinstance(edge_on_surface, (Part.Geom2d.Line2d, Part.Geom2d.Line2dSegment)):
            v1 = edge_on_surface.value(e_param_min)
            y1, x1 = v1.x - umin, v1.y - vmin
            v2 = edge_on_surface.value(e_param_max)
            y2, x2 = v2.x - umin, v2.y - vmin
            line = Part.makeLine(
                Vector(x1, y1 * y_scale_factor), Vector(x2, y2 * y_scale_factor)
            )
            flattened_edges.append(line)
        elif isinstance(edge_on_surface, Part.Geom2d.BSplineCurve2d):
            poles_and_weights = edge_on_surface.getPolesAndWeights()
            poles = [
                (v - vmin, (u - umin) * y_scale_factor, 0)
                for u, v, _ in poles_and_weights
            ]
            weights = [w for _, _, w in poles_and_weights]
            spline = Part.BSplineCurve()
            spline.buildFromPolesMultsKnots(poles=poles, weights=weights)
            flattened_edges.append(spline.toShape())
        else:
            errmsg = (
                f"Unhandled curve type when unfolding face: {type(edge_on_surface)}"
            )
            raise TypeError(errmsg)
    # the edges recovered from cylindrical_face.Edges are likely to not be
    # ordered and oriented tip-to-tail, which are requirements for the
    # FaceMaker classes to produce valid output. Running Part.sortEdges
    # fixes this.
    list_of_list_of_edges = Part.sortEdges(flattened_edges)
    wires = [Part.Wire(x) for x in list_of_list_of_edges]
    try:
        face = Part.makeFace(wires, "Part::FaceMakerBullseye")
    except RuntimeError:
        errmsg = "Failed to create unbent face from cylinder"
        raise RuntimeError(errmsg) from None
    mirror_base_pos = Vector(overall_height / 2, bend_allowance / 2)
    # there are four possible orientations of the face corresponding to four
    # quadrants of the 2D plane. Whether flipping across the x/y/both axis is
    # required depends on the initial orientation and the UV parameters.
    # The correct flip conditions were figured out by brute force
    # (checking each possible permutation).
    match refpos:
        case UVRef.BOTTOM_LEFT:
            fixed_face = face
        case UVRef.BOTTOM_RIGHT:
            fixed_face = face.mirror(mirror_base_pos, Vector(0, 1))
        case UVRef.TOP_LEFT:
            fixed_face = face.mirror(mirror_base_pos, Vector(1, 0))
        case UVRef.TOP_RIGHT:
            fixed_face = face.mirror(mirror_base_pos, Vector(0, 1)).mirror(
                mirror_base_pos, Vector(1, 0)
            )
    # Draw a bend line a little bit longer than the original face,
    # then trim away the excess.
    bent_volume = fixed_face.translated(Vector(0, 0, -0.5)).extrude(Vector(0, 0, 1))
    half_bend_width = Vector(0.55 * (vmax - vmin), 0)
    bend_line = bent_volume.common(
        Part.makeLine(
            mirror_base_pos + half_bend_width, mirror_base_pos - half_bend_width
        )
    )
    return fixed_face, bend_line


def compute_unbend_transform(
    bent_face: Part.Face,
    base_edge: Part.Edge,
    thickness: float,
    bac: BendAllowanceCalculator,
) -> tuple[Matrix, Matrix, UVRef]:
    """Computes the position and orientation of a reference corner on a bent
    surface, as well as a transformation to flatten out subsequent faces to
    align with the pre-bend part of the shape"""
    # for cylindrical surfaces, the u-parameter corresponds to the radial
    # direction, and the u-period is the radial boundary of the cylindrical
    # patch. The v-period corresponds to the axial direction.
    umin, umax, vmin, vmax = bent_face.ParameterRange
    # the u period is always positive: 0.0 <= umin < umax <= 2*pi
    bend_angle = umax - umin
    radius = bent_face.Surface.Radius
    # disallow fully cylindrical bends. These can't be formed because the
    # opposite edge of the sheet will intersect the previous face
    if bend_angle > radians(359.9):
        errmsg = "Bend angle must be less that 359.9 degrees"
        raise RuntimeError(errmsg)
    bend_direction = BendDirection.from_face(bent_face)
    # the reference edge should intersect with the bent cylindrical surface at
    # either opposite corner of surface's uv-parameter range.
    # We need to determine which of these possibilities is correct
    first_corner_point = bent_face.valueAt(umin, vmin)
    second_corner_point = bent_face.valueAt(umax, vmin)
    # at least one of these points should be on the starting edge
    dist1 = first_corner_point.distanceToLine(
        base_edge.Curve.Location, base_edge.Curve.Direction
    )
    dist2 = second_corner_point.distanceToLine(
        base_edge.Curve.Location, base_edge.Curve.Direction
    )
    # the x-axis of our desired reference is the tangent vector to a radial
    # line on the cylindrical surface, oriented away from the previous face.
    # We can compute candidates to choose from with the .tangent() method
    if dist1 < eps:  # 'Forward' orientation
        tangent_vector, binormal_vector = bent_face.Surface.tangent(umin, vmin)
        y_axis = tangent_vector
        # use the normal of the face and not the surface here
        # If the face is reverse oriented, the surface normal will be flipped
        # relative to the face normal.
        z_axis = bent_face.normalAt(umin, vmin)
        # place the reference point such that the cylindrical face lies in the
        # (+x, +y) quadrant of the xy-plane of the reference coordinate system
        x_axis = y_axis.cross(z_axis)
        if x_axis.dot(corner_1 := bent_face.valueAt(umin, vmin)) < x_axis.dot(
            corner_2 := bent_face.valueAt(umin, vmax)
        ):
            lcs_base_point = corner_1
            uvref = UVRef.BOTTOM_LEFT
        else:
            lcs_base_point = corner_2
            uvref = UVRef.TOP_LEFT
    elif dist2 < eps:  # 'Reverse' orientation
        tangent_vector, binormal_vector = bent_face.Surface.tangent(umax, vmin)
        y_axis = tangent_vector.negative()
        z_axis = bent_face.normalAt(umax, vmin)
        x_axis = y_axis.cross(z_axis)
        if x_axis.dot(corner_3 := bent_face.valueAt(umax, vmin)) < x_axis.dot(
            corner_4 := bent_face.valueAt(umax, vmax)
        ):
            lcs_base_point = corner_3
            uvref = UVRef.BOTTOM_RIGHT
        else:
            lcs_base_point = corner_4
            uvref = UVRef.TOP_RIGHT
    else:
        errmsg = "No point on reference edge"
        raise RuntimeError(errmsg)
    # note that the x-axis is ignored here based on the priority string
    lcs_rotation = Rotation(x_axis, y_axis, z_axis, "ZYX")
    alignment_transform = Placement(lcs_base_point, lcs_rotation).toMatrix()
    # the actual unbend transformation is found by reversing the rotation of
    # a flat face after the bend due to the bending operation,
    # then pushing it forward according to the bend allowance
    bend_allowance = bac.get_bend_allowance(
        bend_direction, radius, thickness, bend_angle
    )
    # fmt: off
    allowance_transform = Matrix(
        1, 0, 0, 0,
        0, 1, 0, bend_allowance,
        0, 0, 1, 0,
        0, 0, 0, 1
    )
    rot = Rotation(
        Vector(1, 0, 0),
        (-1 if bend_direction == BendDirection.UP else 1) * degrees(bend_angle)
    ).toMatrix()
    translate = Matrix(
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, (1 if bend_direction == BendDirection.UP else -1) * radius,
        0, 0, 0, 1
    )
    # fmt: on
    # compose transformations to get the final matrix
    overall_transform = Matrix()
    overall_transform.transform(Vector(), alignment_transform.inverse())
    overall_transform.transform(Vector(), translate * rot * translate.inverse())
    overall_transform.transform(Vector(), allowance_transform)
    overall_transform.transform(Vector(), alignment_transform)
    return alignment_transform, overall_transform, uvref


def unfold(
    shape: Part.Shape, root_face_index: int, bac: BendAllowanceCalculator
) -> tuple[Part.Shape, Part.Compound]:
    """Given a solid body of a sheet metal part and a reference face, computes
    a solid representation of the unbent object, as well as a compound object
    containing straight edges for each bend centerline."""
    graph_of_sheet_faces = build_graph_of_tangent_faces(shape, root_face_index)
    thickness = EstimateThickness.using_best_method(shape, root_face_index)
    # we could also get a random spanning tree here. Would that be faster?
    # Or is it better to take the opportunity to get a spanning tree that meets
    # some criteria for minimization?
    # I.E.: the shorter the longest path in the tree, the fewer nested
    # transformations we have to compute
    spanning_tree = nx.minimum_spanning_tree(graph_of_sheet_faces, weight="label")
    # convert to 'directed tree', where every edge points away from the selected face
    dg = nx.DiGraph()
    for node in spanning_tree:
        dg.add_node(node)
    lengths = nx.all_pairs_shortest_path_length(spanning_tree)
    distances_to_root_face = {k: kv for k, kv in lengths}[root_face_index]
    for f1, f2, edata in spanning_tree.edges(data=True):
        if distances_to_root_face[f1] <= distances_to_root_face[f2]:
            dg.add_edge(f1, f2, label=edata["label"])
        else:
            dg.add_edge(f2, f1, label=edata["label"])
    # the digraph should now have everything we need to unfold the shape,
    # For every edge f1--e1-->f2 where f2 is a cylindrical face, feed f1
    # through our unbending functions with e1 as the stationary edge.
    for e in [
        e for e in dg.edges if shape.Faces[e[1]].Surface.TypeId == "Part::GeomCylinder"
    ]:
        # the bend face is the end-node of the directed edge
        bend_part = shape.Faces[e[1]]
        # we stored the edge indices as the labels of the graph edges
        edge_before_bend_index = dg.get_edge_data(e[0], e[1])["label"]
        # check that we aren't trying to unfold across a non-linear reference edge
        # this condition is reached if the user supplies a part with complex formed
        # features that have unfoldable-but-tangent faces, for example.
        edge_before_bend = shape.Edges[edge_before_bend_index]
        if edge_before_bend.Curve.TypeId != "Part::GeomLine":
            errmsg = (
                "This shape appears to have bends across non-straight edges. "
                "Unfolding such a shape is not yet supported."
                f" (Edge{edge_before_bend_index + 1})"
            )
            raise RuntimeError(errmsg)
        # compute the unbend transformation matrices.
        alignment_transform, overall_transform, uvref = compute_unbend_transform(
            bend_part, edge_before_bend, thickness, bac
        )
        # Determine the unbent face shape from the reference UV position.
        # Also get a bend line across the middle of the flattened face.
        dg.nodes[e[1]]["unbend_transform"] = overall_transform
        try:
            unbent_face, bend_line = unroll_cylinder(bend_part, uvref, bac, thickness)
            # Add the transformation and unbend shape to the end node of the edge
            # as attributes.
            dg.nodes[e[1]]["unbent_shape"] = unbent_face.transformed(
                alignment_transform
            )
            dg.nodes[e[1]]["bend_line"] = bend_line.transformed(alignment_transform)
        except Exception as E:
            msg = (
                f"failed to unroll a cylindrical face (Face{e[1]+1})"
                + "\n"
                + f"Original exception: {E}\n"
            )
            FreeCAD.Console.PrintWarning(msg)
    # Get a path from the root (stationary) face to each other face,
    # so we can combine transformations to position the final shape.
    list_of_faces = []
    list_of_bend_lines = []
    # Apply the unbent transformation to all the flattened geometry to bring
    # it in-plane with the root face.
    for face_id, path in nx.shortest_path(dg, source=root_face_index).items():
        # the path includes the root face itself, which we don't need
        path_to_face = path[:-1]
        node_data = dg.nodes.data()
        # accumulate transformations while traversing from the root face to this face
        list_of_matrices = [
            node_data[f]["unbend_transform"]
            for f in path_to_face
            if "unbend_transform" in node_data[f]
        ]
        # use reduce() to do repeated matrix multiplication
        # Matrix() * M_1 * M_2 * ... * M_N for N matrices
        final_mat = reduce(multiply_operator, list_of_matrices, Matrix())
        # bent faces of the input shape are swapped for their unbent versions
        if "unbent_shape" in node_data[face_id]:
            finalized_face = node_data[face_id]["unbent_shape"]
        # planar faces of the input shape are returned aligned to the root face,
        # but otherwise unmodified
        else:
            finalized_face = shape.Faces[face_id]
        # also combine all of the bend lines into a list after positioning
        # them correctly
        if "bend_line" in node_data[face_id]:
            list_of_bend_lines.append(
                node_data[face_id]["bend_line"].transformed(final_mat)
            )
        list_of_faces.append(finalized_face.transformed(final_mat))
    # Extrude the 2d profile back into a flattened solid body.
    extrude_vec = (
        shape.Faces[root_face_index].normalAt(0, 0).normalize() * -1 * thickness
    )
    solid_components = [f.extrude(extrude_vec) for f in list_of_faces]
    # note that the multiFuse function can also accept a tolerance/fuzz value
    # argument. In testing, supplying such a value did not change performance
    solid = solid_components[0].multiFuse(solid_components[1:]).removeSplitter()
    bend_lines = Part.makeCompound(list_of_bend_lines)
    return solid, bend_lines


def gui_unfold(bac: BendAllowanceCalculator) -> None:
    """This is the main entry-point for the unfolder.
    It grabs a selected sheet metal part and reference face from the active
    FreeCAD document, and creates new objects showing the unfold results."""
    # the user must select a single flat face of a sheet metal part in the
    # active document
    selection = FreeCAD.Gui.Selection.getCompleteSelection()[0]
    selected_object = selection.Object
    object_placement = selected_object.getGlobalPlacement().toMatrix()
    shp = selected_object.Shape.transformed(object_placement.inverse())
    root_face_index = int(selection.SubElementNames[0][4:]) - 1
    unfolded_shape, bend_lines = unfold(shp, root_face_index, bac)
    # show the unfolded solid in the active document
    unfold_doc_obj = Part.show(unfolded_shape, selected_object.Label + "_Unfold")
    unfold_vobj = unfold_doc_obj.ViewObject
    unfold_doc_obj.Placement = Placement(object_placement)
    # set appearance
    unfold_vobj.ShapeAppearance = selected_object.ViewObject.ShapeAppearance
    unfold_vobj.Transparency = 70  # FIXME: hardcoded value
    root_normal = shp.Faces[root_face_index].normalAt(0, 0)
    sketch_profile, inner_wires, hole_wires = SketchExtraction.extract_manually(
        unfolded_shape, root_normal
    )
    SEPERATE_SKETCHES = False  # FIXME: hardcoded value
    if not SEPERATE_SKETCHES:
        sketch_profile = Part.makeCompound([sketch_profile, *inner_wires, *hole_wires])
        inner_wires = None
        hole_wires = None
    # move the sketch profiles nicely to the origin
    sketch_align_transform = SketchExtraction.move_to_origin(
        sketch_profile, shp.Faces[root_face_index]
    )
    sketch_profile = sketch_profile.transformed(sketch_align_transform)
    # organize the unfold sketch layers in a group
    sketch_doc_obj = SketchExtraction.edges_to_sketch_object(
        sketch_profile.Edges, selected_object.Label + "_UnfoldProfile"
    )
    sketch_objects_list = [
        sketch_doc_obj,
    ]
    sketch_color = (255, 0, 0, 0)  # FIXME: hardcoded value
    sketch_doc_obj.ViewObject.LineColor = sketch_color
    sketch_doc_obj.ViewObject.PointColor = sketch_color
    # bend lines are sometimes not present
    if bend_lines.Edges:
        bend_lines = bend_lines.transformed(sketch_align_transform)
        bend_lines_doc_obj = SketchExtraction.edges_to_sketch_object(
            bend_lines.Edges, selected_object.Label + "_UnfoldBendLines"
        )
        bend_color = (0, 255, 0, 0)  # FIXME: hardcoded value
        bend_lines_doc_obj.ViewObject.LineColor = bend_color
        bend_lines_doc_obj.ViewObject.PointColor = bend_color
        bend_lines_doc_obj.ViewObject.DrawStyle = "Dashdot"
        sketch_objects_list.append(bend_lines_doc_obj)
    # inner lines are sometimes not present
    if inner_wires:
        inner_lines = Part.makeCompound(inner_wires).transformed(sketch_align_transform)
        inner_lines_doc_obj = SketchExtraction.edges_to_sketch_object(
            inner_lines.Edges, selected_object.Label + "_UnfoldInnerLines"
        )
        inner_color = (0, 0, 255, 0)  # FIXME: hardcoded value
        inner_lines_doc_obj.ViewObject.LineColor = inner_color
        inner_lines_doc_obj.ViewObject.PointColor = inner_color
        sketch_objects_list.append(inner_lines_doc_obj)
    if hole_wires:
        hole_lines = Part.makeCompound(hole_wires).transformed(sketch_align_transform)
        hole_lines_doc_obj = SketchExtraction.edges_to_sketch_object(
            hole_lines.Edges, selected_object.Label + "_UnfoldHoles"
        )
        hole_color = (255, 255, 0, 0)  # FIXME: hardcoded value
        hole_lines_doc_obj.ViewObject.LineColor = hole_color
        hole_lines_doc_obj.ViewObject.PointColor = hole_color
        sketch_objects_list.append(hole_lines_doc_obj)
