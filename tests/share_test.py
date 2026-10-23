"""optimize/share.py on a fake run folder: nothing of the owner's may reach the text that is sent.

    python3 tests/share_test.py          (no TV needed)
"""
import os, sys, tempfile
from pathlib import Path
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "optimize"))
import share

ours = next(l.split()[0] for l in open(os.path.join(here, "..", "optimize", "lists", "tcl-safe.txt"))
            if l.strip() and not l.startswith("#"))
share.RUN = Path(tempfile.mkdtemp())
(share.RUN / "run.log").write_text("\n".join([
    "!! adb " + ".".join(["192", "168", "1", "23"]) + ":5555 refused",   # built apart: tests/check.py bars IPs in files
    "!! mac aa:bb:cc:dd:ee:ff and AA-BB-CC-DD-EE-FF",
    r"!! saved C:\Users\Ann Lee\x\run.log",
    r"!! also c:\documents and settings\Ann Lee\x",
    "!! /home/ann/x and /Users/Ann Lee/y and /c/Users/ann/z",
]), encoding="utf-8")
(share.RUN / "report.md").write_text("\n".join([
    "- ok: com.android.vending",
    "- home hides: com.thirdparty.secretapp | no TV activity",
    "- home hides: com.other.private | no TV activity",
    "- home hides: com.third.cfg | config.xml",
    f"- home hides: {ours} | config.xml",
]), encoding="utf-8")

text = share.scrub("\n".join(share.trouble() + share.report_checks()))
leaks = [w for w in ("192.168", "aa:bb", "AA-BB", "Ann", "Lee", "/ann", "secretapp", "other.private", "third.cfg")
         if w.lower() in text.lower()]
counts = "2 no TV activity" in text and "1 config.xml" in text and ours in text
print("share: " + ("nothing personal left, counts kept" if not leaks and counts else "WRONG")
      + (f", leaked {leaks}" if leaks else ""))

def keep_off(*pkgs):   # report lines naming these keep packages as off
    return share.packages([f"- pkg off: {p} (keep)" for p in pkgs])


by_design = [l for l in keep_off("com.google.android.apps.tv.launcherx") if l.startswith("!!")]
real = [l for l in keep_off("com.google.android.tungsten.setupwraith", "com.tcl.airplay2") if l.startswith("!!")]
alarm = not by_design and real == ["!! protected but off: com.tcl.airplay2"]
print("share: " + ("off-by-design keep packages not flagged, others still are" if alarm else f"WRONG alarm {by_design} {real}"))
sys.exit(1 if leaks or not counts or not alarm else 0)
