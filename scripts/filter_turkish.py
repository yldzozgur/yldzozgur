"""
Reads LinkedIn's Connections.csv export, filters to Turkish-named contacts,
writes a plain-text list of full names to turkish_names.txt (one per line).

That output is the input for the userscript that does the actual unfollowing
inside the browser.

Usage:
    python3 scripts/filter_turkish.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "Connections.csv"
OUT_PATH = HERE / "turkish_names.txt"
REVIEW_PATH = HERE / "turkish_review.csv"  # full rows for manual sanity check

# Same heuristic as linkedin_cleanup.py — keep them in sync if you tweak.
TURKISH_FIRST_NAMES = {
    "mehmet","ahmet","mustafa","ali","hüseyin","huseyin","hasan","ibrahim",
    "ismail","osman","yusuf","murat","emre","burak","can","cem","deniz",
    "eren","furkan","gökhan","gokhan","hakan","kaan","kerem","levent","mert",
    "onur","ozan","serkan","tolga","tuna","uğur","ugur","volkan","yağız",
    "yagiz","yiğit","yigit","zafer","özgür","ozgur","çağrı","cagri","şahin",
    "sahin","şükrü","sukru","ümit","umit","ilker","berk","alper","anıl",
    "anil","arda","aykut","barış","baris","batuhan","bilal","bora","buğra",
    "bugra","burhan","caner","cenk","doğan","dogan","ediz","efe","ekrem",
    "ender","ergin","ersin","ertuğrul","ertugrul","fatih","ferhat","halil",
    "hamza","kadir","kemal","koray","kürşat","kursat","mahmut","metin",
    "necati","nuri","okan","oktay","orhan","ömer","omer","rıza","riza",
    "sabri","sedat","selçuk","selcuk","selim","serdar","sinan","süleyman",
    "suleyman","taner","tarık","tarik","taylan","timur","tunç","tunc",
    "turgay","turgut","veli","yalçın","yalcin","yavuz","abdullah","doruk",
    "engin","gürkan","gurkan","haluk","harun","ilhan","kayhan","macit",
    "muhammet","muhammed","mücahit","nazım","nazim","okay","rahmi","rüstem",
    "rustem","samet","savaş","savas","şener","sener","tamer","ufuk",
    "yiğitcan","yigitcan","ataberk","aytaç","aytac","bayram",
    "ayşe","ayse","fatma","emine","hatice","zeynep","elif","sevgi","selin",
    "pınar","pinar","gül","gul","esra","merve","büşra","busra","tuğçe",
    "tugce","aslı","asli","sibel","özge","ozge","çiğdem","cigdem","şule",
    "sule","defne","ebru","ece","eda","aysu","ceyda","dilek","duygu","funda",
    "gamze","gizem","hande","irem","melis","nazlı","nazli","nesrin","nihal",
    "nilgün","nilgun","pelin","sema","şeyma","seyma","tuba","yasemin","ayla",
    "aylin","ayşegül","aysegul","begüm","begum","berna","beste","betül",
    "betul","burcu","buse","canan","cansu","ceren","demet","derya","didem",
    "dilara","dilay","dilruba","ela","emel","evrim","fadime","ferda","feride",
    "fulya","gönül","gonul","gülbahar","gülçin","gulcin","gülşah","gulsah",
    "günay","gunay","handan","hülya","hulya","hilal","ilknur","inci","ipek",
    "irmak","kübra","kubra","lale","leyla","meltem","meral","müge","muge",
    "nagehan","nehir","nesibe","neslihan","nuray","oya","öykü","oyku",
    "perihan","rabia","saliha","şebnem","sebnem","sedef","selma","semra",
    "senem","serap","sevda","sevil","sevim","şeyda","seyda","şirin","sirin",
    "songül","songul","şükran","sukran","tülay","tulay","ümran","umran",
    "yelda","yıldız","yildiz","zehra","zerrin","hira",
}
TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")
TURKISH_SURNAME_SUFFIXES = ("oğlu", "oglu", "gil")


def looks_turkish(first: str, last: str) -> tuple[bool, str]:
    full = f"{first} {last}".strip()
    if not full:
        return False, ""
    f = first.lower().strip(".,")
    if f in TURKISH_FIRST_NAMES:
        return True, f"first:{f}"
    if any(ch in TURKISH_CHARS for ch in full):
        return True, "tr-char"
    l = last.lower().strip(".,")
    for suf in TURKISH_SURNAME_SUFFIXES:
        if l.endswith(suf):
            return True, f"suffix:{suf}"
    return False, ""


def main() -> int:
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found.", file=sys.stderr)
        print("LinkedIn → Settings → Data Privacy → Get a copy of your data → Connections.", file=sys.stderr)
        return 1

    # LinkedIn CSV has a header preamble; the actual header row starts with "First Name,Last Name,..."
    raw = CSV_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    header_idx = next(
        (i for i, line in enumerate(raw) if line.lower().startswith("first name,")),
        0,
    )
    rows = list(csv.DictReader(raw[header_idx:]))
    print(f"loaded {len(rows)} connections")

    matches: list[tuple[str, str, dict]] = []
    for r in rows:
        first = (r.get("First Name") or "").strip()
        last = (r.get("Last Name") or "").strip()
        is_tr, reason = looks_turkish(first, last)
        if is_tr:
            matches.append((f"{first} {last}".strip(), reason, r))

    OUT_PATH.write_text("\n".join(m[0] for m in matches) + "\n", encoding="utf-8")
    with REVIEW_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Full Name", "Reason", "Company", "Position", "Connected On", "URL"])
        for name, reason, r in matches:
            w.writerow([
                name,
                reason,
                r.get("Company", ""),
                r.get("Position", ""),
                r.get("Connected On", ""),
                r.get("URL", ""),
            ])

    print(f"matched {len(matches)} Turkish-named connections")
    print(f"  → names: {OUT_PATH}")
    print(f"  → review CSV (with company/title): {REVIEW_PATH}")
    print()
    print("ÖNERİ: turkish_review.csv'yi açın, yanlış işaretlenmiş olanları silin")
    print("(yine de userscript'e tam listeyi vermeden önce göz gezdirin).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
