# PlantSim: iron ore material tracking demo (Blender)

A live, interactive Blender demo of an iron ore plant that tracks every parcel of ore from the crusher to the train. The story: a hydrocyclone fault in the wet plant is detected, traced through a chevron stockpile, and pinned to the exact train wagons it affected.

It also includes a standalone **hydrocyclone explainer** (how cyclones classify iron ore by size and density, with Normal / Roping / Pulsing modes) and a simple **browser view** of the stockyard.

Everything is generated from Python scripts. The `.blend` files are build outputs, so never edit them by hand: change the scripts and rebuild. All values are illustrative and the plant is generic.

## Requirements
- Windows 10/11 (the `.bat` launchers are Windows-only; the build scripts are cross-platform).
- **Blender 5.2** (`winget install BlenderFoundation.Blender`). Put `blender` on PATH, or set the `BLENDER` environment variable to the full path of `blender.exe`.
- **Python 3.11+** with pytest (`py -m pip install pytest`), for the simulation tests and tools. The sim is pure Python with no other dependencies.
- Optional: **ffmpeg** on PATH, only for joining the backup chapter videos into one file.
- GPU: tuned for 24 fps or better at 1920x1080 on an Intel Arc 140V laptop iGPU (EEVEE). Anything at that level or better works.

## Quick start
```bash
git clone <this repo>
cd PlantSim
py -m pytest -q                         # sim tests (mass and analyte balance)
blender -b -P build.py                  # builds build/plant_demo.blend (a few minutes)
blender -b -P build_cyclone.py          # builds build/cyclone_explainer.blend
```
Then double-click **`run_demo.bat`** (main demo) or **`run_cyclone.bat`** (cyclone explainer). They open Blender with `-y` so the demo's Python scripts are allowed to run. Without that, the sidebar, KPI panel and playback do not work.

In Blender, the **Plant Demo** sidebar tab (press `N` if it is hidden) has the chapter buttons 1–7, playback speed, metric band choices, cyclone controls, **Present** (full-screen) and **Reset**. Press Space to play.

How to present it (the 7 chapters, what to click, how to read the colours): see **[docs/RUNSHEET.md](docs/RUNSHEET.md)**.

Browser view of the stockyard (no Blender needed): open `web/stockyard.html` directly, or regenerate its data with `py tools/export_web.py`.

## How it works
1. **Simulation (`demo/sim/`, pure Python):** ore is split into 25 t parcels with tonnes and analytes (Fe, SiO2, Al2O3, P, LOI, moisture, size). Parcels pass through the crusher, scrubber, screen, cyclone cluster (a partition model with Normal / Roping / Pulsing conditions), belt filter, stacker, chevron stockpile, bucket wheel reclaimer and train load-out. Every split and blend conserves tonnes and every analyte, and each parcel carries a contribution ledger, so every wagon tonne traces back to the minute and cyclone it came from. Data enters through `sim.source.ParcelSource`, so live plant data could plug in later.
2. **Geometry (`demo/assets/`):** one module per asset, built from the shared helpers in `_prims.py` and `_steel.py`. Units are metres.
3. **Playback (`demo/runtime.py`):** the sim is precomputed, then a frame-change handler drives everything from arrays. Ore on belts, in pipes and in wagons is drawn as banded blocks (`demo/viz/segments.py`): height = tonnes, bands = up to 4 chosen metrics.
4. **Story (`demo/story/`):** 7 chapters on the timeline with a camera per chapter. **UI (`demo/ui/`)** is the sidebar. **Overlay (`demo/viz/kpi.py`)** draws the KPI panel, tags and captions with the GPU module.
5. A boot text block inside the `.blend` registers the runtime when the file opens (this is why `-y` is needed).

All settings and numbers live in **`demo/config.py`**: plant layout, parcel size, cyclone model, fault schedule, chapter lengths, cameras, colours.

## Repository layout
| Path | What it is |
|---|---|
| `build.py` | Rebuilds the whole demo scene. `--check` also renders 640x360 stills to `renders/`; `--only <prefix>` limits the stills; `--no-save` skips writing the .blend. |
| `build_cyclone.py` | Builds the standalone cyclone explainer (`--check` renders a still per mode). |
| `demo/config.py` | Every setting. |
| `demo/sim/` | Parcels, split/blend, equipment, wet plant, stockyard (pile, reclaim, train). No bpy. |
| `demo/assets/` | Geometry, one module per asset. |
| `demo/viz/` | Colours, segments, KPI overlay and tags. |
| `demo/story/` | Chapters and cameras. |
| `demo/ui/` | Sidebar panel. |
| `demo/explainer/` | Cyclone explainer: model, scene, live UI. |
| `tests/` | pytest for the sim, story timing, colours and explainer model. |
| `tools/` | Perf test, screenshots, dry run, video recording and encoding, web export. |
| `web/` | Browser stockyard view. |
| `docs/RUNSHEET.md` | Presenter guide. |
| `docs/PLAN.md` | Build plan and developer notes (design decisions, coordinates, perf numbers). |
| `CLAUDE.md` | Rules for working on the repo with Claude Code. |

## Making changes
1. Edit the scripts (numbers go in `demo/config.py`).
2. `py -m pytest -q`: tonnes and every analyte in must equal what comes out at every step.
3. `blender -b -P build.py -- --check`: rebuilds `build/plant_demo.blend` and writes stills to `renders/`. Look at the stills.
4. For anything visual or interactive, open it with `run_demo.bat` and play the affected chapter.

## Tools
Run these from the repo root. GUI tools need a 1920x1080 window (`-p 0 0 1920 1080`).
```bash
blender -y -p 0 0 1920 1080 build/plant_demo.blend -P tools/perf.py -- 8      # fps per shading mode -> renders/perf.txt
blender -y -p 0 0 1920 1080 build/plant_demo.blend -P tools/dryrun.py          # plays all chapters, fps per chapter -> renders/dryrun.txt
blender -y build/plant_demo.blend -P tools/shot.py -- renders/ui_check.png PULSING 9   # GUI screenshot: C3 pulsing, at sim minute 9
py tools/backup_videos.py                 # records 1080p/24 fps backup videos to renders/backup/ (about an hour)
py tools/backup_videos.py 3 5             # only chapters 3 and 5
py tools/backup_videos.py cyclone         # the cyclone explainer video
py tools/export_web.py                    # regenerates web/yard_data.js
```

## Performance tips
- Present at 1920x1080, not 4K: the viewport fps roughly halves at higher resolutions.
- On a laptop, plug in and use Windows power mode **Best performance**. On battery the GPU throttles hard.
- If anything stutters, switch the viewport to **Solid** shading (about 55 fps, but no live colours).

## Not in the repo
`build/` (the built .blend files), `renders/` images and the `.mp4` backup videos are generated, so they are git-ignored. Rebuild them with the commands above.
