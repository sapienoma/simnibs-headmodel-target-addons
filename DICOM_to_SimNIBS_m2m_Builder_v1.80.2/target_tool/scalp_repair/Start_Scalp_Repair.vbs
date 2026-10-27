' SPDX-License-Identifier: GPL-3.0-only
' SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
' This program is free software: you can redistribute it and/or modify it
' under the terms of the GNU General Public License version 3 only.
' This program is distributed WITHOUT ANY WARRANTY; without even the implied
' warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
' See the accompanying LICENSE file for the full license text.
' Existing third-party copyright and license notices remain applicable.
Option Explicit
Dim shell, fso, folder, ps, cmd, rc
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
ps = folder & "\launch_hidden.ps1"
cmd = "powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File " & Chr(34) & ps & Chr(34)
rc = shell.Run(cmd, 0, True)
If rc <> 0 Then
    MsgBox "Unable to start Scalp Repair. See %TEMP%\SimNIBS_ScalpRepair_startup.log.", 16, "SimNIBS Scalp Repair"
End If
