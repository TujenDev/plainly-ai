"""What the schedule runs: prices.py once a day, logged, with a notification on trouble.

    pythonw pricewatch.py                                # what the scheduled task runs
    $env:PRICEWATCH_FORCE=1; python pricewatch.py        # PowerShell: run now, past the 09:15 guard

This replaced pricewatch.sh and its launchd agent on 23 September 2026. Those
ran on a Mac, and when the Mac went, nothing replaced them: the site went on
promising a daily check that was not happening, and nothing anywhere said so.
The logic is the same as the shell script's, ported rather than redesigned,
because every rule in it came from a way the watcher had already failed.

prices.py prints and exits non-zero when something moved or could not be
verified. Run from a schedule, that output goes nowhere anybody looks, which
would make the watcher the quiet failure it was written to prevent. So this
appends every run to a log and raises a notification when a run is not clean.

It refuses to cry wolf. With no network, every source fails to fetch and
prices.py correctly reports UNVERIFIED across the board. Alarming about that
would train you to dismiss the notification, which costs more than the missed
run. A reachability probe comes first, and an offline run is logged once a day
and skipped rather than announced. The day's run stays owed, so the next tick
tries again.

It catches up. The task ticks hourly from 09:15 and this decides whether the
day's run is owed: it keeps the date of the last real run and exits at once
until that date is not today. The effect is at most one check a day, at 09:15
if the machine is on then and at the first tick after that if it wasn't. The
Mac's scheduler dropped a run missed while it was powered off, on 27 August
2026, without a trace; the hourly tick is why that cannot recur.

And it says when it slipped. A run that finds days missing since the last one
says so in the log and notifies, because healing the gap quietly would leave the
log agreeing with a promise the site had not kept.

It runs under pythonw, which has no console, so an hourly tick never flashes a
window. The price of that is that nothing it prints is seen by anyone, so every
failure, including a crash in this file, goes to the log and to a notification.
"""
import base64
import os
import pathlib
import subprocess
import sys
import traceback
import urllib.request
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from xml.sax.saxutils import escape

REPO = pathlib.Path(__file__).resolve().parent
if sys.platform == "win32":
    STATE = pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home())) / "plainlyai"
elif sys.platform == "darwin":
    STATE = pathlib.Path.home() / "Library" / "Logs" / "plainlyai"
else:
    STATE = pathlib.Path.home() / ".local" / "state" / "plainlyai"
LOG = STATE / "pricewatch.log"
RAN = STATE / "pricewatch.lastrun"
OFF = STATE / "pricewatch.lastoffline"

UA = "Mozilla/5.0 (compatible; plainlyai-price-watch/1.0; +https://plainlyai.org)"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def stamp():
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def read(path):
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def write(path, text):
    path.write_text(text + "\n", encoding="utf-8")


def log(text):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"=== {stamp()}\n{text}\n\n")


def online():
    """Reachability, not a fetch: one vendor host, short timeout, nothing parsed.

    Any HTTP answer at all, an error status included, means the network is up.
    """
    req = urllib.request.Request("https://platform.claude.com/", method="HEAD",
                                 headers={"User-Agent": UA})
    try:
        urllib.request.urlopen(req, timeout=10)
    except HTTPError:
        return True
    except (URLError, TimeoutError, OSError):
        return False
    return True


def notify(title, body):
    """A Windows toast, or a macOS notification. A failure to notify is logged.

    The toast goes through PowerShell because Windows has no notification call
    Python can reach without a third-party package, and this project has none.
    The script is passed encoded, so nothing in the message can break its quoting.
    """
    try:
        if sys.platform == "win32":
            xml = (f'<toast><visual><binding template="ToastGeneric"><text>{escape(title)}'
                   f'</text><text>{escape(body)}</text></binding></visual></toast>')
            ps = (
                "$ErrorActionPreference='Stop';"
                "[void][Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime];"
                "[void][Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom.XmlDocument,ContentType=WindowsRuntime];"
                "$x=New-Object Windows.Data.Xml.Dom.XmlDocument;"
                f"$x.LoadXml('{xml.replace(chr(39), chr(39) * 2)}');"
                "$app='{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app)"
                ".Show([Windows.UI.Notifications.ToastNotification]::new($x))"
            )
            cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                   base64.b64encode(ps.encode("utf-16-le")).decode("ascii")]
        elif sys.platform == "darwin":
            quoted = lambda s: '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
            cmd = ["/usr/bin/osascript", "-e",
                   f"display notification {quoted(body)} with title {quoted(title)} "
                   f'sound name "Submarine"']
        else:
            return
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                           creationflags=NO_WINDOW)
        if r.returncode != 0:
            log(f"notification failed ({r.returncode}): {(r.stderr or r.stdout).strip()}")
    except Exception as e:                       # a broken notifier must not hide the run
        log(f"notification failed: {e!r}")


def python_exe():
    """The console interpreter beside this one, so the child's output can be captured.

    Under pythonw, sys.executable is pythonw.exe. python.exe sits next to it; run
    with CREATE_NO_WINDOW it still shows nothing.
    """
    exe = pathlib.Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and (exe.parent / "python.exe").exists():
        return str(exe.parent / "python.exe")
    return str(exe)


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    prev = read(RAN)

    # Already checked today. Every hourly tick after the day's run lands here.
    if prev == today:
        return 0

    # Before the nominal time, wait. The hourly tick is here to catch up on a day
    # that was missed, not to move the check earlier. PRICEWATCH_FORCE=1 skips
    # this, so the whole path can be exercised at any hour.
    if not os.environ.get("PRICEWATCH_FORCE"):
        now = datetime.now()
        if (now.hour, now.minute) < (9, 15):
            return 0

    if not online():
        if read(OFF) != today:
            log("offline, skipped")
            write(OFF, today)
        return 0

    # Days skipped since the last real run. Absent on a first run, which is not a gap.
    gap = ""
    if prev:
        try:
            days = (date.fromisoformat(today) - date.fromisoformat(prev)).days
        except ValueError:
            gap = f"the last-run record is unreadable ({prev!r}), so a gap cannot be ruled out"
        else:
            if days >= 2:
                gap = f"missed {days - 1} scheduled run(s): last ran {prev}"

    env = dict(os.environ, PYTHONUTF8="1")
    try:
        r = subprocess.run([python_exe(), str(REPO / "prices.py")], cwd=REPO, env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900, creationflags=NO_WINDOW)
        out, status = (r.stdout + r.stderr).strip("\r\n"), r.returncode
    except subprocess.TimeoutExpired:
        out, status = "prices.py did not finish within 15 minutes and was stopped", 124

    log("\n".join(x for x in (gap, out, f"exit {status}") if x))
    write(RAN, today)

    if status != 0:
        summary = next((l.strip() for l in out.splitlines() if "figures checked" in l),
                       f"prices.py exited {status}")
        notify("Plainly: Model facts needs a look", summary)
    elif gap:
        notify("Plainly: the price watcher slipped", gap)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Under pythonw a crash is otherwise invisible, which is the one outcome
        # this file exists to prevent.
        try:
            STATE.mkdir(parents=True, exist_ok=True)
            log("pricewatch.py crashed:\n" + traceback.format_exc())
        finally:
            notify("Plainly: the price watcher crashed", f"see {LOG}")
        sys.exit(1)
