$ErrorActionPreference='SilentlyContinue'
Stop-Process -Id 31292,29004 -Force
Start-Sleep -Seconds 2
if (-not (Test-Path 'logs')) { New-Item -ItemType Directory -Path 'logs' | Out-Null }
$d = Start-Process -FilePath '.venv/Scripts/python.exe' -ArgumentList '-m','src.server','--port','5000' -PassThru -WindowStyle Hidden -RedirectStandardOutput 'logs/dash.out.log' -RedirectStandardError 'logs/dash.err.log'
$e = Start-Process -FilePath '.venv/Scripts/python.exe' -ArgumentList '-m','src.runner','--provider','all','--models','auto','--benchmarks','all','--quick' -PassThru -WindowStyle Hidden -RedirectStandardOutput 'logs/full_run.log' -RedirectStandardError 'logs/full_run.err.log'
Write-Output ("DASH_PID=" + $d.Id)
Write-Output ("EVAL_PID=" + $e.Id)
Start-Sleep -Seconds 12
Write-Output ("RESULT_FILES=" + (Get-ChildItem results -Filter *.json -ErrorAction SilentlyContinue | Measure-Object).Count)
Write-Output '--- full_run.log tail ---'
if (Test-Path 'logs/full_run.log') { Get-Content 'logs/full_run.log' -Tail 22 }
Write-Output '--- dash.err.log tail ---'
if (Test-Path 'logs/dash.err.log') { Get-Content 'logs/dash.err.log' -Tail 4 }