# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Runs the solution of every lab of USE-SEC-207 against the file pack and prints PASS per lab.

  uv run labs/solutions/check.py            # every lab
  uv run labs/solutions/check.py 1.3 2.2    # some labs

Standard library only. It reads labs/files/ (what participants get) and labs/solutions/ (the
completed sheets and key.json), recomputes every number a lab asks for from the participants'
files, and checks that the completed sheets, the start files and the key agree with it. It writes
nothing and calls no model: the outputs of Marji', Ihkam, Mahdar, Asbaqiyya and Tarjih are
recorded, authored stand-ins with planted errors.
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parent.parent
FILES = LABS / "files"
SOL = LABS / "solutions"
KEY = json.loads((SOL / "key.json").read_text(encoding="utf-8"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f}%"


def say(lab: str, *lines: str) -> None:
    print(f"== Lab {lab}")
    for line in lines:
        print("  " + line)
    print("  PASS")


# ------------------------------------------------------------------ 1.1

def lab_1_1() -> None:
    sheet = rows(SOL / "sort_sheet.csv")
    given = rows(FILES / "deployments" / "sort_sheet.csv")
    assert [r["الرقم"] for r in sheet] == [r["الرقم"] for r in given] and len(given) == 10
    assert all(r["الوصف"] == g["الوصف"] for r, g in zip(sheet, given))
    assert {r["الرقم"]: r["الفئة"] for r in sheet} == KEY["1.1"]
    decide = [k for k, v in KEY["1.1"].items() if v.startswith("يُبنى")]
    say("1.1", f"10 deployments; inform decisions about people: {', '.join(decide)} ({len(decide)})",
        "pass mark: 8 of 10 correct")


# ------------------------------------------------------------------ 1.2 and 1.3: citations

def corpus() -> tuple[dict, dict]:
    laws = {}
    for code in ("L1", "L2", "L3", "L4"):
        for m in re.finditer(r"^المادة (\d+): (.*)$", text(FILES / "corpus" / f"{code}.txt"), re.M):
            laws[f"{code} م{m.group(1)}"] = m.group(2)
    judgments = {}
    for block in text(FILES / "corpus" / "judgments.txt").split("\n\n"):
        m = re.search(r"الحكم (.+)\nالمحكمة: .* · الحالة: (.+)\nالمبدأ: (.+)", block)
        if m:
            judgments[m.group(1).strip()] = (m.group(2).strip(), m.group(3).strip())
    return laws, judgments


def classify(c: dict, laws: dict, judgments: dict) -> str:
    ref, claim, evidence = c["المرجع كما ذكره «مرجع»"], c["ما استند إليه «مرجع»"], c["الدليل"]
    if ref in laws:
        source, status = laws[ref], "النافذ"
    elif ref in judgments:
        status, source = judgments[ref]
    else:
        return "مختلق"
    if status.startswith("نُقض"):
        return "متجاوَز"
    if "عُدّلت" in source:
        before = re.search(r"«(.+?)»", source.split("عُدّلت")[1]).group(1)
        if any(w in claim for w in before.split() if len(w) > 4):
            return "متجاوَز"
    quoted = re.search(r"«(.+?)»", claim)
    if quoted and quoted.group(1) not in source and not quoted.group(1).startswith("خطر"):
        return "اقتباس غير موجود"
    if evidence in source:
        return "سليم"
    return "لا يدعم القول"


def audit(part: str) -> list[dict]:
    laws, judgments = corpus()
    scored = rows(SOL / "audit_sheet_scored.csv")
    out = []
    for c in scored:
        got = classify(c, laws, judgments)
        assert got == c["الحكم"] == KEY["citations"][c["المرجع"]], (c["المرجع"], got, c["الحكم"])
        out.append(c)
    given = rows(FILES / "research" / f"audit_sheet_{part}.csv")
    ids = {g["المرجع"] for g in given}
    return [c for c in out if c["المرجع"] in ids]


def summary(cs: list[dict]) -> str:
    bad = [c for c in cs if c["الحكم"] != "سليم"]
    kinds = {}
    for c in bad:
        kinds[c["الحكم"]] = kinds.get(c["الحكم"], 0) + 1
    qs = sorted({c["السؤال"] for c in cs})
    bad_q = sorted({c["السؤال"] for c in bad})
    return (f"{len(cs)} citations, {len(bad)} faulty ({pct(len(bad), len(cs))}): "
            + ", ".join(f"{k} {v}" for k, v in kinds.items())
            + f"; answers with at least one faulty citation {len(bad_q)} of {len(qs)}: {' '.join(bad_q)}")


def lab_1_2() -> None:
    cs = audit("part1")
    assert len(cs) == 12
    say("1.2", summary(cs))


def lab_1_3() -> None:
    cs = audit("part2")
    start = rows(FILES / "start" / "audit_part1_scored.csv")
    assert start == [c for c in rows(SOL / "audit_sheet_scored.csv") if c["السؤال"] <= "Q06"]
    answers = rows(FILES / "research" / "marji_answers.csv")
    assert len(answers) == 12
    say("1.3", summary(cs), "start file audit_part1_scored.csv matches the solution")


# ------------------------------------------------------------------ 1.4 transcript and translation

def lab_1_4() -> None:
    ref = {r["السطر"]: (r["المتحدث"], r["النص"]) for r in rows(FILES / "transcript" / "hearing_reference.csv")}
    mah = {r["السطر"]: (r["المتحدث"], r["النص"]) for r in rows(FILES / "transcript" / "hearing_mahdar.csv")}
    changed = sorted(k for k in ref if ref[k] != mah[k])
    key = KEY["1.4"]["diffs"]
    assert changed == sorted(key), (changed, sorted(key))
    words = sum(len(t.split()) for _, t in ref.values())
    same = sum(sum(b.size for b in difflib.SequenceMatcher(a=ref[k][1].split(), b=mah[k][1].split()).get_matching_blocks()) for k in ref)
    assert (words, same) == (67, 60), (words, same)
    meaning = [k for k, v in key.items() if v == "يغيّر المعنى"]
    tr = KEY["1.4"]["translation"]
    tr_meaning = [k for k, v in tr.items() if v == "يغيّر المعنى"]
    en = {r["المقطع"]: r["النص الإنجليزي الملزم"] for r in rows(FILES / "transcript" / "clause_translation.csv")}
    assert "half" in en["T1"] and "may" in en["T2"]
    say("1.4", f"transcript: {words} words, {same} matched ({pct(same, words)}), {len(changed)} lines changed, {len(meaning)} change the meaning (lines {' '.join(meaning)})",
        f"translation: {len(tr_meaning)} of {len(tr)} passages change the meaning ({' '.join(tr_meaning)})")


# ------------------------------------------------------------------ 1.5 and 1.6 contracts

def contract_grid() -> list[dict]:
    find = {(r["العقد"], r["الفحص"]): r["حكم «إحكام»"] for r in rows(FILES / "contracts" / "ihkam_findings.csv")}
    key = {(r["العقد"], r["الفحص"]): r for r in rows(FILES / "contracts" / "key.csv")}
    grid = rows(SOL / "review_sheet_scored.csv")
    for g in grid:
        k = (g["العقد"], g["الفحص"])
        truth = key[k]["الحكم المرجعي"]
        ihkam = find[k]
        if truth == "لا ينطبق":
            expect = "لا ينطبق"
        elif ihkam == truth:
            expect = "صحيح"
        elif truth == "مخالف":
            expect = "إغفال"
        else:
            expect = "تنبيه زائف"
        assert g["النتيجة"] == expect and g["الحكم المرجعي"] == truth, (k, g)
        # a missing clause in the key is really missing from the contract text
        body = text(FILES / "contracts" / f"{k[0]}.txt")
        if key[k]["رقم البند"] == "غائب":
            assert truth != "مطابق", k
        else:
            assert f"البند {key[k]['رقم البند']}:" in body, k
    return grid


def contract_summary(grid: list[dict]) -> str:
    issues = [g for g in grid if g["الحكم المرجعي"] == "مخالف"]
    missed = [g for g in grid if g["النتيجة"] == "إغفال"]
    false = [g for g in grid if g["النتيجة"] == "تنبيه زائف"]
    flags = [g for g in grid if g["حكم «إحكام»"] == "مخالف"]
    return (f"true issues {len(issues)}, missed {len(missed)} ({pct(len(missed), len(issues))}): "
            + " ".join(g["العقد"] + "-" + g["الفحص"] for g in missed)
            + f"; flags {len(flags)}, false {len(false)} ({pct(len(false), len(flags))}): "
            + " ".join(g["العقد"] + "-" + g["الفحص"] for g in false))


def lab_1_5() -> None:
    grid = [g for g in contract_grid() if g["العقد"] <= "C05"]
    assert len(grid) == 40
    say("1.5", contract_summary(grid))


def lab_1_6() -> None:
    grid = [g for g in contract_grid() if g["العقد"] > "C05"]
    assert rows(FILES / "start" / "review_part1_scored.csv") == [g for g in rows(SOL / "review_sheet_scored.csv") if g["العقد"] <= "C05"]
    c07 = text(FILES / "contracts" / "C07.txt")
    assert "half the Contract Value" in c07 and "بما لا يتجاوز قيمة العقد" in c07
    say("1.6", contract_summary(grid), "C07: the binding English says half; the Arabic translation drops it")


# ------------------------------------------------------------------ 1.7 error log

def lab_1_7() -> None:
    cs = rows(FILES / "start" / "audit_scored.csv")
    assert cs == rows(SOL / "audit_sheet_scored.csv")
    grid = rows(FILES / "start" / "review_scored.csv")
    assert grid == rows(SOL / "review_sheet_scored.csv")
    bad = [c for c in cs if c["الحكم"] != "سليم"]
    bad_q = {c["السؤال"] for c in bad}
    wrong = KEY["wrong_conclusion"]
    issues = [g for g in grid if g["الحكم المرجعي"] == "مخالف"]
    missed = [g for g in grid if g["النتيجة"] == "إغفال"]
    flags = [g for g in grid if g["حكم «إحكام»"] == "مخالف"]
    false = [g for g in grid if g["النتيجة"] == "تنبيه زائف"]
    fab = [c for c in cs if c["الحكم"] == "مختلق"]
    say("1.7",
        f"research, per citation: {len(bad)} of {len(cs)} ({pct(len(bad), len(cs))}); fabricated {len(fab)}",
        f"research, per answer: {len(bad_q)} of 12 ({pct(len(bad_q), 12)}); wrong conclusion {len(wrong)} of 12 ({pct(len(wrong), 12)})",
        f"contracts: missed {len(missed)} of {len(issues)} ({pct(len(missed), len(issues))}); false flags {len(false)} of {len(flags)} ({pct(len(false), len(flags))})")


# ------------------------------------------------------------------ 1.8 exhibits

def lab_1_8() -> None:
    ex = rows(FILES / "evidence" / "exhibits.csv")
    sol = {r["الرقم"]: r["القرار"] for r in rows(SOL / "exhibits.csv")}
    assert sol == KEY["1.8"] and len(ex) == 8
    rules = text(FILES / "evidence" / "intake_rules.txt")
    assert all(d in rules for d in set(sol.values()))
    # the rules decide: a hash mismatch or a generated-content credential goes to the expert
    for r in ex:
        if "غير متطابقة" in r["البصمة الرقمية"] or "توليد" in r["ما لاحظه الكاتب"]:
            assert sol[r["الرقم"]] == "إحالة إلى خبير رقمي", r["الرقم"]
        if "نص أبيض" in r["ما لاحظه الكاتب"]:
            assert sol[r["الرقم"]].startswith("إحالة إلى القاضي"), r["الرقم"]
    counts = {}
    for v in sol.values():
        counts[v] = counts.get(v, 0) + 1
    say("1.8", "; ".join(f"{k}: {v}" for k, v in counts.items()))


# ------------------------------------------------------------------ 2.1 to 2.3 triage

def filings() -> list[dict]:
    return rows(FILES / "triage" / "filings_500.csv")


def conf(fs: list[dict], t: int) -> dict:
    c = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for r in fs:
        hi = int(r["درجة «أسبقية»"]) >= t
        u = r["الوسم المرجعي"] == "عاجل"
        c["tp" if hi and u else "fp" if hi else "fn" if u else "tn"] += 1
    c["flagged"] = c["tp"] + c["fp"]
    return c


def lab_2_1() -> None:
    fs = filings()
    assert len(fs) == 500
    c = conf(fs, 60)
    assert c == KEY["triage"]["60"]
    start = rows(FILES / "start" / "table_t60.csv")[0]
    assert [int(start[k]) for k in list(start)[1:]] == [c["tp"], c["fp"], c["fn"], c["tn"], c["flagged"]]
    u = c["tp"] + c["fn"]
    say("2.1", f"urgent {u} of 500; at 60: caught {c['tp']}, missed {c['fn']} ({pct(c['fn'], u)}), "
               f"needless {c['fp']}, flagged {c['flagged']} against a capacity of {KEY['triage']['capacity']}")


def lab_2_2() -> None:
    fs = filings()
    lines = []
    for t in (60, 45, 50, 55):
        c = conf(fs, t)
        if str(t) in KEY["triage"]:
            assert c == KEY["triage"][str(t)]
        lines.append(f"at {t}: missed {c['fn']}, needless {c['fp']}, flagged {c['flagged']}"
                     + (" (over capacity)" if c["flagged"] > KEY["triage"]["capacity"] else ""))
    sol = rows(SOL / "confusion_table.csv")
    assert int(sol[1]["عاجل ودون العتبة"]) == conf(fs, 45)["fn"]
    say("2.2", *lines)


def lab_2_3() -> None:
    fs = filings()
    lines = []
    for t in (60, 45, 55):
        for filer in ("محامٍ", "صاحب الدعوى بنفسه"):
            c = conf([r for r in fs if r["مقدّم الدعوى"] == filer], t)
            if f"{t}|{filer}" in KEY["triage"]:
                assert c == KEY["triage"][f"{t}|{filer}"]
            u = c["tp"] + c["fn"]
            lines.append(f"at {t}, {filer}: urgent {u}, missed {c['fn']} ({pct(c['fn'], u)})")
    sol = rows(SOL / "subgroup_table.csv")
    assert len(sol) == 4
    say("2.3", *lines)


# ------------------------------------------------------------------ 2.4 to 2.6 due process

def lab_2_4() -> None:
    policy = text(FILES / "dueprocess" / "ministry_policy.txt")
    assert len(re.findall(r"^المتطلب \d:", policy, re.M)) == 6
    notice = text(FILES / "dueprocess" / "decision_notice_sample.txt")
    process = text(FILES / "dueprocess" / "current_process.txt")
    assert "بحسب ترجيح" in notice and "لا يذكر النموذج «ترجيح»" in process
    sol = {r["المتطلب"]: r["الحكم"] for r in rows(SOL / "checklist.csv")}
    assert sol == KEY["dueprocess"]
    part1 = {k: sol[k] for k in ("R1", "R2", "R3")}
    say("2.4", "rows R1-R3: " + ", ".join(f"{k} {v}" for k, v in part1.items()))


def lab_2_5() -> None:
    sol = rows(SOL / "checklist.csv")
    start = rows(FILES / "start" / "checklist_part1.csv")
    assert start[:3] == sol[:3] and all(r["الحكم"] == "" for r in start[3:])
    gaps = [r["المتطلب"] for r in sol if r["الحكم"] == "ثغرة"]
    traced = rows(SOL / "case_files_traced.csv")
    cases = rows(FILES / "dueprocess" / "case_files.csv")
    assert [t["الملف"] for t in traced] == [c["الملف"] for c in cases] and len(cases) == 6
    assert "مكررتان" in next(c["الوقائع"] for c in cases if c["الملف"] == "K3")
    say("2.5", f"gaps {len(gaps)} of 6: {' '.join(gaps)}; every gap has a control and an owner",
        "K3: a duplicated record raised the score and cannot be corrected; K6: inputs withheld as a trade secret")
    assert all(r["الضابط المقترح"] and r["المسؤول"] for r in sol)


def lab_2_6() -> None:
    sol = rows(SOL / "classification_sheet.csv")
    assert {r["الرقم"]: r["مستوى المخاطر عند سدايا"] for r in sol} == KEY["classify"]
    assert rows(FILES / "start" / "checklist_complete.csv") == rows(SOL / "checklist.csv")
    high = [r["الرقم"] for r in sol if r["مستوى المخاطر عند سدايا"] == "عالية"]
    say("2.6", f"five deployments classified; high under the SDAIA levels: {' '.join(high)}")


# ------------------------------------------------------------------ 2.7 and 2.8 map

def quadrant(code: str, s: list[int]) -> tuple[int, int, str]:
    value, err, rev, ready, contest = s
    opp, risk = value + ready, err + (4 - rev) + (4 - contest)
    if code == "U07":
        return opp, risk, "متوقف عند البوابة"
    if opp >= 5:
        return opp, risk, "تجربة الآن" if risk <= 5 else "تجربة بضوابط"
    return opp, risk, "لاحقًا" if risk <= 5 else "لا الآن"


def lab_2_7() -> None:
    guide = text(FILES / "map" / "map_guide.txt")
    assert "الفرصة = القيمة + جاهزية البيانات" in guide
    sol = rows(SOL / "map_sheet.csv")
    out = {}
    for r in sol:
        s = [int(r[f]) for f in ("القيمة", "تكلفة الخطأ", "قابلية التراجع", "جاهزية البيانات", "قابلية الطعن")]
        opp, risk, quad = quadrant(r["الرقم"], s)
        assert (opp, risk, quad) == (int(r["الفرصة"]), int(r["الخطر"]), r["الربع"]) == (
            KEY["map"][r["الرقم"]]["opportunity"], KEY["map"][r["الرقم"]]["risk"], KEY["map"][r["الرقم"]]["quadrant"])
        out.setdefault(quad, []).append(r["الرقم"])
    say("2.7", *[f"{k}: {' '.join(v)}" for k, v in out.items()])


def lab_2_8() -> None:
    assert rows(FILES / "start" / "map_scored.csv") == rows(SOL / "map_sheet.csv")
    r3 = KEY["pilot"]["rule_of_three"]
    for n, v in r3.items():
        assert abs(3 / int(n) - v) < 0.001
    say("2.8", "start file map_scored.csv matches the solution",
        "rule of three: zero errors in 60 reviewed items bounds the rate below about 5%; 100 below 3%; 300 below 1%")


LABS_RUN = {"1.1": lab_1_1, "1.2": lab_1_2, "1.3": lab_1_3, "1.4": lab_1_4, "1.5": lab_1_5, "1.6": lab_1_6,
            "1.7": lab_1_7, "1.8": lab_1_8, "2.1": lab_2_1, "2.2": lab_2_2, "2.3": lab_2_3, "2.4": lab_2_4,
            "2.5": lab_2_5, "2.6": lab_2_6, "2.7": lab_2_7, "2.8": lab_2_8}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(LABS_RUN)
    for lab in wanted:
        LABS_RUN[lab]()
    print(f"all {len(wanted)} labs PASS")
