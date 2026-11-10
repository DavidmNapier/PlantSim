"""Every tunable number for the demo. Units: metres, tonnes, minutes, %."""

SEED = 42

# --- Quality fields carried by every parcel (dry-mass weighted when blended) ---
ANALYTES = ("Fe", "SiO2", "Al2O3", "P", "LOI")
# Blended by dry tonnes as well. fault_frac = share of mass made under a cyclone fault.
BLEND_FIELDS = ANALYTES + ("lump_frac", "p80_mm", "fault_frac")

TARGETS = {"Fe": 61.0, "SiO2": 4.5, "Al2O3": 2.3, "P": 0.08, "LOI": 5.0, "moisture": 8.5}
ALERT_TOL = {"Al2O3": 0.4, "SiO2": 0.5, "yield": 0.05}   # deviation that raises an alert

# --- Simulated ore source (blast blocks feeding the crusher) ---
SOURCE = {
    "parcel_t": 25.0,           # dry tonnes per parcel (one every 30 s): short tonnage segments
    "rate_tph": 3000.0,         # plant feed rate, dry t/h
    "moisture": 6.0,            # ROM moisture %
    "block_t": 20000.0,         # tonnes per blast block before grade shifts
    "grade_mean": {"Fe": 59.5, "SiO2": 5.6, "Al2O3": 3.2, "P": 0.085, "LOI": 5.4},
    "grade_sd":   {"Fe": 0.8,  "SiO2": 0.5, "Al2O3": 0.3, "P": 0.005, "LOI": 0.3},
    "lump_frac": 0.35,
    "p80_mm": 10.0,             # whole-stream size index (dry-weighted)
}

# --- Screens: lump (+6.3 mm) / fines split ---
SCREEN = {"cut_mm": 6.3, "fines_p80_mm": 3.5}

# --- Horizontal vacuum belt filter: underflow slurry -> filter cake ---
FILTER = {"cake_moisture": 8.5, "uf_ref": 30.0, "k": 0.25}   # cake = 8.5 + 0.25*(uf - 30)

# --- Desliming cyclones ---
CYCLONE = {
    "count": 5,
    "hero": 2,                  # index of the hero cyclone (0-based)
    "apex_mm": 90.0,            # nominal apex diameter
    "feed_solids_pct": 35.0,    # nominal feed solids, % w/w
    "pressure_kpa": 120.0,      # nominal feed pressure
    # Yield sensitivity to settings (per unit deviation from nominal)
    "dY_apex_per_mm": 0.0015,
    "dY_solids_per_pct": -0.002,
    "dY_pressure_per_kpa": 0.0004,
    "pulse_period_min": 6.0,    # pulsing swing period
    # Per-condition behaviour. ratio = product grade / feed grade.
    "conditions": {
        "NORMAL":  {"yield": 0.88, "yield_amp": 0.0,  "moist_delta": 0.0,
                    "ratio": {"Fe": 1.025, "SiO2": 0.80, "Al2O3": 0.70, "P": 0.95, "LOI": 0.93}},
        "ROPING":  {"yield": 0.78, "yield_amp": 0.0,  "moist_delta": -0.4,
                    "ratio": {"Fe": 1.020, "SiO2": 0.82, "Al2O3": 0.72, "P": 0.96, "LOI": 0.94}},
        "PULSING": {"yield": 0.91, "yield_amp": 0.04, "moist_delta": 1.0,
                    "ratio": {"Fe": 1.005, "SiO2": 0.97, "Al2O3": 0.93, "P": 0.99, "LOI": 0.98}},
    },
    "uf_moisture": 30.0,        # underflow slurry moisture % (70% solids); + 4x moist_delta
    "slimes_moisture": 85.0,    # overflow slurry to the thickener
}

# --- Default fault scenario for the storyline (minutes from start) ---
FAULT_SCHEDULE = [
    # (start_min, end_min, cyclone_index, condition)
    (30.0, 45.0, 2, "ROPING"),
    (62.0, 70.0, 2, "PULSING"),     # ~half a stacker pass -> localised in the pile
]
SIM_MINUTES = 120.0                 # ~3.4 kt product = one 28-wagon train

# ======================= Geometry (metres) =======================
COLORS = {
    "steel": (0.55, 0.58, 0.62, 1), "steel_dark": (0.25, 0.27, 0.30, 1),
    "safety": (0.95, 0.70, 0.05, 1), "rubber": (0.06, 0.06, 0.07, 1),
    "cyclone": (0.80, 0.82, 0.85, 1), "pipe": (0.20, 0.35, 0.55, 1),
    "glass": (0.75, 0.85, 0.95, 0.22),
    "ore": (0.42, 0.16, 0.08, 1), "slimes": (0.85, 0.62, 0.30, 1),
    "ground": (0.45, 0.28, 0.18, 1),
}

# Pilbara look: material defaults used by _prims.material(name) when no args override them.
# dust = red-dust weathering strength on lower surfaces; ribs = profiled-sheeting bump.
MATERIALS = {
    "steel": {"rgba": (0.60, 0.62, 0.64, 1), "metallic": 0.6, "roughness": 0.45, "dust": 0.6},
    "galv": {"rgba": (0.66, 0.68, 0.69, 1), "metallic": 0.7, "roughness": 0.5, "dust": 0.8},
    "steel_dark": {"rgba": (0.25, 0.27, 0.30, 1), "metallic": 0.5, "roughness": 0.5, "dust": 0.5},
    "safety": {"rgba": (0.95, 0.70, 0.05, 1), "roughness": 0.5, "dust": 0.7},
    "grating": {"rgba": (0.40, 0.41, 0.40, 1), "metallic": 0.5, "roughness": 0.7, "dust": 0.9},
    "concrete": {"rgba": (0.62, 0.60, 0.56, 1), "roughness": 0.9, "dust": 1.0},
    "clad": {"rgba": (0.80, 0.81, 0.78, 1), "metallic": 0.3, "roughness": 0.45, "dust": 0.8, "ribs": "wall"},
    "clad_green": {"rgba": (0.42, 0.50, 0.42, 1), "roughness": 0.55, "dust": 0.8, "ribs": "wall"},
    "roof": {"rgba": (0.74, 0.76, 0.76, 1), "metallic": 0.5, "roughness": 0.4, "dust": 0.3, "ribs": "roof"},
    "roller_door": {"rgba": (0.86, 0.86, 0.84, 1), "roughness": 0.5, "dust": 0.8, "ribs": "door"},
    "trim": {"rgba": (0.20, 0.33, 0.30, 1), "roughness": 0.5, "dust": 0.5},
    "rubber": {"rgba": (0.06, 0.06, 0.07, 1), "roughness": 0.9},
    "pipe": {"rgba": (0.20, 0.35, 0.55, 1), "metallic": 0.3, "roughness": 0.4, "dust": 0.5},
    "hdpe": {"rgba": (0.08, 0.08, 0.09, 1), "roughness": 0.6, "dust": 0.6},
    "cyclone": {"rgba": (0.78, 0.80, 0.82, 1), "roughness": 0.4, "dust": 0.3},   # neutral: the KPI ramp owns red/green
    "window": {"rgba": (0.10, 0.14, 0.18, 1), "metallic": 0.2, "roughness": 0.1},
    "wagon": {"rgba": (0.62, 0.62, 0.60, 1), "metallic": 0.6, "roughness": 0.5, "dust": 1.0},   # alloy ore car
    "loco_body": {"rgba": (0.62, 0.20, 0.08, 1), "metallic": 0.2, "roughness": 0.45, "dust": 0.8},
    "loco_cream": {"rgba": (0.88, 0.85, 0.76, 1), "roughness": 0.45, "dust": 0.6},
    "loco_dark": {"rgba": (0.10, 0.10, 0.11, 1), "metallic": 0.4, "roughness": 0.5, "dust": 0.8},
    "truck_yellow": {"rgba": (0.93, 0.68, 0.06, 1), "roughness": 0.5, "dust": 1.0},
    "tyre": {"rgba": (0.05, 0.05, 0.05, 1), "roughness": 0.9, "dust": 1.0},
    "counterweight": {"rgba": (0.50, 0.50, 0.48, 1), "roughness": 0.8, "dust": 0.6},
    "machinery": {"rgba": (0.25, 0.40, 0.55, 1), "metallic": 0.3, "roughness": 0.5, "dust": 0.6},
}
LOOK = {"dust": True, "ribs": True, "dust_noise": True}   # shader features (perf switches)
DUST = {
    "rgba": (0.50, 0.20, 0.08, 1),   # linear red-brown Pilbara dust
    "height": 3.0,                   # full dust at z = 0, none above this (m)
    "noise_scale": 0.6, "film": 0.12,
    "rib_pitch": 0.25, "door_pitch": 0.12,
}
STEEL = {    # structural kit (_steel.py)
    "rail_h": 1.1, "mid_h": 0.55, "post_pitch": 2.0, "kick_h": 0.12,
    "rail_w": 0.05, "post_w": 0.06, "deck_t": 0.05,
    "stair_rise": 0.2, "stair_going": 0.25, "stair_w": 0.9,
}
CONVEYOR = {   # belt structure detail (belt.py)
    "trough_deg": 35.0, "roll_r": 0.07, "walkway_w": 0.9,
    "gallery_min_z": 3.0,      # belts higher than this get a truss gallery on trestles
    "truss_depth": 1.6, "trestle_pitch": 18.0, "hoop_every": 4,
}

CYCLONE_GEOM = {
    "ring_r": 1.4,          # cyclone centres on this radius around the manifold
    "head_r": 0.32, "head_h": 0.5, "head_z": 5.0,   # head bottom at head_z
    "cone_h": 1.6, "apex_r": 0.06, "spigot_h": 0.15,
    "vf_r": 0.10, "vf_h": 0.6,                     # vortex finder up into overflow launder
    "manifold_r": 0.45, "manifold_z": (4.6, 5.8),
    "of_launder_z": 6.3, "uf_launder_z": 2.6, "uf_launder_r": 0.25,
    "leg_xy": 1.9, "frame_half": 2.4,     # 4-column support frame half-width
}

HERO = {
    "n_coarse": 280, "n_slimes": 200,      # <= 500 particles total
    "radius": 0.022, "laps": 4.0,          # spiral turns from head to apex
    "cycle_s": 3.0,                        # seconds for one particle trip
    # share of each material that goes the "wrong" way, per condition
    "coarse_to_of": {"NORMAL": 0.03, "ROPING": 0.40, "PULSING": 0.06},
    "slimes_to_uf": {"NORMAL": 0.03, "ROPING": 0.02, "PULSING": 0.60},
    "spray_r": {"NORMAL": 0.45, "ROPING": 0.02, "PULSING": 0.30},
}

BELT = {     # product belt: belt filter discharge -> transfer to the stockyard
    "start": (17.5, 0.0, 2.0), "end": (31.0, 0.0, 4.2),
    "width": 1.0, "idler_pitch": 1.5, "speed_mps": 3.0,
    "n_lumps": 160, "lump_r": 0.07,
}

# ======================= Playback / display =======================
PLAYBACK = {
    "sim_min_per_s": 2.0,      # sim minutes per second of animation
    "belt_lag_min": 10.0,      # sim minutes of product represented along the belt
    "product_off_min": 3.0,    # cyclone -> pipe -> belt filter before the product belt
    "tags_on_belt": 4,         # floating parcel tags shown at once
    "overlay_scale": 0.8,      # KPI panel / tag size relative to Blender UI scale
}

# metric key -> (label, unit, lo, hi, higher_is_better). lo..hi spans the colour ramp.
METRICS = {
    "tonnes":   ("Product rate", "t/h", 1650.0, 1730.0, True),
    "Fe":       ("Fe", "%", 60.4, 61.2, True),
    "SiO2":     ("SiO2", "%", 4.3, 4.75, False),
    "Al2O3":    ("Al2O3", "%", 2.15, 2.45, False),
    "P":        ("P", "%", 0.06, 0.10, False),
    "LOI":      ("LOI", "%", 4.5, 6.0, False),
    "moisture": ("Moisture", "%", 8.3, 8.9, False),
    "size":     ("P80", "mm", 2.5, 5.0, False),
}
RAMP = ((0.15, 0.70, 0.25), (0.98, 0.82, 0.15), (0.90, 0.15, 0.10))   # sRGB: good -> mid -> bad

LABELS = {   # 3D labels drawn by the overlay
    "ROM bin + primary crusher": (-130.0, 0.0, 16.0),
    "TP1 crusher discharge": (-100.0, 0.0, 9.0),
    "Scrubber": (-64.0, 0.0, 9.0),
    "Screens": (-50.0, 0.0, 9.0),
    "Desliming cyclones": (0.0, 0.0, 7.0),
    "Belt filter": (11.0, 0.0, 7.5),
    "TP2 product": (24.0, 0.0, 8.0),
    "Thickener": (-18.0, 22.0, 6.0),
    "Chevron stockpile": (90.0, 0.0, 16.0),
    "Bucket wheel reclaimer": (60.0, 26.0, 14.0),
    "TP3 weighbridge": (175.0, 60.0, 19.0),
}

# Chapter-3 presenter camera: (location, target)
CAM_CH3 = ((15.0, -21.0, 8.0), (5.5, 0.0, 6.0))

# ======================= Stockyard and load-out (sim) =======================
STOCKPILE = {
    "pass_min": 15.0,          # stacker time for one pass along the pile (one chevron layer)
    "slices": 160,             # reclaim slices along the pile length (0.625 m each)
    "reclaim_tph": 6000.0,     # BWR rate
    "reclaim_start_min": 125.0,
}
TRAIN = {
    "wagons": 28,
    "payload_t": 120.0,        # dry tonnes per wagon
    "flag_fault_frac": 0.005,  # flag a wagon if >0.5% of its mass passed a faulty cyclone
    "flag_conditions": ("PULSING",),   # quality faults (roping loses tonnes, not grade)
}

YARD_GEOM = {
    "x0": 40.0, "length": 100.0,       # pile runs along +x from x0, centreline y = 0
    "repose_deg": 37.0, "bulk_density": 2.2,
    "vis_scale": 15.0,                 # pile drawn at 15x real volume (3.4 kt is tiny); numbers stay true
    "rail_y": -26.0, "yard_belt_y": -30.0, "yard_belt_z": 1.6,
    "boom_len": 28.0, "boom_pivot_h": 7.5, "drop_h": 2.0, "cw_len": 7.0,
    "tripper_len": 16.0, "tripper_head_z": 8.9,   # tripper car lifts the yard belt to the boom feed chute
    "tail_back": 21.5,                 # yard belt tail (and its transfer tower) this far west of x0
    "stream_n": 40,
}
TIMELINE_END_MIN = 170.0               # stacking 0-120, reclaim from 125, load-out after

BWR_GEOM = {
    "rail_y": 26.0, "pivot_h": 9.0, "boom_len": 45.0, "cw_len": 16.0,
    "wheel_r": 4.0, "buckets": 10, "wheel_rps": 0.5,
    "benches": 3,                     # passes down the face per slice
    "ease": 0.15,                     # share of each bench spent luffing / repositioning before the slew
    "face_frac": 0.6,                 # wheel centre x within the block being cut (then 0.4 r toward the face)
    "block_slices": 4,                # visual cut block: the wheel takes 4 slices (2.5 m) per bench pass
}

LOADOUT_GEOM = {
    "chute_x": 175.0, "track_y": 60.0,
    "bin_w": 8.0, "bin_z": (10.0, 16.0), "hopper_z": 6.5, "chute_z": 5.0,
    "belt_start": (128.0, 34.0, 1.5), "belt_end": (175.0, 57.5, 16.5),
    "wagon_len": 10.5, "wagon_w": 3.2, "wagon_h": 2.4, "deck_z": 1.2, "spacing": 12.0,
    "loco_len": 20.0,
    "sleeper_x": (60.0, 260.0),        # concrete sleepers drawn only where cameras get close
}

# ======================= Upstream plant (low detail) =======================
UPSTREAM = {
    "crusher_xy": (-130.0, 0.0), "rom_h": 13.0,          # ROM bin top height
    "crusher_belt": ((-121.0, 0.0, 1.5), (-73.0, 0.0, 7.2)),
    "scrubber_xy": (-64.0, 0.0), "scrubber_z": 5.0, "scrubber_r": 2.2, "scrubber_len": 10.0,
    "scrubber_rpm": 12.0,
    "screen_xy": (-50.0, 0.0), "screen_z": 4.0, "screen_len": 7.0, "screen_w": 3.0, "screen_deg": 15.0,
    "screen_hz": 3.0,
    "tp1_x": -100.0, "tp2_x": 24.0, "tp3_x": 175.0,      # tracking points (on belts / weighbridge)
    "rom_pad": (24.0, 22.0),                             # ROM pad length (x) and width at crusher level
    "ramp_len": 70.0,                                    # haul ramp up to the pad (~11%)
}

# Transfer towers at belt junctions: name -> (x, y, top floor z, w, d, clad head house, stair side)
TRANSFER_TOWERS = {
    "TT1_crusher_head": (-74.0, 0.0, 7.0, 5.0, 5.0, True, "-y"),
    "TT2_product_head": (32.5, 0.0, 4.0, 4.5, 4.5, True, "+y"),
    "TT3_yard_tail": (19.5, -30.0, 2.8, 4.0, 4.0, True, "-y"),
    "TT4_reclaim_head": (127.0, 34.0, 2.6, 4.5, 4.5, False, "+y"),   # open frame: BWR counterweight swings above
}
# Site buildings: (x, y, size x, size y, eave height); tanks (x, y, r, h); light tower (x, y)
SITE = {
    "workshop": (-20.0, -68.0, 32.0, 20.0, 10.0),
    "admin": (20.0, -64.0, 16.0, 10.0, 3.6),
    "control": (-14.0, -12.0, 10.0, 6.0, 3.6),
    "substation": (-80.0, -18.0, 8.0, 6.0, 3.5),
    "tanks": [(-42.0, 20.0, 4.0, 7.0), (-42.0, 31.0, 4.0, 7.0)],   # behind the thickener, out of the ch3 shot
    "light_towers": [(-150.0, -14.0), (-60.0, 14.0), (200.0, 42.0)],   # kept out of the chapter camera lines
}

# Haul trucks (~220 t rigid, generic). (x, y, z, yaw, pitch, tray raised)
TRUCK_GEOM = {"wheel_r": 1.8, "front_axle": 3.0, "rear_axle": -2.9, "hinge_x": -4.4, "hinge_z": 2.6,
              "tray_front": 2.6, "tray_w": 6.6, "tray_h": 2.2, "canopy": 3.8, "dump_deg": 45.0}
TRUCKS = [
    (-145.6, 0.0, 8.0, 3.14159, 0.0, True),            # reversed up to the dump pocket, dumping
    (-157.0, -6.0, 8.0, 2.6, 0.0, False),              # queued on the pad
    (-205.0, 3.5, 3.2, 3.14159, 0.114, False),         # empty, heading down the ramp
]

# ======================= Storyline (7 chapters) =======================
# (title, seconds, sim minute start, sim minute end,
#  camera loc start, loc end, target start, target end)
STORY = [
    ("Plant overview", 30, 0.0, 10.0,
     (-160.0, -220.0, 140.0), (200.0, -210.0, 120.0), (20.0, 0.0, 0.0), (40.0, 0.0, 0.0)),
    ("Parcels are born", 45, 10.0, 30.0,
     (-112.0, -26.0, 14.0), (-88.0, -24.0, 13.0), (-118.0, 0.0, 4.0), (-96.0, 0.0, 5.0)),
    ("Wet plant and cyclones (live)", 90, 50.0, 75.0,
     (15.0, -21.0, 8.0), (16.5, -21.5, 8.5), (5.5, 0.0, 6.0), (6.5, 0.0, 6.0)),
    ("Stacking the chevron pile", 60, 75.0, 120.0,
     (40.0, -75.0, 30.0), (125.0, -70.0, 32.0), (70.0, 0.0, 5.0), (110.0, 0.0, 5.0)),
    # slow, close digging: ~25 s per bench pass on a 2.5 m block; ch6 picks up at minute 142
    # end-on from high in the west, looking at the stepped face; aimed right of and above the face
    # so it sits in the clear area left of the sidebar and below the KPI panel
    ("Reclaiming", 120, 124.85, 126.2,
     (2.0, -16.0, 44.0), (6.0, -14.0, 40.0), (44.0, -9.0, 13.0), (46.0, -9.0, 12.0)),
    ("Train load-out", 60, 142.0, 160.0,
     (150.0, 25.0, 22.0), (105.0, 30.0, 24.0), (170.0, 60.0, 4.0), (115.0, 60.0, 3.0)),
    ("Close: every wagon traced", 30, 160.0, 170.0,
     (60.0, -150.0, 90.0), (-40.0, -240.0, 160.0), (40.0, 10.0, 0.0), (40.0, 10.0, 0.0)),
]
STORY_FPS = 24

# ======================= Slurry pipes and belt filter =======================
# Glass pipes: slurry segments are drawn inside them. Polylines in world metres.
PIPES = {
    "FeedSlurry": {"r": 0.45, "pts": [(-46.0, 0.0, 0.8), (-46.0, -4.5, 0.8), (0.0, -4.5, 0.8),
                                      (0.0, 0.0, 0.8), (0.0, 0.0, 4.6)]},
    "Underflow": {"r": 0.35, "pts": [(1.65, 0.0, 2.4), (3.6, 0.0, 2.4), (3.6, 0.0, 4.4), (5.2, 0.0, 4.4)]},
    "Overflow": {"r": 0.40, "pts": [(-1.4, 0.0, 6.3), (-3.5, 0.0, 0.6), (-16.0, 13.0, 0.6)]},
    "Filtrate": {"r": 0.25, "pts": [(9.0, 1.8, 2.7), (9.0, 12.0, 0.6), (-9.0, 21.0, 0.6)], "water": True},
}
FILTER_GEOM = {"x0": 5.0, "x1": 16.5, "y": 0.0, "z": 3.8, "width": 2.6}

# ======================= Standalone cyclone explainer (build_cyclone.py) =======================
# Backup video of the explainer (tools/record_cyclone.py): (start s, end s, mode)
EXPLAINER_VIDEO = [(0, 30, "NORMAL"), (30, 60, "ROPING"), (60, 90, "PULSING"), (90, 100, "NORMAL")]
EXPLAINER = {
    "z0": 1.6,                      # cyclone apex height above the floor (m); geometry below is relative
    "head_r": 1.0, "head_h": 1.0, "cone_h": 3.4, "apex_r": 0.12, "spigot_h": 0.25,
    "vf_r": 0.32, "vf_depth": 0.8, "vf_top": 0.6, "wall": 0.06,
    "cut_deg": 120.0,               # cutaway window facing the camera (-y)
    "inlet": {"y": 0.84, "z": 0.72, "w": 0.3, "h": 0.4, "len": 2.6},   # tangential feed duct (head-relative z)
    "cycle_s": 4.0,                 # seconds for one particle trip at speed 1
    "turns_down": 5.0, "turns_up": 4.0,
    "d50_um": 45.0,                 # silica-equivalent cut size at nominal settings
    "sharpness_m": 2.5, "water_rf": 0.10,
    "rho_water": 1.0, "rho_ref": 2.65,
    "apex_mm": 90.0, "feed_solids_pct": 35.0, "pressure_kpa": 120.0,
    "rope_load": 1.35,              # underflow load ratio above which the apex ropes (auto mode)
    "pulse_kpa": 70.0,              # feed pressure below which feed becomes unstable (auto mode)
    "pulse_period_s": 2.0,
    # (name, label, density t/m3, d_min um, d_max um, count, draw radius m, sRGB colour)
    "classes": [
        ("coarse_hem", "Coarse hematite (5.0 t/m3)", 5.0, 150.0, 1000.0, 300, 0.050, (0.32, 0.12, 0.10)),
        ("fine_hem", "Fine hematite", 5.0, 8.0, 150.0, 400, 0.034, (0.78, 0.22, 0.12)),
        ("silica", "Quartz / silica (2.65 t/m3)", 2.65, 30.0, 400.0, 200, 0.034, (0.85, 0.85, 0.82)),
        ("slimes", "Clay slimes (kaolinite)", 2.6, 1.0, 30.0, 450, 0.022, (0.95, 0.78, 0.40)),
    ],
}
