$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$buildStarted = [DateTimeOffset]::Now.ToString('o')
@{ state = 'running'; pid = $PID; started = $buildStarted } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $PSScriptRoot 'build-state.json')
Start-Process -FilePath (Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe') -ArgumentList ('"' + (Join-Path $PSScriptRoot 'build_monitor.pyw') + '"') -WindowStyle Hidden
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\Launch-VsDevShell.ps1' -Arch amd64 -HostArch amd64 -SkipAutomaticLocation
$env:LIBCLANG_PATH = Join-Path $repo 'vendor\llvm\bin'
$env:FFMPEG_DIR = (Get-ChildItem (Join-Path $repo 'ffmpeg-dev') -Directory | Select-Object -First 1).FullName
$env:Path = "$env:USERPROFILE\.cargo\bin;$PSScriptRoot\.venv\Scripts;$env:LIBCLANG_PATH;$env:FFMPEG_DIR\bin;$env:Path"
if (-not (Test-Path "$env:LIBCLANG_PATH\libclang.dll")) { throw 'LLVM installation is not complete' }
Set-Location (Join-Path $repo 'src')
& cargo build --profile quick -p concat --jobs 2 *> (Join-Path $PSScriptRoot 'integrated-build.log')
$buildExit = $LASTEXITCODE
"Exit code: $buildExit" | Set-Content (Join-Path $PSScriptRoot 'integrated-build-status.txt')
@{ state = $(if ($buildExit -eq 0) { 'done' } else { 'failed' }); pid = $PID; started = $buildStarted; exitCode = $buildExit } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $PSScriptRoot 'build-state.json')
exit $buildExit
