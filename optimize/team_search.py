"""Search our club list (assets/shared/teams.json) by an Arabic or English name, offline and without crashing.

The TV settings screen has the same code in android/app/.../TeamSearch.java; tests/team_search_cases.tsv runs
against both, so they can't drift apart.

Names are compared after normalising:
  Arabic   harakat and tatweel gone; أ إ آ ٱ -> ا; ة -> ه; ى -> ي; the article ال dropped from every word
  English  lower case, accents gone (Atlético = Atletico), hyphens and dots gone, FC/SC/CF/AFC/Club dropped
Both: «Al-Hilal», «Al Hilal», «alhilal» are one name, and «Hilal» is the same name without its «Al». In English,
spellings that differ only in doubled letters or vowels are one name too («Al-Nasr» = «Al-Nassr», «Wahda» = «Wehda»).

A club matches by how much of its name the query is, best first:
  the same name (exactly, or only in doubled letters and vowels)   the start of a word, or of the name
  the start of every word
Ties: Saudi clubs first (Saudi Al-Ain before the Emirati one, Al-Nassr before Al Nasr), then the exact spelling
(«Mainz» before Monza), then the order of the list.
"""
import re
import unicodedata

HARAKAT = re.compile("[ً-ٰٟـۖ-ۭ]")
ARABIC_LETTERS = str.maketrans("أإآٱةىئؤ", "ااااهييو")
FILLER_AR = {"نادي", "فريق"}          # «نادي الهلال» is «الهلال»
FILLER_EN = {"fc", "sc", "cf", "afc", "sfc", "club", "football", "clube"}
KIND_AR = {"منتخب"}                    # «منتخب السعودية»: dropped from the query only when something else is left


def normalize(text):
    """The words of a name, normalised as described above."""
    s = unicodedata.normalize("NFKD", str(text or "")).replace("ı", "i").replace("ß", "ss")
    s = HARAKAT.sub("", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\b([fs])\.c\.", r"\1c", s.lower())
    s = s.translate(ARABIC_LETTERS)
    words = re.findall(r"[a-z0-9]+|[ء-يٮ-ۓ٠-٩]+", s)
    out = []
    for w in words:
        if re.match("[ء-ي]", w):
            if len(w) > 3 and w.startswith("ال"):
                w = w[2:]
            if w in FILLER_AR:
                continue
        elif w in FILLER_EN:
            continue
        out.append(w)
    return out


def drop_al(words):
    return words[1:] if len(words) > 1 and words[0] == "al" else words


def skeleton(word):
    """«nassr» -> «nsr», «wehda» -> «whd»: an English name without doubled letters or vowels after the first."""
    if not re.fullmatch("[a-z0-9]+", word):
        return ""
    s = re.sub(r"(.)\1+", r"\1", word)
    s = s[0] + re.sub("[aeiouy]", "", s[1:])
    return s if len(s) >= 3 else ""


def tier(q, name):
    """How the query q (normalised words) matches the name: 0 exactly, 1 in doubled letters and vowels only, 2 the
    start of a word or of the name, 3 the start of every word, 9 not at all. 0 and 1 rank together (see GROUP)."""
    if not q or not name:
        return 9
    bare, bare_name = "".join(drop_al(q)), "".join(drop_al(name))
    if "".join(q) == "".join(name) or bare == bare_name or (skeleton(bare) and skeleton(bare) == skeleton(bare_name)):
        return 0 if "".join(q) == "".join(name) or bare == bare_name else 1
    if len(bare) >= 2 and ("".join(name).startswith(bare) or bare_name.startswith(bare)
                           or any(w.startswith(bare) for w in name)):
        return 2
    if all(len(w) >= 2 and any(n.startswith(w) for n in name) for w in drop_al(q)):
        return 3
    return 9


GROUP = {0: 0, 1: 0, 2: 1, 3: 2}   # a misspelt name still ranks as the same name, so the Saudi club wins


ARTICLES = {"ال", "al", "el"}   # a query of nothing else finds nothing


def query_words(query):
    q = normalize(query)
    stripped = [w for w in q if w not in KIND_AR]
    q = stripped or q
    return [] if all(w in ARTICLES for w in q) else q


def names_of(club):
    return [club.get("en"), club.get("ar"), *(club.get("alt") or [])]


def is_saudi(club):
    return any("Saudi" in l for l in club.get("leagues") or [])


def search(clubs, query, limit=None):
    """The clubs matching query, best first; [] for an empty or silly query. Never raises."""
    try:
        q = query_words(query)
        if not q or len("".join(q)) < 2:
            return []
        ranked = []
        for n, club in enumerate(clubs or []):
            t = min((tier(q, normalize(x)) for x in names_of(club) if x), default=9)
            if t < 9:
                ranked.append((GROUP[t], not is_saudi(club), t, n, club))
        ranked.sort(key=lambda r: r[:4])
        found = [r[4] for r in ranked]
        return found[:limit] if limit else found
    except Exception:  # noqa: BLE001  (a bad entry in the list must not take the setup down)
        return []
