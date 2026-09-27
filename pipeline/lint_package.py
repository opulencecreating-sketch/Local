#!/usr/bin/env python3
"""Lint a Mode B content package against the pipeline's structural and editorial rules.

Usage:
    python3 pipeline/lint_package.py DRAFT.md [--tier 1|2|3] [--transcript FILE]

Exits 1 if any ERROR is found; WARNings do not fail the run.
"""

import argparse
import re
import sys

BANNED = [
    "game-changer", "game changer", "mind-blowing", "mind blowing", "insane",
    "revolutionize", "revolutionise", "in today's digital landscape",
    "supercharge", "next-level", "paradigm shift", "the future is here",
]

# Allowed clip duration per tier, in seconds.
TIER_WINDOWS = {1: (3 * 60, 8 * 60), 2: (15 * 60, 30 * 60), 3: (45 * 60, 90 * 60)}

TS = r"\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?"


def to_seconds(ts):
    secs = 0
    for part in ts.split(":"):
        secs = secs * 60 + int(part)
    return secs


def section(text, pattern):
    """Return the body of the first heading matching pattern, up to the next heading of equal or higher level."""
    m = re.search(rf"^(#{{2,3}})\s*{pattern}.*$", text, re.M | re.I)
    if not m:
        return None
    level = len(m.group(1))
    rest = text[m.end():]
    nxt = re.search(rf"^#{{1,{level}}}\s", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def field(text, name):
    m = re.search(rf"\*\*{name}:?\*\*:?\s*(.+)", text, re.I)
    return m.group(1).strip() if m else None


def lint(text, tier, transcript):
    errors, warnings = [], []

    front = re.search(r"^tier:\s*(\d)", text, re.M)
    if tier is None and front:
        tier = int(front.group(1))
    if tier not in TIER_WINDOWS:
        errors.append("tier unknown: pass --tier or set `tier:` in front matter")

    lowered = text.lower()
    for phrase in BANNED:
        if re.search(rf"\b{re.escape(phrase)}\b", lowered):
            errors.append(f"banned phrase: '{phrase}'")

    for heading in ["1\\.", "2\\.", "3\\.", "4\\."]:
        if section(text, heading) is None:
            errors.append(f"missing part {heading.rstrip('.').replace(chr(92), '')} heading")

    # Part 1: cut range
    cut = field(text, "Exact Cut Range")
    if not cut:
        errors.append("missing Exact Cut Range")
    else:
        stamps = re.findall(TS, cut)
        if len(stamps) < 2:
            errors.append(f"cut range needs start and end timestamps: '{cut}'")
        elif tier in TIER_WINDOWS:
            dur = to_seconds(stamps[1]) - to_seconds(stamps[0])
            lo, hi = TIER_WINDOWS[tier]
            if dur <= 0:
                errors.append("cut range end is not after start")
            elif not lo <= dur <= hi:
                errors.append(f"cut duration {dur // 60}m{dur % 60:02d}s outside Tier {tier} window "
                              f"({lo // 60}-{hi // 60} min)")

    headline = field(text, "On-Screen Headline")
    if not headline:
        errors.append("missing On-Screen Headline")
    else:
        n = len(re.sub(r"[\"“”]", "", headline).split())
        if not 4 <= n <= 8:
            errors.append(f"headline is {n} words; needs 4-8")

    retention = field(text, "Retention Mechanics")
    if not retention:
        errors.append("missing Retention Mechanics")
    elif len(re.findall(r"[.!?](?:\s|$)", retention)) != 2:
        warnings.append("Retention Mechanics should be exactly 2 sentences")

    # Part 2: hook
    hook = section(text, r"2\.")
    if hook is not None:
        lines = [l.strip() for l in hook.splitlines() if l.strip()]
        source = [l for l in lines if l.lower().startswith("source:")]
        body = [l for l in lines if not l.lower().startswith("source:")]
        if not 2 <= len(body) <= 4:
            errors.append(f"hook has {len(body)} lines; needs 2-4 (excluding Source line)")
        if not source:
            errors.append("hook missing 'Source: @Host via @Channel | Guest: @Guest' line")
        elif "@" not in source[0]:
            errors.append("Source line has no @handles")

    # Part 3: article
    thesis = section(text, "Core Thesis")
    if thesis is None:
        errors.append("missing Core Thesis")
    else:
        n = len(re.findall(r"[.!?](?:\s|$)", thesis.strip()))
        if not 2 <= n <= 3:
            warnings.append(f"Core Thesis has ~{n} sentences; target 2-3")

    arch = section(text, r"System Architecture")
    if arch is None:
        errors.append("missing System Architecture / Mechanical Deconstruction")
    else:
        items = re.findall(r"^\s*(?:\d+\.|[-*])\s+\*\*", arch, re.M)
        if not 3 <= len(items) <= 5:
            errors.append(f"deconstruction has {len(items)} bold-led items; needs 3-5")

    nav = section(text, "Navigational Index")
    nav_stamps = re.findall(rf"^\s*[-*\d.]*\s*{TS}", nav or "", re.M)
    if tier in (2, 3):
        if nav is None:
            errors.append(f"Navigational Index is mandatory for Tier {tier}")
        elif not 4 <= len(nav_stamps) <= 8:
            errors.append(f"Navigational Index has {len(nav_stamps)} timestamps; needs 4-8")

    if section(text, "Tactical Playbook") is None:
        errors.append("missing Tactical Playbook")
    if section(text, "Key Mental Model") is None:
        errors.append("missing Key Mental Model / Takeaway")
    if "<!-- value-add -->" not in text:
        errors.append("missing <!-- value-add --> marker for standalone analysis")

    # Part 4: engagement
    question = field(text, "Terminal Discussion Hook")
    if not question:
        errors.append("missing Terminal Discussion Hook")
    elif not question.rstrip().endswith("?"):
        errors.append("Terminal Discussion Hook should be a question")

    tags = field(text, "Search Keywords & Discovery Tags")
    if not tags:
        errors.append("missing Search Keywords & Discovery Tags")
    else:
        n = len([t for t in re.split(r"[,;]", tags) if t.strip()])
        if not 3 <= n <= 5:
            errors.append(f"{n} keywords; needs 3-5")

    # Leftover template placeholders
    if re.search(r"\[mm:ss\]|<4-8 words>|<Term>|<sentence 1>", text):
        errors.append("unfilled template placeholders remain")

    # Timestamps must exist in the transcript
    if transcript is not None:
        known = {to_seconds(t) for t in re.findall(TS, transcript)}
        claimed = set(nav_stamps) | set(re.findall(TS, cut or "")[:2])
        for ts in sorted(claimed, key=to_seconds):
            if to_seconds(ts) not in known:
                warnings.append(f"timestamp {ts} not found verbatim in transcript")

    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("draft")
    ap.add_argument("--tier", type=int, choices=[1, 2, 3])
    ap.add_argument("--transcript")
    args = ap.parse_args()

    with open(args.draft, encoding="utf-8") as f:
        text = f.read()
    transcript = None
    if args.transcript:
        with open(args.transcript, encoding="utf-8") as f:
            transcript = f.read()

    errors, warnings = lint(text, args.tier, transcript)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
