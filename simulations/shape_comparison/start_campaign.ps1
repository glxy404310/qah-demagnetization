param([int]$WaitPid = 0)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
$controllerPath = Join-Path $PSScriptRoot 'controller.json'
if (Test-Path -LiteralPath $controllerPath) {
    $prior = Get-Content -Raw -LiteralPath $controllerPath | ConvertFrom-Json
    $live = Get-CimInstance Win32_Process -Filter "ProcessId = $($prior.pid)" -ErrorAction SilentlyContinue
    if ($live -and $live.CommandLine -like '*continue_campaign.py*' -and $WaitPid -ne $prior.pid) {
        throw "Existing campaign controller is still running: $($prior.pid)"
    }
}
$taskStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$taskOut = Join-Path $PSScriptRoot "campaign_$taskStamp.log"
$taskErr = Join-Path $PSScriptRoot "campaign_$taskStamp.errors.log"
$taskArgs = @('-u','simulations/shape_comparison/continue_campaign.py')
if ($WaitPid -gt 0) { $taskArgs += @('--wait-pid', "$WaitPid") }
$env:PYTHONUTF8 = '1'
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskArgs -WorkingDirectory $taskRoot -WindowStyle Hidden -RedirectStandardOutput $taskOut -RedirectStandardError $taskErr -PassThru
@{pid=$taskProcess.Id; started=(Get-Date -Format o); stdout=$taskOut; stderr=$taskErr; wait_pid=$WaitPid} | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath (Join-Path $PSScriptRoot 'launch.json')
Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'launch.json')
