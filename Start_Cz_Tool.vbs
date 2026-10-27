' SPDX-License-Identifier: GPL-3.0-only
' SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
' This program is free software: you can redistribute it and/or modify it
' under the terms of the GNU General Public License version 3 only.
' This program is distributed WITHOUT ANY WARRANTY; without even the implied
' warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
' See the accompanying LICENSE file for the full license text.
' Existing third-party copyright and license notices remain applicable.
Option Explicit
Dim shell, fso, base, app
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
app = fso.BuildPath(base, "SimNIBS_Cz_distance_tool_v2.4.2\launch_hidden.vbs")
shell.Run "wscript.exe " & Chr(34) & app & Chr(34), 0, False
