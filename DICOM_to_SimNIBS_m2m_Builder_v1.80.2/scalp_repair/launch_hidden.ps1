# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
$ErrorActionPreference = 'Stop'
$log = Join-Path $env:TEMP 'SimNIBS_ScalpRepair_startup.log'
try {
    Set-Location -LiteralPath $PSScriptRoot
    $preferencesPath = Join-Path $env:LOCALAPPDATA 'SimNIBS_HeadBuilder\settings.json'
    $preferences = [PSCustomObject]@{}
    if (Test-Path -LiteralPath $preferencesPath -PathType Leaf) {
        try { $preferences = Get-Content -LiteralPath $preferencesPath -Raw -Encoding UTF8 | ConvertFrom-Json }
        catch { $preferences = [PSCustomObject]@{} }
    }
    if ($null -eq $preferences -or $preferences -isnot [PSCustomObject]) { $preferences = [PSCustomObject]@{} }
    $originalPath = $env:PATH
    function Test-SimNIBSPython([string]$candidate) {
        if (-not $candidate -or -not (Test-Path -LiteralPath $candidate -PathType Leaf)) { return $false }
        $envDir = Split-Path -Parent $candidate
        $env:PATH = "$envDir;$(Join-Path $envDir 'Scripts');$(Join-Path $envDir 'Library\bin');$originalPath"
        $ErrorActionPreference = 'Continue'
        & $candidate -c "import simnibs" *> $log
        return ($LASTEXITCODE -eq 0)
    }
    $candidates = @($env:SIMNIBS_PYTHON, $preferences.python)
    $candidates += (Join-Path $env:ProgramFiles 'SimNIBS-4.6\simnibs_env\python.exe')
    $candidates += 'C:\SimNIBS-4.6\simnibs_env\python.exe'
    $candidates += (Join-Path $env:USERPROFILE 'SimNIBS-4.6\simnibs_env\python.exe')
    $pathEntry = Get-Command simnibs_python -ErrorAction SilentlyContinue
    if ($pathEntry) {
        $entryDir = Split-Path -Parent $pathEntry.Source
        $candidates += (Join-Path $entryDir 'python.exe')
        $candidates += (Join-Path (Split-Path -Parent $entryDir) 'python.exe')
        $candidates += (Join-Path (Split-Path -Parent $entryDir) 'simnibs_env\python.exe')
    }
    $python = $null
    foreach ($candidate in ($candidates | Where-Object { $_ -is [string] -and $_ } | Select-Object -Unique)) {
        if (Test-SimNIBSPython $candidate) { $python = $candidate; break }
    }
    while (-not $python) {
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = 'Select python.exe inside the installed SimNIBS 4.6 simnibs_env folder'
        $dialog.Filter = 'SimNIBS Python|python.exe'
        if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
        if (Test-SimNIBSPython $dialog.FileName) { $python = $dialog.FileName }
        else { [System.Windows.Forms.MessageBox]::Show("This Python could not import SimNIBS. Select the installed SimNIBS environment. Details: $log") | Out-Null }
    }
    # Save only this machine's Python while retaining DICOM/output/converter choices.
    $preferences | Add-Member -MemberType NoteProperty -Name python -Value $python -Force
    $settingsDir = Split-Path -Parent $preferencesPath
    New-Item -ItemType Directory -Path $settingsDir -Force | Out-Null
    $temporarySettings = Join-Path $settingsDir ([Guid]::NewGuid().ToString() + '.tmp')
    $preferences | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $temporarySettings -Encoding UTF8
    Move-Item -LiteralPath $temporarySettings -Destination $preferencesPath -Force
    $env:PYTHONIOENCODING = 'utf-8'
    $app = Join-Path $PSScriptRoot 'gui.py'
    $ErrorActionPreference = 'Continue'
    & $python -u $app *> $log
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 1 }
    exit $code
} catch {
    $_ | Out-String | Out-File -LiteralPath $log -Encoding utf8
    exit 1
}
