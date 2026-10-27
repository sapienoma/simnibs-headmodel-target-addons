REM SPDX-License-Identifier: GPL-3.0-only
REM SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
REM This program is free software: you can redistribute it and/or modify it
REM under the terms of the GNU General Public License version 3 only.
REM This program is distributed WITHOUT ANY WARRANTY; without even the implied
REM warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
REM See the accompanying LICENSE file for the full license text.
REM Existing third-party copyright and license notices remain applicable.
@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_hidden.ps1"
type "%TEMP%\SimNIBS_TargetTool_startup.log"
pause
