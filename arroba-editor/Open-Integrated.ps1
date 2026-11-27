$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$ffmpeg = (Get-ChildItem (Join-Path $repo 'ffmpeg-dev') -Directory | Select-Object -First 1).FullName
$env:Path = "$ffmpeg\bin;C:\Program Files\Concat;$env:Path"
Start-Process -FilePath (Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe') -ArgumentList ('"' + (Join-Path $PSScriptRoot 'launch_silent.pyw') + '"') -WindowStyle Hidden -WorkingDirectory $repo
