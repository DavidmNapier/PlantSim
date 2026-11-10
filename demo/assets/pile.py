"""Chevron stockpile as one mesh, rebuilt each frame from the yard sim.

Data: chevron layers (one per stacker pass) in each of the pile slices. Each slice's
cross-section is nested similar triangles at the angle of repose.

Display ("both views"):
- surface and reclaim face: 3 horizontal benches (the reclaimer's benches) per slice,
  each bench an area-weighted blend of the chevron layers it cuts through, drawn as
  stacked bands, one per selected metric (top band = first metric);
- the pile ends (before reclaim) and the far end: the chevron layers as V-bands,
  coloured by the first metric.
"""
from __future__ import annotations

import math

from demo import config
from demo.assets import _prims as P
from demo.viz import colors

G = config.YARD_GEOM
NAME = "Pile"
CUT_NAME = "PileCut"
BENCHES = config.BWR_GEOM["benches"]
TAN = math.tan(math.radians(G["repose_deg"]))
_cache = {}
_state = {"key": None, "out": None}
_mesh = {"key": None, "cut": False}
_chunks = {}       # slice -> (signature, verts, faces with local indices, colours): static pile geometry
state_cache = {}   # slice -> [(cum height, half width, cell parcel), ...] for the current frame
cuts = {}          # slice -> fraction reclaimed (the slice the BWR is cutting now)


def build(scene):
    import bpy
    col = P.collection("Stockyard")
    me = bpy.data.meshes.new(NAME)
    o = bpy.data.objects.new(NAME, me)
    col.objects.link(o)
    mat = P.attr_material("pile_heat", attr_type="GEOMETRY", roughness=0.95)
    _add_grain(mat)
    me.materials.append(mat)
    cut = bpy.data.meshes.new(CUT_NAME)            # the block under the wheel, rebuilt every frame
    cut.materials.append(mat)
    col.objects.link(bpy.data.objects.new(CUT_NAME, cut))
    return o


def _add_grain(mat):
    """Multiply the heatmap colour by a noise texture and add bump so it reads as ore."""
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    attr = [n for n in nt.nodes if n.bl_idname == "ShaderNodeAttribute"][0]
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.12
    noise.inputs["Detail"].default_value = 6.0
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.inputs["To Min"].default_value = 0.8
    rng.inputs["To Max"].default_value = 1.05
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    L = nt.links
    L.new(noise.outputs["Fac"], rng.inputs["Value"])
    L.new(attr.outputs["Color"], mix.inputs[6])
    L.new(rng.outputs["Result"], mix.inputs[7])
    L.new(mix.outputs[2], bsdf.inputs["Base Color"])
    L.new(noise.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


# ------------------------------------------------------------------ data
def invalidate():
    """Drop cached pile data and meshes (call after the yard sim is recomputed)."""
    _cache.clear()
    _state.update(key=None, out=None)
    _mesh.update(key=None)
    _chunks.clear()


def _cells(yard):
    """{(k, j): ([(laid, t), ...] sorted, blended parcel)} cached per yard result."""
    key = id(yard)
    if _cache.get("key") != key:
        from demo.sim.parcel import blend
        cells = {}
        for (k, j), ps in yard.pile.cells.items():
            laid = sorted((p.stamps.get("laid", 0.0), p.dry_t) for p in ps)
            cells[(k, j)] = (laid, blend(ps, "cell", 0.0))
        rate = config.STOCKPILE["reclaim_tph"] / 60.0
        removed = {j: (m, m + p.dry_t / rate) for m, j, p in yard.reclaimed}
        K = config.BWR_GEOM["block_slices"]
        for j in list(removed):          # the wheel takes K slices per bench pass: shared window
            blk = [removed[i] for i in range(j - j % K, j - j % K + K) if i in removed]
            removed[j] = (min(a for a, _ in blk), max(b for _, b in blk))
        laid_all = sorted(laid for laid_t, _ in cells.values() for laid, _t in laid_t)
        _cache.update(key=key, cells=cells, removed=removed, layers=yard.pile.layers, laid_all=laid_all,
                      starts=sorted(a for a, _ in removed.values()), ends=sorted(b for _, b in removed.values()))
    return _cache


def section(tonnes: float):
    """(height, half-width) of a repose-angle triangle holding `tonnes` over one slice."""
    dx = G["length"] / config.STOCKPILE["slices"]
    area = tonnes * G["vis_scale"] / (G["bulk_density"] * dx)
    h = math.sqrt(area * TAN)
    return h, h / TAN


def state(yard, minute: float):
    """Per slice: [(cum height, half width, cell parcel)] per present layer; [] if empty/gone."""
    import bisect
    c = _cells(yard)
    cuts.clear()
    if bisect.bisect_right(c["starts"], minute) > bisect.bisect_right(c["ends"], minute):
        for j, (t0, t1) in c["removed"].items():
            if t0 <= minute < t1:
                cuts[j] = (minute - t0) / (t1 - t0)
    key = (c["key"], bisect.bisect_right(c["laid_all"], minute), bisect.bisect_right(c["starts"], minute),
           bisect.bisect_right(c["ends"], minute))
    if _state["key"] == key:
        return _state["out"]
    out = []
    for j in range(config.STOCKPILE["slices"]):
        t0, t1 = c["removed"].get(j, (1e9, 1e9))
        layers, cum = [], 0.0
        if t1 > minute:
            for k in range(c["layers"]):
                cell = c["cells"].get((k, j))
                if not cell:
                    continue
                t = sum(tt for laid, tt in cell[0] if laid <= minute)
                if t <= 0:
                    continue
                cum += t
                h, hw = section(cum)
                layers.append((h, hw, cell[1]))
        out.append(layers)
    _state.update(key=key, out=out)
    return out


def _tri_area(H, a, b):
    """Cross-section area of a repose triangle of height H between heights a and b."""
    a, b = min(max(a, 0.0), H), min(max(b, 0.0), H)
    if b <= a or H <= 0:
        return 0.0
    return 2.0 * (H / TAN) * ((b - a) - (b * b - a * a) / (2.0 * H))


def bench_values(layers, metrics):
    """[[value per metric] per bench, top bench first]: area-weighted blend of layers."""
    H = layers[-1][0]
    out = []
    for b in range(BENCHES):
        lo, hi = H * (BENCHES - 1 - b) / BENCHES, H * (BENCHES - b) / BENCHES
        wsum, acc, prev = 0.0, [0.0] * len(metrics), 0.0
        for h, _, p in layers:
            w = _tri_area(h, lo, hi) - _tri_area(prev, lo, hi)
            prev = h
            if w <= 0:
                continue
            wsum += w
            for i, m in enumerate(metrics):
                acc[i] += w * colors.metric_value(p, m)
        out.append([a / wsum for a in acc] if wsum else [0.0] * len(metrics))
    return out


def reclaim_front(yard, minute):
    """(slice, fraction cut, crest height, half width) of the active cut, or None."""
    for j, f in cuts.items():
        s = state_cache.get(j)
        if s:
            return j, f, s[-1][0], s[-1][1]
    return None


def bench_cut(blk, frac, h, hw):
    """Where the bucket wheel is in cut block `blk` (config block_slices slices),
    fraction `frac` cut, crest h, half width hw.

    The slice is taken top bench first. Each bench starts with a short reposition
    (config BWR_GEOM["ease"]): the wheel luffs down and moves across from where the last
    bench ended. Then it slews across the bench once, and material on the side it has
    passed is gone. Slew direction alternates bench by bench, so each bench starts where
    the previous one ended.
    Returns dict: bench, v (0..1 through the bench), sweep (0..1 slew progress),
    sgn (+1 = slewing from +y to -y), y (cut boundary = wheel lateral position),
    w (bench half width at its base)."""
    e = config.BWR_GEOM["ease"]
    u = min(BENCHES - 1e-9, max(0.0, frac * BENCHES))
    b = int(u)
    v = u - b
    sweep = min(1.0, max(0.0, (v - e) / (1.0 - e)))
    g = blk * BENCHES + b
    sgn = 1 if g % 2 == 0 else -1
    w = hw * (1.0 - (BENCHES - 1 - b) / BENCHES)
    return {"bench": b, "v": v, "sweep": sweep, "sgn": sgn, "w": w,
            "y": sgn * (w + 0.5) * math.cos(math.pi * sweep)}


def height_at(yard, minute, x):
    """Pile crest height at world x (for the stacker boom and BWR)."""
    n = config.STOCKPILE["slices"]
    j = int((x - G["x0"]) / G["length"] * n)
    if not 0 <= j < n:
        return 0.0
    s = state_cache.get(j)
    return s[-1][0] if s else 0.0


# ------------------------------------------------------------------ mesh
def update(scene, yard, minute: float, metrics, heat: bool):
    import bpy
    if isinstance(metrics, str):
        metrics = [metrics]
    st = state(yard, minute)
    state_cache.clear()
    state_cache.update(enumerate(st))
    key = (_state["key"], tuple(metrics), bool(heat))
    if _mesh["key"] != key:
        _write(bpy.data.objects[NAME].data, *_geometry(st, metrics, heat, active=False))
        _mesh["key"] = key
    cut = bpy.data.objects.get(CUT_NAME)
    if cut is not None and (cuts or _mesh["cut"]):
        _write(cut.data, *_geometry(st, metrics, heat, active=True))
        _mesh["cut"] = bool(cuts)


def _write(me, verts, faces, cols):
    me.clear_geometry()
    me.from_pydata(verts, [], faces)
    if "col" not in me.attributes:
        me.attributes.new("col", "FLOAT_COLOR", "FACE")
    flat = [v for c in cols for v in c]
    if flat:
        me.attributes["col"].data.foreach_set("color", flat)
    me.update()


def _geometry(st, metrics, heat, active):
    """(verts, faces, colours) for the slices not being cut (active=False) or for the
    block under the wheel (active=True)."""
    n = len(st)
    dx = G["length"] / n
    plain = colors.to_linear(config.COLORS["ore"])
    nm = len(metrics)
    verts, faces, cols = [], [], []

    def rgba(metric, v):
        return colors.to_linear(colors.rgba(metric, v)) if heat else plain

    def quad(a, b, c, d, col):
        i = len(verts)
        verts.extend((a, b, c, d))
        faces.append((i, i + 1, i + 2, i + 3))
        cols.append(col)

    def bound(b):
        """Crest height and half width at slice boundary b (average of present neighbours)."""
        hs = [st[j][-1][:2] for j in (b - 1, b) if 0 <= j < n and st[j]]
        if not hs:
            return None
        return sum(h for h, _ in hs) / len(hs), sum(w for _, w in hs) / len(hs)

    def chevron_face(x, layers, flip):
        prev_h = prev_w = 0.0
        for h, w, p in layers:
            col = rgba(metrics[0], colors.metric_value(p, metrics[0]))
            for s in (-1, 1):
                q = [(x, s * prev_w, 0.0), (x, s * w, 0.0), (x, 0.0, h), (x, 0.0, prev_h)]
                if (s > 0) != flip:
                    q.reverse()
                quad(*q, col)
            prev_h, prev_w = h, w

    def bands_t(b, k):
        """(t_lo, t_hi) height fractions of metric band k within bench b (top bench first)."""
        t_hi = (BENCHES - b) / BENCHES - k / (BENCHES * nm)
        return t_hi - 1.0 / (BENCHES * nm), t_hi

    def bench_face(x, layers, vals):
        """Reclaim face: horizontal bench bands across the triangle (facing -x)."""
        H, W = layers[-1][0], layers[-1][1]
        for b in range(BENCHES):
            for k, m in enumerate(metrics):
                t_lo, t_hi = bands_t(b, k)
                w_lo, w_hi = W * (1 - t_lo), W * (1 - t_hi)
                quad((x, w_lo, t_lo * H), (x, -w_lo, t_lo * H), (x, -w_hi, t_hi * H), (x, w_hi, t_hi * H),
                     rgba(m, vals[b][k]))

    def poly(pts, col):
        if len(pts) < 3:
            return
        i = len(verts)
        verts.extend(pts)
        faces.append(tuple(range(i, i + len(pts))))
        cols.append(col)

    def clip(pts, keep):
        """Clip a (y, z) polygon to keep(y) in {'all', ('lt', yc), ('gt', yc)} (one line)."""
        if keep == "all":
            return pts
        side, yc = keep
        inside = (lambda p: p[0] <= yc) if side == "lt" else (lambda p: p[0] >= yc)
        out = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            ia, ib = inside(a), inside(b)
            if ia:
                out.append(a)
            if ia != ib:
                t = (yc - a[0]) / (b[0] - a[0])
                out.append((yc, a[1] + t * (b[1] - a[1])))
        return out

    def band_face(x, H, W, b, k, col, keep="all"):
        t_lo, t_hi = bands_t(b, k)
        w_lo, w_hi = W * (1 - t_lo), W * (1 - t_hi)
        yz = clip([(w_lo, t_lo * H), (-w_lo, t_lo * H), (-w_hi, t_hi * H), (w_hi, t_hi * H)], keep)
        poly([(x, y, z) for y, z in yz], col)

    K = config.BWR_GEOM["block_slices"]
    first = min(cuts) if cuts else None

    def active_slice(j, x0, x1, vals, vals_next):
        """Slice in the block under the bucket wheel: benches above the wheel are gone, the
        bench being cut is gone on the side the wheel has slewed past, the rest is intact.
        Faces are drawn only at the block's front (x0) and back (x1)."""
        H, W = st[j][-1][0], st[j][-1][1]
        h1, w1 = bound(j + 1) if bound(j + 1) else (H, W)
        lead = st[first][-1]
        c = bench_cut(first // K, cuts[j], lead[0], lead[1])
        is_front, is_back = j == first, not (j + 1 in cuts)
        if not is_back:
            vals_next = None
        cb, yc, sgn = c["bench"], c["y"], c["sgn"]
        cut_side = ("gt", yc) if sgn > 0 else ("lt", yc)
        keep_side = ("lt", yc) if sgn > 0 else ("gt", yc)

        def is_cut(b, y):
            return b < cb or (b == cb and (y - yc) * sgn > 0)
        for b in range(BENCHES):
            for k, m in enumerate(metrics):
                t_lo, t_hi = bands_t(b, k)
                col = rgba(m, vals[b][k])
                for s in (-1, 1):                         # slope strips still in place
                    if is_cut(b, s * W * (1 - (t_lo + t_hi) / 2)):
                        continue
                    q = [(x0, s * W * (1 - t_lo), H * t_lo), (x1, s * w1 * (1 - t_lo), h1 * t_lo),
                         (x1, s * w1 * (1 - t_hi), h1 * t_hi), (x0, s * W * (1 - t_hi), H * t_hi)]
                    if s > 0:
                        q.reverse()
                    quad(*q, col)
                nxt = rgba(m, (vals_next or vals)[b][k])
                if b > cb:                                # intact benches: face at the block front
                    if is_front:
                        band_face(x0, H, W, b, k, col)
                elif b < cb:                              # removed benches: next slice shows behind
                    if is_back:
                        band_face(x1, h1, w1, b, k, nxt)
                else:
                    if is_front:
                        band_face(x0, H, W, b, k, col, keep_side)
                    if is_back:
                        band_face(x1, h1, w1, b, k, nxt, cut_side)
                    z_top = H * (1 - abs(yc) / W) if W > 0 else 0.0     # wall along the cut line
                    za, zb = t_lo * H, min(t_hi * H, z_top)
                    if zb > za:
                        quad((x0, yc, za), (x1, yc, za), (x1, yc, zb), (x0, yc, zb), col)
        # flat treads: top of the bench being cut (uncut side) and floor of the cut side
        for b, keep in ((cb, keep_side), (cb + 1, cut_side)):
            if b == 0 or b >= BENCHES:
                continue
            t = (BENCHES - b) / BENCHES
            wt = W * (1 - t)
            yz = clip([(wt, 0.0), (-wt, 0.0), (-wt, 1.0), (wt, 1.0)], keep)
            ys = [y for y, _ in yz]
            if len(ys) >= 2 and max(ys) - min(ys) > 1e-3:
                ya, yb = min(ys), max(ys)
                quad((x0, ya, t * H), (x1, ya, t * H), (x1, yb, t * H), (x0, yb, t * H), rgba(metrics[0], vals[b][0]))

    for j in range(n):
        if not st[j] or (j in cuts) != active:
            continue
        x0 = G["x0"] + j * dx
        x1 = G["x0"] + (j + 1) * dx
        if j in cuts:
            vals = bench_values(st[j], metrics)
            nxt = bench_values(st[j + 1], metrics) if j + 1 < n and st[j + 1] else None
            active_slice(j, x0, x1, vals, nxt)
            if j == n - 1 or not st[j + 1]:
                chevron_face(x1, st[j], flip=True)
            continue
        (h0, w0), (h1, w1) = bound(j), bound(j + 1)
        front, back = j == 0 or not st[j - 1], j == n - 1 or not st[j + 1]
        sig = (tuple(metrics), heat, tuple((h, w, id(p)) for h, w, p in st[j]), h0, w0, h1, w1, front, back)
        hit = _chunks.get(j)
        if hit is not None and hit[0] == sig:     # unchanged slice: reuse its geometry
            o = len(verts)
            verts.extend(hit[1])
            faces.extend((a + o, b + o, c + o, d + o) for a, b, c, d in hit[2])
            cols.extend(hit[3])
            continue
        v0, f0 = len(verts), len(faces)
        vals = bench_values(st[j], metrics)
        for b in range(BENCHES):                 # surface: per bench, one band per metric up each slope
            for k, m in enumerate(metrics):
                t_lo, t_hi = bands_t(b, k)
                col = rgba(m, vals[b][k])
                for s in (-1, 1):
                    q = [(x0, s * w0 * (1 - t_lo), h0 * t_lo), (x1, s * w1 * (1 - t_lo), h1 * t_lo),
                         (x1, s * w1 * (1 - t_hi), h1 * t_hi), (x0, s * w0 * (1 - t_hi), h0 * t_hi)]
                    if s > 0:
                        q.reverse()
                    quad(*q, col)
        if j == 0 or not st[j - 1]:              # front: reclaim face (benches) or pile end (chevron)
            if j in cuts or j > 0:
                bench_face(x0, st[j], vals)
            else:
                chevron_face(x0, st[j], flip=False)
        if j == n - 1 or not st[j + 1]:
            chevron_face(x1, st[j], flip=True)
        _chunks[j] = (sig, verts[v0:], [tuple(i - v0 for i in f) for f in faces[f0:]], cols[f0:])

    return verts, faces, cols
