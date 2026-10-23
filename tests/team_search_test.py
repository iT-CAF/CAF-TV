#!/usr/bin/env python3
"""Club search, offline: optimize/team_search.py (find-team) and TeamSearch.java (the TV settings screen) on our list,
assets/shared/teams.json. Every case in tests/team_search_cases.tsv must pass in both, and the two must give the same
results, in the same order, for every name in the list and for spellings of it (no hyphens, no «ال», no harakat).
The Java half needs javac; without it, it is skipped with a note.   Run: python3 tests/team_search_test.py"""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("team_search", ROOT / "optimize/team_search.py")
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)
CLUBS = json.loads((ROOT / "assets/shared/teams.json").read_text(encoding="utf-8"))
failed = 0


def check(name, ok, detail=""):
    global failed
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))
    failed += not ok


def cases():
    for line in (ROOT / "tests/team_search_cases.tsv").read_text(encoding="utf-8").split("\n"):
        if not line or line.startswith("#"):   # a case for the empty query is a line starting with a tab
            continue
        q, first, has, hasnt = (line.split("\t") + ["", "", ""])[:4]
        yield q, first, [i for i in has.split(",") if i], [i for i in hasnt.split(",") if i]


def judge(label, q, first, has, hasnt, ids):
    got = ids[0] if ids else "-"
    ok = (got == first) if first != "-" else (bool(ids) if has else not ids)
    ok = ok and all(i in ids for i in has) and not any(i in ids for i in hasnt)
    check(f"{label} {q!r} -> {first}" + (f" with {','.join(has)}" if has else "")
          + (f" without {','.join(hasnt)}" if hasnt else ""), ok, ids[:6])


CASES = list(cases())
for q, first, has, hasnt in CASES:
    judge("python", q, first, has, hasnt, [c["id"] for c in ts.search(CLUBS, q)])

# things that must not crash
for q in [None, 12345, "x" * 5000, "‏‎", "%s%d{}", "ـــ", "الالالال", "\x00", "a" + "́" * 50]:
    try:
        ts.search(CLUBS, q)
        check(f"python: no crash on {str(q)[:20]!r}", True)
    except Exception as e:  # noqa: BLE001
        check(f"python: no crash on {str(q)[:20]!r}", False, e)
check("python: a broken list entry is skipped, not a crash",
      isinstance(ts.search([{"id": "1"}, None, {"en": 5, "ar": None}], "hilal"), list))

# every club can be found by its own names, as people write them
spellings = [s for c in CLUBS for name in filter(None, [c.get("en"), c.get("ar")])
             for s in (name, name.replace("-", " "), name.upper(), name.replace("ال", "", 1), name.replace("ة", "ه"))]
not_found = [(c["id"], c[k]) for c in CLUBS for k in ("en", "ar") if c.get(k) and c["id"] not in [x["id"] for x in ts.search(CLUBS, c[k])]]
check("every club is found by its English and Arabic name", not not_found, not_found[:8])
first_not_saudi = [c["ar"] for c in CLUBS if c.get("ar") and any("Saudi" in l for l in c["leagues"])
                   and ts.search(CLUBS, c["ar"])[0]["id"] != c["id"]]
check("a Saudi club's Arabic name finds that club first", not first_not_saudi, first_not_saudi[:8])

# the Java twin: same results, same order
javac, java = shutil.which("javac"), shutil.which("java")
if not (javac and java):
    print("SKIP TeamSearch.java: no javac here (CI's Build APKs compiles it)")
else:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        clean = lambda s: str(s or "").replace("\t", " ").replace("\n", " ").replace(";", " ")   # noqa: E731
        (tmp / "teams.tsv").write_text("".join(
            f"{clean(c['id'])}\t{clean(c['en'])}\t{clean(c.get('ar'))}\t{';'.join(map(clean, c['leagues']))}\t"
            f"{';'.join(map(clean, c.get('alt') or []))}\n" for c in CLUBS), encoding="utf-8")
        queries = [q for q, *_ in CASES] + spellings + ["x" * 5000, "ـــ", "الالالال", "a" + "́" * 50]
        queries = [clean(q) for q in queries]
        (tmp / "queries.txt").write_text("\n".join(queries) + "\n", encoding="utf-8")
        src = ROOT / "android/app/src/main/java/sa/urtv/screensaver/TeamSearch.java"
        r = subprocess.run([javac, "-encoding", "UTF-8", "-d", str(tmp), str(src), str(ROOT / "tests/TeamSearchRun.java")],
                           capture_output=True, text=True)
        check("TeamSearch.java compiles", r.returncode == 0, r.stderr[-600:])
        if r.returncode == 0:
            r = subprocess.run([java, "-cp", str(tmp), "sa.urtv.screensaver.TeamSearchRun", str(tmp / "teams.tsv"),
                                str(tmp / "queries.txt")], capture_output=True)
            lines = r.stdout.decode("utf-8").split("\n")
            check("TeamSearch.java runs", r.returncode == 0 and len(lines) >= len(queries), r.stderr.decode()[-600:])
            java_ids = [l.split(",") if l else [] for l in lines[:len(queries)]]
            for (q, first, has, hasnt), ids in zip(CASES, java_ids):
                judge("java", q, first, has, hasnt, ids)
            differ = [(q, py, jv[:5]) for q, jv in zip(queries, java_ids)
                      if (py := [c["id"] for c in ts.search(CLUBS, q)]) != jv]
            check(f"java and python agree on all {len(queries)} queries", not differ, [(q, p[:5], j) for q, p, j in differ[:6]])

print("\nall team search checks passed" if not failed else f"\n{failed} failed")
sys.exit(1 if failed else 0)
