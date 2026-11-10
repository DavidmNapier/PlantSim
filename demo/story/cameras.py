"""One keyframed camera per chapter, bound to timeline markers so Blender switches
cameras automatically during playback and scrubbing."""
from __future__ import annotations

from demo.story import chapters


def build(scene):
    import bpy
    col = bpy.data.collections.new("Story")
    scene.collection.children.link(col)
    for m in list(scene.timeline_markers):
        scene.timeline_markers.remove(m)
    cams = []
    for i, title, f0, f1, _, _, c in chapters.chapters():
        _, _, _, _, loc0, loc1, tgt0, tgt1 = c
        cam = bpy.data.objects.new(f"Cam_Ch{i}", bpy.data.cameras.new(f"Cam_Ch{i}"))
        cam.data.lens = 28.0
        cam.data.clip_end = 2000.0
        col.objects.link(cam)
        tgt = bpy.data.objects.new(f"Cam_Ch{i}_target", None)
        col.objects.link(tgt)
        for obj, a, b in ((cam, loc0, loc1), (tgt, tgt0, tgt1)):
            obj.location = a
            obj.keyframe_insert("location", frame=f0)
            obj.location = b
            obj.keyframe_insert("location", frame=f1)
        con = cam.constraints.new("TRACK_TO")
        con.target, con.track_axis, con.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
        mk = scene.timeline_markers.new(f"{i}. {title}", frame=f0)
        mk.camera = cam
        cams.append(cam)
    scene.camera = cams[0]
    return cams
