"""Geometry for the standalone hydrocyclone explainer: a large cutaway cyclone (shell,
lid, vortex finder, spigot), glass feed duct and overflow pipe, underflow tray, air core,
stand, floor, the four particle clouds, lights and camera."""
from __future__ import annotations

import math

import bpy

from demo import config
from demo.assets import _prims as P
from demo.explainer import model as M
from demo.viz.colors import to_linear

E = config.EXPLAINER
Z0 = E["z0"]
SEG = 56


def _lathe(name, inner, outer, mats, col):
    """Revolve paired inner/outer (r, z) profiles around the z axis, leaving the cutaway
    window (centred on -y) open. mats = (outer, inner, cut-face) materials."""
    cut = math.radians(E["cut_deg"])
    a0 = -math.pi / 2 + cut / 2
    span = 2 * math.pi - cut
    angs = [a0 + span * k / SEG for k in range(SEG + 1)]
    verts, faces, mi = [], [], []
    n = len(inner)

    def vid(ring, k, j):            # ring 0 inner, 1 outer
        return (k * 2 + ring) * n + j

    for a in angs:
        for prof in (inner, outer):
            for r, z in prof:
                verts.append((r * math.cos(a), r * math.sin(a), Z0 + z))
    for k in range(SEG):
        for j in range(n - 1):
            faces.append((vid(1, k, j), vid(1, k + 1, j), vid(1, k + 1, j + 1), vid(1, k, j + 1)))
            mi.append(0)
            faces.append((vid(0, k, j), vid(0, k, j + 1), vid(0, k + 1, j + 1), vid(0, k + 1, j)))
            mi.append(1)
        for j in (0, n - 1):        # end rims
            faces.append((vid(0, k, j), vid(0, k + 1, j), vid(1, k + 1, j), vid(1, k, j)))
            mi.append(2)
    for k in (0, SEG):              # cut faces
        for j in range(n - 1):
            faces.append((vid(0, k, j), vid(1, k, j), vid(1, k, j + 1), vid(0, k, j + 1)))
            mi.append(2)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mi)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    return o


def build(scene):
    col = P.collection("Cyclone")
    w = E["wall"]
    shell = P.material("shell", (0.55, 0.62, 0.66, 1), metallic=0.5, roughness=0.35)
    lining = P.material("lining", (0.30, 0.34, 0.40, 1), roughness=0.6)   # dark: pale slimes stand out
    cutface = P.material("cutface", (0.95, 0.45, 0.10, 1), roughness=0.5)
    glass = P.material("xglass", (0.80, 0.90, 1.0, 0.12), roughness=0.05)
    steel = P.material("steel", metallic=0.6, roughness=0.45)
    mats = (shell, lining, cutface)
    H, C, R, ra = M.TOP, E["cone_h"], E["head_r"], E["apex_r"]
    zs = [C * k / 10 for k in range(11)] + [C + E["head_h"] * k / 4 for k in range(1, 5)]
    inner = [(M.wall_r(z), z) for z in zs]
    _lathe("Shell", inner, [(r + w, z) for r, z in inner], mats, col)
    vf, top = E["vf_r"], E["vf_top"]
    _lathe("Lid", [(vf + w, H), (R, H)], [(vf + w, H + w), (R + w, H + w)], mats, col)
    _lathe("VortexFinder", [(vf, H - E["vf_depth"]), (vf, H + top)],
           [(vf + w, H - E["vf_depth"]), (vf + w, H + top)], mats, col)
    _lathe("Spigot", [(ra, -E["spigot_h"]), (ra, 0.0)], [(ra + 0.07, -E["spigot_h"]), (ra + 0.07, 0.0)],
           (P.material("rubber"), lining, cutface), col)

    ii = E["inlet"]
    zc = Z0 + C + ii["z"]
    P.box("FeedDuct", (ii["len"], ii["w"] + 0.04, ii["h"] + 0.04), (ii["len"] / 2 + 0.6, ii["y"], zc), glass, col)
    P.box("FeedFlange", (0.08, ii["w"] + 0.3, ii["h"] + 0.3), (ii["len"] + 0.6, ii["y"], zc), steel, col)
    P.beam("OverflowPipe", (0.0, 0.0, Z0 + H + top), (-2.8, 0.0, Z0 + H + top), vf + 0.02, glass, col, verts=24)
    P.box("UnderflowTray", (2.4, 2.4, 0.4), (0.0, 0.0, Z0 - E["spigot_h"] - 1.5), steel, col)
    P.box("TrayFloor", (2.2, 2.2, 0.05), (0.0, 0.0, Z0 - E["spigot_h"] - 1.27), P.material("slurry",
          (0.45, 0.20, 0.14, 1), roughness=0.3), col)
    air = P.cylinder("AirCore", 0.09, H + top - (-E["spigot_h"]), (0, 0, Z0 + (H + top - E["spigot_h"]) / 2),
                     P.material("air", (0.75, 0.90, 1.0, 0.35), roughness=0.05), col, verts=16)
    air["base_r"] = 0.09
    P.torus("SupportRing", R + 0.1, 0.07, (0, 0, Z0 + C), P.material("safety"), col, segs=(48, 8))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        if math.sin(a) < 0:            # no legs in front of the cutaway window
            continue
        P.beam(f"Leg{k}", ((R + 1.0) * math.cos(a), (R + 1.0) * math.sin(a), 0.0),
               ((R + 0.15) * math.cos(a), (R + 0.15) * math.sin(a), Z0 + C), 0.08, P.material("safety"), col,
               square=True)
    bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0, 0, 0))
    P._finish(bpy.context.active_object, "Floor", P.material("floor", (0.55, 0.52, 0.48, 1), roughness=0.9),
              col)

    for name, _, _, _, _, n, rad, rgb in E["classes"]:
        P.point_cloud(f"P_{name}", n, P.material(f"m_{name}", to_linear((*rgb, 1.0)), roughness=0.6), rad, col,
                      subdiv=2)

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.55, 0.62, 0.72, 1.0)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (0.9, 0.3, -0.5)
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "AREA"))
    fill.data.energy = 1500.0
    fill.data.size = 6.0
    fill.location = (2.0, -7.0, Z0 + 3.0)
    fill.rotation_euler = (math.radians(75), 0, math.radians(15))
    scene.collection.objects.link(fill)

    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.lens = 24.0
    scene.collection.objects.link(cam)
    cam.location = (-1.2, -13.0, Z0 + 2.8)
    tgt = bpy.data.objects.new("Cam_target", None)
    scene.collection.objects.link(tgt)
    tgt.location = (-1.3, 0.0, Z0 + 1.5)
    con = cam.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    scene.camera = cam
