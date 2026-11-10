# Presenter run sheet: iron ore material tracking demo

## Before the room (day before / 30 min before)
1. Laptop plugged in, Windows power mode **Best performance**, external display at **1920×1080** (not 4K).
2. Double-click `run_demo.bat` (opens Blender with scripts allowed). First launch only: click **Continue** on Blender's splash.
3. Sidebar **Plant Demo** tab opens automatically. Click **Present** for a full-screen view with the sidebar kept.
4. Click **Reset**, then chapter **1**. Press **Play** once and stop it to check the fps is smooth.
5. Backup videos are in `renders/backup/`: one per chapter (`ch1_plant_overview.mp4` … `ch7_close_every_wagon_traced.mp4`) and `full_story.mp4`, plus `cyclone_explainer.mp4` (the standalone explainer: Normal, Roping, Pulsing, then Normal, 100 s). They are 1080p at 24 fps and include the KPI panel, tags and captions. Keep a known-good copy of `build/plant_demo.blend` from your last rehearsal (any build can be recreated with `blender -b -P build.py`). Re-record after visual changes with `py tools/backup_videos.py` (about an hour on AC power; pass chapter numbers to redo only some, or `cyclone` for the explainer video).

## How to read the ore
- Each block on a belt, in a glass pipe or in a wagon is one parcel. Its **height is its tonnes** (a roping cyclone gives visibly thinner blocks).
- Its **bands, top to bottom, are Band 1–4** (default Fe, Al2O3, SiO2, Moisture). Change them in **Metric bands**, or pick "(none)" to show fewer.
- Feed, slurry and tailings are coloured against their own normal (green = typical). Filter cake, product, reclaimed ore and wagons are coloured against target.
- The stockpile shows the same bands for each of its **3 benches** along 160 slices. The reclaim face shows the benches the bucket wheel is digging, and the pile ends show the chevron layers (Band 1 metric).
- **Flow:** screen fines leave as slurry and are piped to the cyclones. The underflow slurry is piped to the **belt filter**, which dewaters it to cake that goes onto the product belt and then the stacker. The overflow is piped to the **thickener**. Pulsing makes the cake wetter (watch the moisture band).

## The 7 chapters (about 7¼ min; click the chapter number to jump camera and time)
| # | Chapter | Length | What to say / do |
|---|---|---|---|
| 1 | Plant overview | 30 s | "Every tonne from crusher to train." The KPI panel shows rate, tonnes and grade vs target. |
| 2 | Parcels are born | 45 s | Tags on the crusher belt: parcel ID, blast block, tonnes, grade. TP1 analyser flashes per parcel. |
| 3 | Wet plant and cyclones (live) | 90 s | Click **C3**, then **Roping**: yield drops, blocks get thinner and the alert fires. Then **Pulsing** (hold 5–10 s): slimes bypass, the alert fires, and the Al2O3 and moisture bands turn orange through the filter. Then **Normal**. |
| 4 | Stacking the chevron pile | 60 s | The off-spec material from chapter 3 is laid into the pile, visible in the bench bands. |
| 5 | Reclaiming | 120 s | Close-up of the bucket wheel taking a 2.5 m block in 3 benches, top first. Each bench is a slow slew across the face, and the material disappears behind the wheel as it passes. Every bench cuts through all the chevron layers, so the off-spec band is blended away. |
| 6 | Train load-out | 60 s | Each wagon shows banded grade and fill. Flagged wagons blink red and their tag names the cyclone and the minutes. Blending KPI shows the variability cut. |
| 7 | Close | 30 s | "Every wagon traced back to the hour and cyclone it came from." |

## Rules of thumb
- **Live changes carry downstream.** Whatever you do to a cyclone in chapter 3 shows up in the pile and the wagons. Always set it back to **Normal**, or the rest of the story shows a plant still faulting.
- If you don't touch anything, a scripted pulsing fault (C3, minutes 62–70) still plays. Once you change C3 yourself, your settings replace the script for C3 from that moment. So hold **Pulsing** for 5–10 seconds if you want flagged wagons. Untick **Scripted fault** to turn the script off entirely.
- **Reset** clears all live changes and returns to the start.
- **Speed** in the Story box speeds up or slows down playback without changing the story.
- If anything stutters, set the viewport to **Solid** (Z menu): it runs about 55 fps, but loses the live colours.
- All values are illustrative. The pile is drawn at 15× volume for visibility, and the tonnes shown are true sim values.

## Standalone hydrocyclone explainer
Double-click `run_cyclone.bat` (build it first with `blender -b -P build_cyclone.py`).
- **Cyclone** sidebar tab: **Normal / Roping / Pulsing** buttons, or tick **Auto mode from settings** and change the apex, feed solids or pressure. Example: apex 70 mm at 45% solids ropes; pressure below 70 kPa pulses.
- Particles: dark = coarse hematite, red = fine hematite, white = quartz/silica, yellow = clay slimes. Each particle is sent to underflow or overflow by the partition curve (bottom-left chart). Hematite cuts finer than silica because it is denser.
- Things to point out: the outer vortex spirals down the wall, the inner vortex rises around the air core, the umbrella spray (normal) vs the rope with no air core and coarse ore in the overflow (roping), and surging spray with slimes in the underflow (pulsing).
