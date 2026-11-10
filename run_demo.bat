@echo off
rem Opens the demo with Python scripts allowed (needed for sidebar, KPI panel and playback).
rem Uses %BLENDER% if set, else blender on PATH, else the default Blender 5.2 install folder.
set "BL=%BLENDER%"
if "%BL%"=="" for %%B in (blender.exe) do set "BL=%%~$PATH:B"
if "%BL%"=="" set "BL=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
if not exist "%~dp0build\plant_demo.blend" (
  echo build\plant_demo.blend not found. Build it first:  blender -b -P build.py
  pause
  exit /b 1
)
start "" "%BL%" -y "%~dp0build\plant_demo.blend"
