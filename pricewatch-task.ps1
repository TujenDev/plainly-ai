# Registers the daily price watch with Windows Task Scheduler. Run it once, by
# hand, from this folder; run it again after moving the repo or reinstalling
# Python. It replaces the task of the same name rather than adding a second.
#
#     powershell -NoProfile -ExecutionPolicy Bypass -File pricewatch-task.ps1
#
# One trigger, at 09:15 and then every hour, indefinitely. The hours after 09:15
# are not extra checks: pricewatch.py runs prices.py at most once a day and exits
# at once on every other tick. They are there so a day the machine was off at
# 09:15 is still checked once it is back on. StartWhenAvailable adds the same for
# a tick missed while it was off, rather than waiting for the next one.
#
# It runs as you, only while you are logged on, because that is the session a
# notification can reach. pythonw has no console, so a tick shows no window.
#
# To stop it:  Unregister-ScheduledTask -TaskName 'Plainly price watch' -Confirm:$false
# The watcher's log is %LOCALAPPDATA%\plainlyai\pricewatch.log.

$ErrorActionPreference = 'Stop'

$repo = $PSScriptRoot
$script = Join-Path $repo 'pricewatch.py'
if (-not (Test-Path $script)) { throw "pricewatch.py is not beside this script in $repo" }

# The real interpreter, not the Microsoft Store stub that shares its name.
$pythonw = Get-Command pythonw.exe -All -ErrorAction SilentlyContinue |
    Where-Object { $_.Source -notmatch '\\WindowsApps\\' } |
    Select-Object -First 1
if (-not $pythonw) { throw 'pythonw.exe was not found on PATH (the WindowsApps stub does not count)' }

$user = "$env:USERDOMAIN\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute $pythonw.Source -Argument "`"$script`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At ([datetime]::Today.AddHours(9).AddMinutes(15)) `
    -RepetitionInterval (New-TimeSpan -Hours 1)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName 'Plainly price watch' -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force `
    -Description 'Runs pricewatch.py from the plainly-ai repo: prices.py once a day from 09:15, hourly catch-up, notifies when Model facts needs a look.' |
    Out-Null

$t = Get-ScheduledTask -TaskName 'Plainly price watch'
"Registered '$($t.TaskName)': $($pythonw.Source) `"$script`""
"Repeats every $($t.Triggers[0].Repetition.Interval), duration '$($t.Triggers[0].Repetition.Duration)' (empty means indefinitely)"
"Next run: $((Get-ScheduledTaskInfo -TaskName 'Plainly price watch').NextRunTime)"
