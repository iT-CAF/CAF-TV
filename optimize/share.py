#!/usr/bin/env python3
"""Write how the setup went, for its owner to send to CAF TV's author if they want to (optimize/share.sh).

Only what helps fix the setup for others: the TV (maker, model, firmware, Android), the computer's system, the agent,
CAF TV's version and the apps', how long each step took and where it stopped, the errors and dropped connections,
memory before and after, the checks, the agent's notes and the owner's own words if they want to add any.
Nothing personal: no city, clubs, favourites or apps of theirs, no names, network addresses or file paths.

    optimize/share.sh --agent "Codex (gpt-…)" --owner "the owner's words, if any" "the agent's notes"
"""
import argparse
import datetime
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

for stream in (sys.stdout, sys.stderr):   # Windows writes pipes in its own code page
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace", newline="\n")

RUN = Path(__file__).resolve().parent / "run"
OUT = RUN / "share.md"
QR = RUN / "share-qr.png"
# The author's Google Form (anonymous, no sign-in): each summary becomes a row in the author's sheet. The same two
# values are in docs/share/index.html.
FORM_ID = "1FAIpQLSfDJFfy1NgiB-ZMXoBI29n_KTdYnGadn1-iOqXJOxaQJEr-ZQ"   # from the form's link: docs.google.com/forms/d/e/<FORM_ID>/viewform
FORM_FIELD = "1457112794"   # the question's number: entry.<FORM_FIELD>=… in the form's pre-filled link
# Without the form, or offline: the QR code opens this page (docs/share/, GitHub Pages) with the summary after the #
PAGE = "https://iT-CAF.github.io/CAF-TV/share/"


def scrub(text):   # in case a note or an output carries something personal
    text = re.sub(r"\b\d{1,3}(\.\d{1,3}){3}(:\d+)?\b", "<ip>", text)
    text = re.sub(r"\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    # the user folder may hold spaces ("Ann Lee"): it runs to the next separator or the end of the line
    text = re.sub(r"(?i)\b[A-Z]:[\\/]+(Users|Documents and Settings)[\\/]+[^\\/\r\n]+", "<home>", text)
    text = re.sub(r"(?i)(/c)?/Users/[^/\r\n]+|/home/[^/\r\n]+", "<home>", text)
    return text


def tv():
    props = dict(re.findall(r"^(\S+) = (.*)$", (RUN / "tv.txt").read_text(encoding="utf-8"), re.M))
    return (f"{props.get('ro.product.manufacturer', '?')} {props.get('ro.product.model', '?')} "
            f"({props.get('ro.product.device', '?')}), Android {props.get('ro.build.version.release', '?')} "
            f"(SDK {props.get('ro.build.version.sdk', '?')}), firmware {props.get('ro.build.display.id', '?')}")


def urtv_version():   # this copy of the repo: its last commit
    try:
        out = subprocess.run(["git", "-C", str(RUN.parent.parent), "log", "-1", "--format=%h %cs"],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        return out or "?"
    except Exception:  # noqa: BLE001
        return "?"


def trouble():   # from run.log: what the scripts said went wrong, and how often ADB dropped
    log = RUN / "run.log"
    if not log.exists():
        return []
    lines = [l.strip() for l in re.split(r"[\r\n]+", log.read_text(encoding="utf-8", errors="replace"))]
    errors = list(dict.fromkeys(l for l in lines if l.startswith("!!") or " !! " in l))[:8]
    drops = sum("(connection problem" in l for l in lines)
    resumed = sum(l.startswith("resuming upload") for l in lines)
    out = [f"ADB: {drops} dropped connections (retried), {resumed} resumed uploads"]
    return out + [f"- {l}" for l in errors]


def computer():
    name = platform.system()
    if name == "Windows" or "MINGW" in name.upper() or "MSYS" in name.upper():
        return f"Windows {platform.release()}"
    return {"Darwin": f"macOS {platform.mac_ver()[0]}"}.get(name, f"{name} {platform.release()}")


def steps():
    log = RUN / "steps.log"
    if not log.exists():
        return ["(no steps.log: an older run.sh)"]
    lines, started, first, last, stopped_at = [], {}, None, None, None
    for row in log.read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\S+ \S+) (start|done|stopped) (\S+)(.*)", row)
        if not m:
            continue
        t = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        first, last = first or t, t
        what, step = m.group(2), m.group(3)
        if what == "start":
            started[step] = t
            if stopped_at:   # the time between a stop and the next try went into finding out why
                gap = int((t - stopped_at).total_seconds())
                lines.append(f"[{gap // 60}:{gap % 60:02d} until it was run again]")
                stopped_at = None
        elif step in started:
            took = int((t - started.pop(step)).total_seconds())
            lines.append(f"{step} {took // 60}:{took % 60:02d}" + ("" if what == "done" else f" STOPPED{m.group(4)}"))
            stopped_at = t if what == "stopped" else None
    total = f"{int((last - first).total_seconds()) // 60} min in all" if first else ""
    return [", ".join(lines), total] if lines else [total]


def memory(summary):   # summary.md's table as short lines: they read better in a message and fit a QR code
    if not summary.exists():
        return ["(not measured)"]
    rows = [[c.strip() for c in l.strip("|").split("|")] for l in summary.read_text(encoding="utf-8").splitlines()
            if l.startswith("|") and not l.startswith("|---")]
    if not rows:
        return ["(not measured)"]
    head, out = rows[0], []
    total = "".join(ch for ch in (head[1] if len(head) > 1 else "") if ch.isdigit())
    for r in rows[1:]:
        if len(r) < 6 or not r[1].isdigit():
            out.append(f"- {r[0]}: {r[1] if len(r) > 1 else ''}")
            continue
        out.append(f"- {r[0]}: {r[1]} MB free{' of ' + total if total else ''}, {r[2]} MB swap, {r[3]} processes, "
                   f"{r[4] or '?'} CPU idle, {r[5]} disabled")
    return out


def report_checks():
    report = RUN / "report.md"
    if not report.exists():
        return ["(no report.md yet: the setup didn't finish)"]
    lines = report.read_text(encoding="utf-8").splitlines()
    ok = sum(l.startswith("- ok:") for l in lines)
    bad = [l[2:] for l in lines if l.startswith("- !!")]
    out = [f"Protected features on: {ok}/{ok + len(bad)}", *bad,
           *[l for l in lines if l.startswith(("Home:", "Screensaver:", "Versions:", "Extras:", "Optional picks"))]]
    return out + packages(lines)


# in keep.txt but off by design once our home is in: install.sh launcher turns them off; keep.sh leaves them too
OFF_BY_DESIGN = {"com.google.android.apps.tv.launcherx", "com.google.android.tvlauncher",
                 "com.google.android.tungsten.setupwraith", "com.tcl.keycustomfunctionservice"}


def packages(lines):   # what our lists turned off, what they left on, and what the home screen hides
    state = {}   # (state, list) -> packages
    for l in lines:
        m = re.match(r"- pkg (off|on|absent): (\S+) \((\S+)\)", l)
        if m:
            state.setdefault((m.group(1), m.group(3)), []).append(m.group(2))
    out = []
    for lst in ("tcl-safe", "tcl-optional", "home-replaced"):
        off, on = state.get(("off", lst), []), state.get(("on", lst), [])
        absent = len(state.get(("absent", lst), []))
        if off or on or absent:
            out.append(f"{lst}: {len(off)} off, {len(on)} still on, {absent} not on this TV")
            out += [f"  off: {', '.join(off)}"] if off else []
            out += [f"  on: {', '.join(on)}"] if on else []
    protected = [p for p in state.get(("off", "keep"), []) if p not in OFF_BY_DESIGN]
    if protected:
        out.append(f"!! protected but off: {', '.join(protected)}")
    out += hidden(lines)
    return out


def hidden(lines):   # the home screen's "package | reason" lines: the owner's own apps only as counts per reason
    ours = {l.split()[0] for f in (Path(__file__).resolve().parent / "lists").glob("*.txt")
            for l in f.read_text(encoding="utf-8").splitlines() if l.strip() and not l.lstrip().startswith("#")}
    reasons, named = {}, []
    for l in lines:
        if not l.startswith("- home hides: "):
            continue
        pkg, _, why = l[len("- home hides: "):].partition(" | ")
        if not why:
            continue
        if pkg.strip() in ours:
            named.append(f"{pkg.strip()} ({why.strip()})")
        else:
            reasons[why.strip()] = reasons.get(why.strip(), 0) + 1
    out = []
    if reasons:
        out.append("home hides: " + ", ".join(f"{n} {why}" for why, n in reasons.items()))
    if named:
        out.append("home hides, from our lists: " + ", ".join(named))
    return out


def main():
    if not (RUN / "tv.txt").exists():
        sys.exit("!! No setup results here (optimize/run/tv.txt): run the setup first.")
    a = argparse.ArgumentParser(description="Send the author how the setup went (nothing personal).")
    a.add_argument("--agent", default="", help="which agent ran the setup, and its model")
    a.add_argument("--owner", default="", help="the owner's own words for the author, if they gave any")
    a.add_argument("notes", nargs="*", help="the agent's notes: what failed or was slow, and what fixed it")
    args = a.parse_args()
    notes = " ".join(args.notes).strip()
    summary = RUN / "summary.md"
    parts = [
        f"CAF TV setup report, {datetime.date.today()}, CAF TV {urtv_version()}",
        "",
        f"TV: {tv()}",
        f"Computer: {computer()}" + (f", agent: {args.agent}" if args.agent else ""),
        "",
        "Steps, minutes:seconds:",
        *steps(),
        *trouble(),
        "",
        "Memory:",
        *memory(summary),
        "",
        "Checks:",
        *report_checks(),
    ]
    if notes:
        parts += ["", "Notes from the agent:", notes]
    if args.owner.strip():
        parts += ["", "From the owner:", args.owner.strip()]
    text = scrub("\n".join(parts)) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved in {OUT.relative_to(RUN.parent.parent)}.")
    if send(text):
        print("Sent to the author. Thank you!")
        return
    # not sent from here (no internet?): a QR code carries it to the phone, whose page sends it
    if qr(PAGE + "#" + urllib.parse.quote(text)):
        print(f"QR code: {QR.relative_to(RUN.parent.parent)}" + (" (open on this screen)" if show(QR) else ""))
        print("Scan it with the phone's camera: a page opens with this text and a button that sends it.")


def send(text):
    """Into the author's Google Form, anonymously; False if it didn't go through."""
    url = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"
    data = urllib.parse.urlencode({f"entry.{FORM_FIELD}": text}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as r:
            return r.status == 200
    except Exception as e:  # noqa: BLE001
        print(f"(couldn't send it from this computer: {e})")
        return False


def qr(link):
    try:
        import segno
    except ImportError:
        print("(no QR code: optimize/share.sh installs segno when it runs, and that did not work: no internet for pip?)")
        return False
    try:
        segno.make(link, error="l").save(str(QR), scale=6, border=4)
    except segno.DataOverflowError:
        print("(too long for a QR code: send it from a computer with internet: optimize/share.sh again)")
        return False
    return True


def show(path):
    """Open the picture on this computer's screen, if there is a way."""
    try:
        if sys.platform == "win32" or os.environ.get("MSYSTEM"):
            os.startfile(str(path))   # noqa: S606  (Windows' own viewer)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True, timeout=20)
        elif shutil.which("xdg-open"):
            subprocess.run(["xdg-open", str(path)], check=True, timeout=20, capture_output=True)
        else:
            return False
        return True
    except Exception:  # noqa: BLE001
        return False


if __name__ == "__main__":
    main()
