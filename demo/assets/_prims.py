"""Parametric building blocks shared by every asset module.

Two layers: the original one-object-per-call helpers (box, cylinder, beam...) and
`Mesh`, a fast builder that accumulates many parts (multi-material) into one mesh
without bpy.ops calls. Detailed structures (trusses, walkways, machines) use Mesh;
the structural kit built on it is in `_steel.py`.
"""
from __future__ import annotations

import math
from contextlib import contextmanager

import bpy
from mathutils import Euler, Matrix, Vector

from demo import config

_mats: dict = {}


def reset():
    _mats.clear()


def material(name: str, rgba=None, metallic=None, roughness=None, dust=None, ribs=None):
    """Cached Principled material. rgba alpha < 1 makes it see-through.
    Defaults come from config.MATERIALS[name], then config.COLORS.
    dust: red-dust weathering strength on lower surfaces (0 = none).
    ribs: 'wall' / 'roof' / 'door' profiled-sheeting bump."""
    if name in _mats:
        return _mats[name]
    d = config.MATERIALS.get(name, {})
    rgba = rgba or d.get("rgba") or config.COLORS.get(name, (0.8, 0.8, 0.8, 1))
    metallic = d.get("metallic", 0.0) if metallic is None else metallic
    roughness = d.get("roughness", 0.6) if roughness is None else roughness
    dust = d.get("dust", 0.0) if dust is None else dust
    ribs = d.get("ribs") if ribs is None else ribs
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba                      # used by Solid-mode fallback
    if m.node_tree is None:
        m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if rgba[3] < 1.0:
        bsdf.inputs["Alpha"].default_value = rgba[3]
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"
    if dust and config.LOOK["dust"]:
        _add_dust(m, rgba, dust)
    if ribs and config.LOOK["ribs"]:
        _add_ribs(m, ribs)
    _mats[name] = m
    return m


def _add_dust(m, rgba, amount):
    """Mix toward red Pilbara dust below config.DUST['height'] (world z), broken up by
    noise, plus a light film everywhere. Dust is matte."""
    D = config.DUST
    nt = m.node_tree
    nd, lk = nt.nodes, nt.links
    bsdf = nd["Principled BSDF"]
    geo = nd.new("ShaderNodeNewGeometry")
    sep = nd.new("ShaderNodeSeparateXYZ")
    lk.new(geo.outputs["Position"], sep.inputs[0])
    ramp = nd.new("ShaderNodeMapRange")            # z 0 -> 1 (full dust), z >= height -> 0
    ramp.inputs["From Min"].default_value = 0.0
    ramp.inputs["From Max"].default_value = D["height"]
    ramp.inputs["To Min"].default_value = 1.0
    ramp.inputs["To Max"].default_value = 0.0
    lk.new(sep.outputs["Z"], ramp.inputs["Value"])
    noise = nd.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = D["noise_scale"]
    noise.inputs["Detail"].default_value = 1.0
    lk.new(geo.outputs["Position"], noise.inputs["Vector"])
    mul = nd.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    lk.new(ramp.outputs[0], mul.inputs[0])
    lk.new(noise.outputs["Fac"], mul.inputs[1])
    fac = nd.new("ShaderNodeMath")
    fac.operation = "MULTIPLY_ADD"
    fac.use_clamp = True
    lk.new(mul.outputs[0], fac.inputs[0])
    fac.inputs[1].default_value = 1.6 * amount
    fac.inputs[2].default_value = D["film"] * amount
    mix = nd.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    lk.new(fac.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = rgba
    mix.inputs["B"].default_value = D["rgba"]
    lk.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    rough = nd.new("ShaderNodeMath")
    rough.operation = "MAXIMUM"
    rough.inputs[1].default_value = bsdf.inputs["Roughness"].default_value
    lk.new(fac.outputs[0], rough.inputs[0])
    lk.new(rough.outputs[0], bsdf.inputs["Roughness"])


def _add_ribs(m, kind):
    """Profiled sheeting as a bump: wall varies with x+y (vertical ribs on axis-aligned
    walls), roof with x (ridge along x, ribs down the slope), door with z (slats)."""
    nt = m.node_tree
    nd, lk = nt.nodes, nt.links
    geo = nd.new("ShaderNodeNewGeometry")
    sep = nd.new("ShaderNodeSeparateXYZ")
    lk.new(geo.outputs["Position"], sep.inputs[0])
    coord = nd.new("ShaderNodeMath")
    if kind == "wall":
        coord.operation = "ADD"
        lk.new(sep.outputs["X"], coord.inputs[0])
        lk.new(sep.outputs["Y"], coord.inputs[1])
    else:
        coord.operation = "MULTIPLY"
        coord.inputs[1].default_value = 1.0
        lk.new(sep.outputs["Z" if kind == "door" else "X"], coord.inputs[0])
    pitch = config.DUST["door_pitch" if kind == "door" else "rib_pitch"]
    scale = nd.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = 2 * math.pi / pitch
    lk.new(coord.outputs[0], scale.inputs[0])
    wave = nd.new("ShaderNodeMath")
    wave.operation = "SINE"
    lk.new(scale.outputs[0], wave.inputs[0])
    bump = nd.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    bump.inputs["Distance"].default_value = 0.02
    lk.new(wave.outputs[0], bump.inputs["Height"])
    lk.new(bump.outputs["Normal"], nd["Principled BSDF"].inputs["Normal"])


def emissive(name, rgba, strength):
    m = material(name, rgba, roughness=0.3)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = rgba
    b.inputs["Emission Strength"].default_value = strength
    return m


def attr_material(name: str, attr: str = "col", roughness=0.8, attr_type="INSTANCER"):
    """Material whose base colour comes from a colour attribute
    (INSTANCER for GN instances, GEOMETRY for a mesh's own attribute)."""
    if name in _mats:
        return _mats[name]
    m = material(name + "_base", config.COLORS["ore"], roughness=roughness, dust=0.0)
    m.name = name
    nt = m.node_tree
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_type = attr_type
    a.attribute_name = attr
    nt.links.new(a.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    _mats[name] = m
    return m


def collection(name: str, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in (parent or bpy.context.scene.collection).children:
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def _finish(obj, name, mat, col, smooth=False):
    obj.name = name
    if mat is not None:
        obj.data.materials.append(mat)
    if smooth:
        obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    if col is not None:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        col.objects.link(obj)
    return obj


def box(name, size, loc, mat=None, col=None, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        m = o.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments = bevel, 1
    return _finish(o, name, mat, col)


def cylinder(name, r, depth, loc, mat=None, col=None, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth,
                                        location=loc, rotation=rot)
    return _finish(bpy.context.active_object, name, mat, col, smooth=True)


def cone(name, r_top, r_bot, depth, loc, mat=None, col=None, verts=20):
    """Vertical frustum centred at loc: r_top at the top, r_bot at the bottom."""
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r_bot, radius2=r_top,
                                    depth=depth, location=loc)
    return _finish(bpy.context.active_object, name, mat, col, smooth=True)


def torus(name, major, minor, loc, mat=None, col=None, segs=(32, 8)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc,
                                     major_segments=segs[0], minor_segments=segs[1])
    return _finish(bpy.context.active_object, name, mat, col, smooth=True)


def beam(name, p0, p1, r, mat=None, col=None, verts=8, square=False):
    """Pipe (round) or member (square) between two points."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rot = d.to_track_quat("Z", "Y").to_euler()
    mid = (p0 + p1) / 2
    if square:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=mid, rotation=rot)
        o = bpy.context.active_object
        o.scale = (2 * r, 2 * r, d.length)
        bpy.ops.object.transform_apply(scale=True)
        return _finish(o, name, mat, col)
    return cylinder(name, r, d.length, mid, mat, col, rot=rot, verts=verts)


def point_cloud(name, n, mat, radius, col=None, subdiv=1, colour_attr=False):
    """Mesh of n loose vertices drawn as instanced spheres (Geometry Nodes).
    Animate by writing vertex coordinates (set_points) and colours (set_colours)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(0.0, 0.0, -50.0)] * n, [], [])
    if colour_attr:
        me.attributes.new("col", "FLOAT_COLOR", "POINT")
    o = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(o)
    tree = bpy.data.node_groups.new(name + "_GN", "GeometryNodeTree")
    tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nd = tree.nodes
    gi, go = nd.new("NodeGroupInput"), nd.new("NodeGroupOutput")
    ico = nd.new("GeometryNodeMeshIcoSphere")
    ico.inputs["Radius"].default_value = radius
    ico.inputs["Subdivisions"].default_value = subdiv
    setm = nd.new("GeometryNodeSetMaterial")
    setm.inputs["Material"].default_value = mat
    inst = nd.new("GeometryNodeInstanceOnPoints")
    lk = tree.links
    lk.new(ico.outputs["Mesh"], setm.inputs["Geometry"])
    lk.new(gi.outputs["Geometry"], inst.inputs["Points"])
    lk.new(setm.outputs["Geometry"], inst.inputs["Instance"])
    lk.new(inst.outputs["Instances"], go.inputs["Geometry"])
    o.modifiers.new("Instances", "NODES").node_group = tree
    return o


def set_points(obj, coords):
    """coords: flat list [x0, y0, z0, x1, ...] with exactly 3 * vertex count values."""
    obj.data.vertices.foreach_set("co", coords)
    obj.data.update()


def set_colours(obj, rgba_flat):
    """rgba_flat: [r0, g0, b0, a0, r1, ...] for every vertex."""
    obj.data.attributes["col"].data.foreach_set("color", rgba_flat)
    obj.data.update()


# ====================================================================== fast builder
def ring(n, r=1.0, z=0.0, a0=0.0):
    return [(r * math.cos(a0 + 2 * math.pi * k / n), r * math.sin(a0 + 2 * math.pi * k / n), z)
            for k in range(n)]


_CUBE_V = [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
           (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]
_CUBE_F = {"-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4), "+x": (1, 2, 6, 5),
           "+y": (2, 3, 7, 6), "-x": (3, 0, 4, 7)}


def xform(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    r = rot.to_3x3() if isinstance(rot, Matrix) else Euler(rot).to_matrix()
    M = (r @ Matrix.Diagonal(Vector(scale))).to_4x4()
    M.translation = Vector(loc)
    return M


def along(p0, p1, w, h=None, roll_up=(0, 0, 1)):
    """Matrix mapping the unit cube/cylinder (z -0.5..0.5) onto segment p0->p1, with the
    member's local y kept as close as possible to roll_up."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    z = d / L if L > 1e-9 else Vector((0, 0, 1))
    up = Vector(roll_up)
    if abs(z.dot(up.normalized())) > 0.98:
        up = Vector((1, 0, 0)) if abs(z.x) < 0.9 else Vector((0, 1, 0))
    x = up.cross(z).normalized()
    y = z.cross(x)
    R = Matrix((x, y, z)).transposed()
    M = (R @ Matrix.Diagonal(Vector((w, h if h is not None else w, L)))).to_4x4()
    M.translation = (p0 + p1) / 2
    return M


class Mesh:
    """Accumulates parts into one multi-material mesh. Coordinates pass through the
    current transform (see `at`)."""

    def __init__(self):
        self.v, self.f, self.fm, self.fs = [], [], [], []
        self.mats = []
        self.M = Matrix.Identity(4)

    def slot(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def add(self, verts, faces, mat, M=None, smooth=False):
        M = self.M @ M if M is not None else self.M
        b = len(self.v)
        self.v.extend((M @ Vector(v))[:] for v in verts)
        s = self.slot(mat)
        for f in faces:
            self.f.append(tuple(b + i for i in f))
            self.fm.append(s)
            self.fs.append(smooth)

    @contextmanager
    def at(self, loc=(0, 0, 0), rot=(0, 0, 0), M=None):
        """Nest a local frame: everything added inside is placed by loc/rot (or M)."""
        old = self.M
        self.M = old @ (M if M is not None else xform(loc, rot))
        try:
            yield self
        finally:
            self.M = old

    def merge(self, other, loc=(0, 0, 0), rot=(0, 0, 0)):
        """Append another Mesh's geometry, placed by loc/rot in the current frame."""
        M = self.M @ xform(loc, rot)
        b = len(self.v)
        self.v.extend((M @ Vector(v))[:] for v in other.v)
        remap = [self.slot(m) for m in other.mats]
        for f, fm, s in zip(other.f, other.fm, other.fs):
            self.f.append(tuple(b + i for i in f))
            self.fm.append(remap[fm])
            self.fs.append(s)

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    def obj(self, name, col, parent=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in self.mats:
            me.materials.append(m)
        me.polygons.foreach_set("material_index", self.fm)
        me.polygons.foreach_set("use_smooth", self.fs)
        me.update()
        o = bpy.data.objects.new(name, me)
        (col or bpy.context.scene.collection).objects.link(o)
        o.parent = parent
        return o

    # -- primitives (in the current frame)
    def box(self, size, loc, mat, rot=(0, 0, 0), skip=()):
        self.boxm(xform(loc, rot, size), mat, skip)

    def boxm(self, M, mat, skip=()):
        self.add(_CUBE_V, [f for k, f in _CUBE_F.items() if k not in skip], mat, M)

    def bar(self, p0, p1, w, mat, h=None, caps=False, up=(0, 0, 1)):
        """Rectangular member between two points (open ends: joints hide them)."""
        self.boxm(along(p0, p1, w, h, up), mat, skip=() if caps else ("-z", "+z"))

    def pipe(self, p0, p1, r, mat, n=8, caps=False):
        self.cyl_m(along(p0, p1, 2 * r), mat, n, caps)

    def cyl_m(self, M, mat, n=12, caps=True):
        """Unit cylinder (diameter 1, z -0.5..0.5) through M: smooth sides, flat caps."""
        lo, hi = ring(n, 0.5, -0.5), ring(n, 0.5, 0.5)
        self.add(lo + hi, [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)], mat, M, smooth=True)
        if caps:
            self.add(lo, [tuple(reversed(range(n)))], mat, M)
            self.add(hi, [tuple(range(n))], mat, M)

    def cyl(self, r, depth, loc, mat, rot=(0, 0, 0), n=12, caps=True):
        self.cyl_m(xform(loc, rot, (2 * r, 2 * r, depth)), mat, n, caps)

    def lathe(self, prof, mat, n=16, loc=(0, 0, 0), rot=(0, 0, 0), close=False, smooth=True, arc=None):
        """Revolve profile [(r, z), ...] about local z. arc=(a0, a1) for a partial sweep."""
        full = arc is None
        a0, a1 = arc or (0.0, 2 * math.pi)
        cols = n if full else n + 1
        verts = []
        for k in range(cols):
            a = a0 + (a1 - a0) * k / n
            ca, sa = math.cos(a), math.sin(a)
            verts += [(r * ca, r * sa, z) for r, z in prof]
        m = len(prof)
        faces = []
        for k in range(n):
            k2 = (k + 1) % cols
            for j in range(m - 1):
                faces.append((k * m + j, k2 * m + j, k2 * m + j + 1, k * m + j + 1))
        M = xform(loc, rot)
        self.add(verts, faces, mat, M, smooth=smooth)
        if close and full:
            for j in (0, m - 1):
                if prof[j][0] > 1e-6:
                    rr = ring(n, prof[j][0], prof[j][1])
                    self.add(rr, [tuple(range(n)) if j else tuple(reversed(range(n)))], mat, M)

    def poly(self, pts, mat):
        self.add(pts, [tuple(range(len(pts)))], mat)

    def prism(self, outline, z0, z1, mat, loc=(0, 0, 0), rot=(0, 0, 0)):
        """Extrude outline [(x, y)] (CCW) from z0 to z1, with ngon caps."""
        n = len(outline)
        lo = [(x, y, z0) for x, y in outline]
        hi = [(x, y, z1) for x, y in outline]
        faces = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
        faces += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        self.add(lo + hi, faces, mat, xform(loc, rot))
