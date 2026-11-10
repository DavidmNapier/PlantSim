@echo off
rem Opens the standalone hydrocyclone explainer (scripts allowed for the sidebar and animation).
rem Uses %BLENDER% if set, else blender on PATH, else the default Blender 5.2 install folder.
set "BL=%BLENDER%"
if "%BL%"=="" for %%B in (blender.exe) do set "BL=%%~$PATH:B"
if "%BL%"=="" set "BL=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
if not exist "%~dp0build\cyclone_explainer.blend" (
  echo build\cyclone_explainer.blend not found. Build it first:  blender -b -P build_cyclone.py
  pause
  exit /b 1
)
start "" "%BL%" -y "%~dp0build\cyclone_explainer.blend"
