# PlantSim – Iron Ore Material Tracking Demo (Blender)

Plan: `docs/PLAN.md` (short). Only re-read it when starting a new milestone.

## Rules
- Never edit the .blend by hand or with ad hoc MCP calls. Change the scripts and rebuild.
- One module per asset in `demo/assets/`, built from `demo/assets/_prims.py` helpers. Every number goes in `demo/config.py`. Units are metres.
- `demo/sim/` is pure Python (no bpy, no numpy) and covered by tests. Tonnes and every analyte in must equal what comes out at every step.
- After each change:
  - `py -m pytest -q`
  - `blender -b -P build.py -- --check` (writes `build/plant_demo.blend` and 640x360 stills to `renders/`). Look at the stills before calling a task done.
- Commit after each working milestone. Tag phase gates `p1`, `p2`, `p3`.
- Keep token use low: one milestone per session, read only the files you need, no MCP viewport work except perf gates and polish.

## Layout
- `build.py`: entry point, rebuilds the whole scene.
- `demo/config.py`: all settings.
- `demo/sim/`: parcels, split, blend, cyclone, source.
- `demo/assets/`: geometry.
- `demo/viz/`: colours, tags, KPI overlay, heatmap.
- `demo/story/`: chapters and cameras.
- `demo/ui/`: sidebar panel.
- `tests/`: pytest for sim.
