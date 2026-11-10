# Build plan (trimmed)

**Story:** a cyclone fault in the wet plant is detected, traced through the chevron pile, and pinned to the exact wagons it affected. The demo has 7 chapters (about 7 minutes):
1. Overview
2. Parcels born
3. Cyclones (live roping/pulsing tweak)
4. Stacking
5. Reclaiming
6. Load-out
7. Close

**Metrics:** tonnes and rate; Fe, SiO2, Al2O3, P, LOI; moisture; lump/fines and size.
**Look:** EEVEE low shadows, no ray tracing, solid-mode fallback. Target is 20 fps or better at 1080p on the Arc 140V iGPU.
**Performance:** precompute the sim, then play it back from arrays. GN instances (≤2000 lumps, ≤500 cyclone particles). The pile is one mesh with a colour attribute. Only animate what's on screen.

## Cyclone conditions (illustrative)
| Condition | Yield | Product Al2O3/SiO2 | Moisture |
|---|---|---|---|
| Normal | ~88% | 2.2 / 4.0 | baseline |
| Roping | ~78% | little change | slightly lower |
| Pulsing | swings | ~2.9 / 4.8 | +1% |

## Sessions (one per session, `/clear` between)
| Phase | # | Work | Status |
|---|---|---|---|
| P1 | 1 | config, sim (parcel/split/blend/cyclone/source), tests, build.py --check | done |
| P1 | 2 | _prims, cyclone cluster (5) + hero particles, short product belt | done |
| P1 | 3 | sidebar UI, metric colours, KPI overlay + alert, precompute→playback handler | done |
| P1 | 4 | perf gate (scripted, MCP not needed), tune, tag p1 (Fri 13 Nov) | done |
| P2 | 5 | sim: stockpile layers, BWR cut-blend, load-out/wagons + tests | done |
| P2 | 6 | stacker, chevron pile mesh + heatmap | done |
| P2 | 7 | bucket wheel reclaimer | done |
| P2 | 8 | load-out bin, 28 wagons w/ tags + flags, blend KPIs, tag p2 (Fri 20 Nov) | done |
| P3 | 9 | ROM hopper, crushers, scrubber, screens, scales (low detail) | done |
| P3 | 10 | curve conveyors, terrain, sheds, lump belt (untracked) | done |
| P3 | 11 | story chapters, cameras, chapter buttons (culling not needed: 35 fps) | done |
| P3 | 12 | dry run, fixes, backup clip ch 3–6, tag p3 (Tue 1 Dec) | done |

## Defaults
- Generic plant; targets are in config.
- The lump stream isn't tracked.
- No branding.
- Data comes in through `sim.source.ParcelSource`, so live data can plug in later.

## Notes for later sessions
- The cyclone was built from scratch (`demo/assets/cyclone.py`). The hero is the faulted cyclone (`config.CYCLONE["hero"]`) and is rotated to face +x.
- Animation is pure functions of the frame: `cyclone.update(scene, condition, frame)` and `belt.update(scene, frame)`. Session 3 hooks these into a frame_change handler driven by the sidebar props.
- `_prims.point_cloud` and `set_points` handle every GN-instanced particle or lump.
- Live layer: `demo/runtime.py` (state, recompute, frame handler, boot text), `demo/ui/panel.py`, and `demo/viz/kpi.py` (overlay plus tags). Presenter changes are logged as events that apply from the current sim minute.
- Open the demo with `run_demo.bat`. The `-y` flag is needed so the boot script runs.
- GUI check: `blender -y build/plant_demo.blend -P tools/shot.py -- renders/ui_check.png PULSING 9`
- Colours: the ramp is in sRGB; use `colors.to_linear()` before writing Blender attributes.
- Perf gate P1 (9 Nov 2026, AC power, Balanced, 1920x1080 window, 1570x907 viewport): EEVEE Rendered 37-38 fps, Material 34-35, Solid 58-66. The Python handler costs about 1.1 ms/frame. At 2359x1442 the viewport drops to about 19 fps, so present at 1080p. Recheck after each phase: `blender -y -p 0 0 1920 1080 build/plant_demo.blend -P tools/perf.py -- 8` (writes renders/perf.txt).
- Budget left for P2+P3 is about 45% of frame time. Use Solid mode as the fallback (≥58 fps).
- The **Present** button gives a full-screen 3D view with the sidebar kept and the camera framed. The default shading is EEVEE Rendered.
- Milestone files: `milestones/p1.blend` (open with `-y`).
- Yard sim (`demo/sim/stockyard.py`): `run_yard(records)` returns a pile (cells[(layer, slice)]), reclaimed cuts [(minute, slice, parcel)], wagons and leftover.
  - Stacking: one chevron layer per 15-min pass, 40 slices. The stacker position comes from `stacker_pos(minute)`, for geometry.
  - Reclaiming: the BWR blends one whole slice per cut, slice 0 first. `pile.grid(metric)` gives the heatmap data.
  - Tracing: `Parcel.contrib` (product minute → t) traces every wagon tonne, and `Wagon.trace(records)` gives the faulty minutes and cyclones.
  - Flagging: a wagon is flagged when >0.5% of its tonnes came from a PULSING cyclone. Roping costs tonnes, not grade, so it doesn't flag.
- Yard geometry: the pile runs along +x from x=40 to 140, centreline y=0, drawn at 15x volume. The stacker rail is at y=-26 and the yard belt at y=-30. The BWR goes on the +y side (rail y=+26) in session 7.
  - `pile.update` rebuilds one mesh per frame (face colour attr "col"). The top skin shows the top layer; the end and reclaim faces show the V-bands. `pile.height_at(None, minute, x)` gives the crest height.
  - Reclaimed slices disappear once their reclaim minute has passed. Session 7 adds the BWR and a partial-cut face.
  - Python cost: on_frame 2.5 ms, recompute (wet plant + yard) 13 ms.
- BWR (`demo/assets/bwr.py`): the rail is at y=+26 with a 45 m boom. `reach()` solves travel, slew and luff to put the wheel on the cut face, making 3 benches per slice.
  - `pile.reclaim_front()` gives the active slice and the fraction cut, and the pile face recedes smoothly.
  - Reclaim runs at minutes 125-159 (about 0.86 min per slice). Story session 11 must slow playback for chapter 5, otherwise each slice lasts about 0.4 s.
- Load-out (`demo/assets/loadout.py`): the bin is at x=175 over the track (y=60), fed by the LoadBelt from (128,34). There are 28 wagons as linked duplicates; the load colour comes from `obj.color` (Object Info) and blinking red beacons mark flagged wagons.
  - `train_state()` places the train and the fills. Loaded wagons move +x past the chute.
  - The overlay shows the yard KPIs (stockpile and layer, reclaimed t, wagons and flagged, blending SD), the flagged-wagon alert, and wagon tags.
  - Gotcha: `_prims.box` bakes the location into the mesh (transform_apply defaults), so linked duplicates need offset (0,0,0).
- Perf gate P2: Rendered 38-39 fps on both the cyclone and yard views at 1080p; Python 4 ms/frame. `tools/perf.py -- 8 125 20,-60,40 90,10,3` tests the yard view. `tools/shot.py` accepts SCHEDULE plus a camera loc/target.
- Milestones: `milestones/p2.blend`.
- Upstream (session 9) along -x at y=0: ROM bin and crusher at x=-130, CrusherBelt to the scrubber at -64 (it spins), screen at -50 (it shakes).
  - TP1 (x=-100) and TP2 (x=15) have belt-scale and analyser arches whose LEDs flash per parcel. TP3 is the weighbridge at the chute, flashing per wagon.
  - The train now runs toward -x: empties queue east and loaded wagons pull west past the yard. The BWR parks with its boom along the rail (+x).
- Links (session 10, `conveyors.py`): slurry pipe from the screen sump to the cyclone riser, LumpBelt to the untracked lump pile, TransferBelt from the product belt to the yard belt, ReclaimBelt along y=33.5 to the LoadBelt. `site.py` adds roads, sheds, the thickener with its tailings pipe, and berms.
- Perf: `build.merge_static()` joins static meshes per collection, taking 722 objects to 276. Keep animated or name-looked-up objects parented, GN-based, or listed in KEEP_SEPARATE.
  - Belt lumps use a cached layout plus 24 colour buckets, and cyclone particles use cached randoms.
  - Whole-site view at 1080p: Rendered 35 fps, Solid 55, Python 2.8 ms.
- Story (session 11): `config.STORY` sets 7 chapters (6 min 15 s, 9000 frames). `demo/story/chapters.py` maps frames to each chapter's sim-minute window, and `cameras.py` adds keyframed Cam_Ch1..7 bound to timeline markers.
  - The sidebar has a Story box (chapter buttons 1-7, story toggle, speed), and the overlay shows the chapter caption. Chapter 2 shows feed-parcel tags on the CrusherBelt.
  - Live events now layer on top of the scripted fault (`use_schedule` default on), so presenter tweaks in chapter 3 (minutes 50-75) flow into the pile and wagons.
  - The BWR parks at the east end and travels in during minutes 123-125.
  - Gotcha (fixed): the GUI opened in Solid mode, which hides live colours. `runtime._show_tab` now forces RENDERED shading on load.
  - Wagon loads use per-wagon materials; Object Info colour didn't update live.
  - Session 12: `tools/dryrun.py` jumps to each chapter, plays it, logs fps (all 23.8 = cap), and runs the ch3 live tweak (the alert now fires immediately, because events apply from the current parcel).
  - Tags are hidden in overview chapters 1 and 7. `tools/record.py` + `tools/encode.py` produce `renders/backup_ch3-6.mp4` from GUI screenshots, so the overlay is included. Presenter notes: `docs/RUNSHEET.md`.
  - `build.py --check --only story` renders just the chapter stills. `tools/shot.py -- out.png CH6 20` screenshots 20 s into chapter 6.
- Scripted scenario: 120 sim min, roping C3 at 30-45 and pulsing C3 at 62-70. The result is 3.4 kt, 8 layers, a 28-wagon train, and wagons 4-19 flagged. Al2O3 sd falls 0.050 → 0.015 through the BWR.

## Update (9 Nov, after p3): segments, belt filter, bench pile
- `demo/viz/segments.py`: every belt, glass pipe and wagon shows parcels as blocks. Height = dry t vs the stream's median parcel; stacked bands = `runtime.bands(pd)` (sidebar Band 1-4, default Fe/Al2O3/SiO2/moisture).
  - Streams are listed in `segments.streams()` with off/lag in sim minutes.
  - Upstream streams (rel=True) are coloured vs their own normal median; product streams vs config.METRICS.
  - Belt lumps are off (`belt.build(lumps=False)`).
- Sim: fines leave the screen as slurry (65% moisture). The underflow is a 30% slurry (+4x moist_delta). `belt_filter()` takes it to cake at 8.5 + 0.25*(uf-30). Records add `.fines` and `.underflow`, and `.product` is now filter cake.
- Layout: underflow pipe → belt filter (x 5-16.5) → product belt (17.5→31) → transfer at x=32.5. Glass pipes are in `config.PIPES` (feed slurry, underflow, overflow → thickener, filtrate). TP2 is at x=24.
- Pile: 80 slices × 3 benches. Bench values are area-weighted blends of the chevron layers. The surface and reclaim face are banded per metric, and the pile ends show the chevron layers.
- Check views now unbind marker cameras while rendering (markers had been overriding check cameras since session 11).
- Perf after the update: yard 32 fps, site 34 fps, dry run 23.5-24 fps (cap) in every chapter.

## Standalone hydrocyclone explainer (9 Nov)
- `build_cyclone.py` builds `build/cyclone_explainer.blend`; open it with `run_cyclone.bat`. Code is in `demo/explainer/`: `model.py` (pure: Plitt-style partition with density-corrected d50, mode effects, particle paths, tested in `tests/test_explainer.py`), `scene.py` (lathed cutaway shell, 120° window), and `live.py` (sidebar, frame handler, overlay text, partition chart, labels).
- Settings live in `config.EXPLAINER`. 1,350 particles cost about 3 ms/frame in Python. GUI check: `tools/shot_cyclone.py -- out.png MODE`.

## Pilbara detail pass (9 Nov): infrastructure and equipment
- **Builder:** `_prims.Mesh` builds many parts into one multi-material mesh with no bpy.ops calls. `at()` nests local frames, `merge()` appends another Mesh, and `lathe`/`prism`/`bar`/`pipe` cover most shapes. The full build still takes about 7 s.
  - `_steel.py` is the structural kit: handrails with kick plates, grating decks and walkways, stairs and switch-back flights, box and plane trusses, trestle bents, braced towers, transfer towers and clad sheds (gable roof, gutters, roller doors, windows, roof vents).
- **Materials:** `config.MATERIALS` sets defaults per material name (galvanised, safety yellow, grating, cladding, alloy ore car, loco livery and so on).
  - `dust` adds red-dust weathering, driven by world z with a noise break-up. `ribs` adds a profiled-sheeting bump (wall, roof or roller door).
  - Both can be switched off in `config.LOOK`, but A/B tests showed no fps cost.
- **Conveyors (`belt.py`):** each belt is now one `{name}_Structure` mesh: troughed belt on 3-roll idler sets, return rollers, channel stringers, pulleys, a walkway with handrail on `walk_side`, and hood hoops.
  - Belts above `CONVEYOR["gallery_min_z"]` get a box-truss gallery on trestle bents.
  - Covers are left as open hoops on purpose, because sheeted hoods would hide the tonnage segments.
- **Transfer towers (`towers.py`, `config.TRANSFER_TOWERS`):** crusher-belt head, product-belt head, yard-belt tail, and an open frame at the reclaim head (the BWR counterweight swings over it).
- **Layout change:** the TransferBelt now runs diagonally to the yard-belt **tail** (`YARD_GEOM["tail_back"]`), so the stacker's tripper car never runs into a tower. `boom_pivot_h` is now 7.5 so the tripper head (8.9) can drop into the boom.
- **Equipment:**
  - Cyclone cluster: flanged bodies, knife-gate valves with actuators, dished manifold, U-section launders, a 4-column frame and a top deck in the `CycloneDeck` collection (no shadow) with a stair. Faces toward the ch3 camera stay open below the deck so the hero cyclone stays visible.
  - Belt filter: elevated deck, drums, drive, vacuum box, filtrate receivers and vacuum pump.
  - BWR: rail bogies, portal, machinery house, cab, lattice boom, mast with stays, counterweight boom, and a wheel with shaped buckets and teeth.
    - Child meshes: `BWR_Base`, `BWR_Superstructure`, `BWR_Boom`, `BWR_WheelBody`. The empties `BWR` > `BWR_Slew` > `BWR_Luff` > `BWR_Wheel` are unchanged.
  - Stacker: lattice boom, A-frame, counterweight, cab, lattice tower and a tripper car riding the yard-belt stringers. Child meshes: `Stacker_Base`, and `Stacker_Boom` under `Stacker_BoomPivot`.
  - Load-out: braced structure, bin with stiffeners, head house, ballast and sleepers.
  - Ore cars: alloy gondolas with ribs and three-piece bogies (still linked duplicates of `tmpl_body`/`tmpl_bogie`).
  - Locos: two generic long-hood units (`Loco_Unit1`/`Loco_Unit2`, sharing one mesh) under `Loco`.
  - Haul trucks (`haultruck.py`, `config.TRUCKS`): one dumping, one queued, one on the ramp.
  - Crusher station: pocket, rock breaker, crusher building, baghouse, e-room and a ramp with windrows.
  - Scrubber (girth gear and trunnions) and screen house frame.
- **Site:** clad workshop with roller doors, transportables with verandahs, substation with transformers and fence, a detailed thickener, water tanks (kept out of the ch3 shot) and light towers.
- **Checks:** `--only detail_` renders 11 close-ups. `py tools/sheet.py OUT.png PREFIX [cols]` tiles check renders into one sheet. The build prints triangles per collection: about 126k in total (from 35k), with wagons the largest at 52k.
- **Perf gotcha:** the `Segments` mesh is rebuilt every frame along every belt. If it casts shadows, every shadow page over the detailed belts is redrawn each frame (about 3-5 fps at 1080p). It now has `visible_shadow = False`; keep any per-frame mesh that spans the site shadowless.
- **Perf gate (10 Nov, AC power, 1080p):** whole site Rendered 33.9 fps uncapped (Material 31.3, Solid 45.1). The yard view at minute 125 runs at 29.1.
  - Python `on_frame` takes 2.6 ms. The dry run holds 23.6-24.2 fps (the cap) in all 7 chapters, and the ch3 live tweak still fires its alert and flags wagons 16 -> 28.
  - On battery the laptop throttles hard: HEAD and this build both drop to 12-23 fps and on_frame reads about 6.3 ms. Always gate on AC.

## Chapter 5 digging (10 Nov)
- **Timing:** chapter 5 now runs 120 s over sim minutes 124.6-127.2, so the story is 7¼ min. The wheel takes one **block** of `BWR_GEOM["block_slices"]` = 4 slices (5 m) per bench pass.
  - A block takes about 1.7 sim min, which is about 80 s on screen: about 26 s per bench.
  - The sim still reclaims slice by slice, so tonnes, timing and wagons are unchanged. Only the drawing groups the slices.
  - Chapter 6 picks up at minute 142, as before.
- **Cut state:** `pile.bench_cut(block, frac, h, hw)` is shared by the pile mesh and the BWR (`bwr.wheel_target`).
  - Benches are taken top first. Each one starts with an `ease` share (15%) of luffing and repositioning, then one slew across.
  - Material on the side the wheel has passed is gone. Slew direction alternates bench by bench, so each bench starts where the last one ended.
- **Pile drawing:** the active block draws stepped benches: slope strips only where material remains, faces only at the block front and back, a wall along the cut line, and flat treads.
- **Camera:** end-on from high in the west, aimed right of and above the face, so the face and wheel sit in the clear area below the KPI panel and left of the sidebar. Check it with `tools/shot.py -- C:/abs/out.png CH5 55`, which needs an absolute output path.
  - `ch5_dig1..4` check views cover the top, middle and bottom benches.
- **Viewport:** camera wireframes are hidden in the exec view (`show_object_viewport_camera = False`).
- **Dry run (AC):** 23.5-24.2 fps in every chapter.

## Smaller slices (10 Nov)
- **Parcels:** `SOURCE["parcel_t"]` is 25 t, one every 30 s (was 100 t every 2 min). The sim now makes 240 parcels, and each belt shows about 4x more, shorter tonnage segments.
  - Alerts scale with the parcel count (46 vs 12). The story is unchanged: 28 wagons, wagons 4-19 flagged, and the ch3 live tweak flags 28.
- **Pile:** `STOCKPILE["slices"]` is 160 (0.625 m each). A cut block is still 4 slices, now 2.5 m deep.
  - Chapter 5 covers minutes 124.85-126.2, so a bench pass still takes about 25 s.
- **Performance:**
  - The static pile mesh (`Pile`) is rebuilt only when the stacked state changes (a parcel piece is laid, or a block starts or ends), and each slice's geometry is cached and reused when it hasn't changed (`pile._chunks`).
  - The block under the wheel is its own small mesh (`PileCut`), rebuilt every frame.
  - `pile.invalidate()` runs after every yard recompute; Python can reuse `id(yard)`, so never rely on the id alone.
  - The segment box builder is flattened.
  - Handler: ch3 9.5, ch4 11, ch5 5 ms/frame (background).
  - Dry run on AC: 23.3-24.0 fps in every chapter.

## Backup videos (10 Nov)
- `py tools/backup_videos.py [chapters...]` runs `tools/record.py` (GUI, every frame), then `tools/encode.py`, for each chapter, and deletes the frames as it goes.
  - Output: `renders/backup/chN_<title>.mp4` (1920x1080, 24 fps), plus `full_story.mp4` joined with ffmpeg (stream copy).
  - It takes about 7.5 min of recording and encoding per minute of story.
- **Encode gotcha (fixed):** `encode.py` runs with `--factory-startup`, which defaults to the AgX view transform and washes out the sRGB screenshots. It now forces Standard. The old `backup_ch3-6.mp4` has this haze.
- `record.py` turns viewport overlays off while recording, which removes the dashed camera frame. The KPI panel, tags and labels are drawn by our own overlay handler and still show.

## Stockyard web view (10 Nov)
- `web/stockyard.html` is a simple browser view of the stacker, stockpile, reclaimer and train. It has no Blender dependency and no external libraries, and it opens straight from disk.
  - **Data:** `py tools/export_web.py` runs the pure-Python sim and writes `web/yard_data.js` (about 300 kB): cells with laid pieces and blended grades, reclaim cuts, wagons with traces, and product records. Re-export after changing the sim or config.
  - **Views:** a feed strip (product by minute, fault windows shaded) and a long section (one column per slice, one block per chevron layer, height = tonnes), with the stacker laying layers and the reclaimer cutting the face bench by bench.
    - A cross-section of any slice shows the chevron triangles and the 3 benches with their blended grades.
    - KPIs include the variability drop from stacked to reclaimed to wagons.
    - The train shows fill, grade colour and flags, and clicking a wagon shows its source slices and fault trace.
  - **Controls:** play/pause (space), speed, scrub, jumps, metric, fault outline, and hover tooltips. Playback runs 10x slower during the reclaim.
  - **Deep links:** `stockyard.html#t=62&metric=Al2O3&fault=1&slice=40&wagon=5&play=1`.
- The Claude browser pane can't load the companion script from `file://`, so `.claude/launch.json` adds a `stockyard-web` local server: `py -m http.server 8765 --directory web`.
