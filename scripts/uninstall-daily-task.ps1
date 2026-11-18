# 卸载「今日一拆」每天 9:00 的任务计划。
$ErrorActionPreference = "Stop"
$TaskName = "DailyDissect"

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "没有找到任务计划：$TaskName（可能已经卸过了）"
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "已卸载任务计划：$TaskName"
