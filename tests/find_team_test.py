#!/usr/bin/env python3
"""optimize/find-team.py against our club list, offline: TheSportsDB's search is replaced by one that fails the
test, since every club asked here must come from assets/shared/teams.json. Run: python3 tests/find_team_test.py"""
import importlib.util
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

spec = importlib.util.spec_from_file_location("find_team", Path(__file__).resolve().parents[1] / "optimize/find-team.py")
fteam = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fteam)
searched = []
fteam.search = lambda name: searched.append(name) or []
failed = 0


def check(name, ok, detail=""):
    global failed
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))
    failed += not ok


def run(*args):
    sys.argv = ["find-team.py", *args]
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            fteam.main()
    except SystemExit as e:
        out.write(str(e))
    return out.getvalue()


for q, want in [("الهلال", "136013"), ("النصر", "136022"), ("السعودية", "136137"), ("الزلفي", "150643"),
                ("Real Madrid", "133738"), ("Al Hilal", "136013")]:
    out = run(q)
    check(f"{q} -> {want} first", out.split(":", 1)[0] == want, out.strip()[:200])
leagues = {l for line in run("--list", "Saudi").splitlines() for l in line.rsplit("  |  ", 1)[-1].split(", ")}
check("--list Saudi: both Saudi leagues", len({l for l in leagues if "Saudi" in l}) >= 2, sorted(leagues))
check("no online search", not searched, searched)
# without teams.json (an old checkout): no crash, the online search is used instead
fteam.CLUBS, searched[:] = [], []
fteam.search = lambda name: searched.append(name) or ([{"idTeam": "136013", "strTeam": "Al-Hilal", "strSport": "Soccer",
                                                         "strCountry": "Saudi Arabia"}] if name == "Al-Hilal" else [])
out = run("الهلال")
check("no teams.json: online search", out.startswith("136013:") and searched, out.strip()[:200])
print("\nall find-team checks passed" if not failed else f"\n{failed} failed")
sys.exit(1 if failed else 0)
