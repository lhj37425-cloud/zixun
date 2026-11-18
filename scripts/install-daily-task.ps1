# 注册「今日一拆」每天 9:00 的任务计划；错过 9 点则开机后尽快补跑。
$ErrorActionPreference = "Stop"

$ScriptsDir = $PSScriptRoot
$RepoRoot = (Resolve-Path (Join-Path $ScriptsDir "..")).Path
$Runner = Join-Path $ScriptsDir "run-daily.bat"
$TaskName = "DailyDissect"

if (-not (Test-Path -LiteralPath $Runner)) {
    throw "找不到运行脚本：$Runner"
}

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$Runner`"" `
    -WorkingDirectory $RepoRoot

$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "今日一拆：每天 09:00 自动抓取并生成网页；错过则尽快补跑" | Out-Null

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host "已注册任务计划：$TaskName"
Write-Host "状态：$($task.State)"
Write-Host "时间：每天 09:00（本机时区）"
Write-Host "错过补跑：StartWhenAvailable = $($task.Settings.StartWhenAvailable)"
Write-Host "脚本：$Runner"
Write-Host "日志目录：$(Join-Path $RepoRoot 'logs')"
Write-Host "上次运行：$($info.LastRunTime)（结果码 $($info.LastTaskResult)）"
Write-Host ""
Write-Host "立刻试跑：Start-ScheduledTask -TaskName $TaskName"
Write-Host "卸载：双击 scripts\uninstall-daily-task.bat"
