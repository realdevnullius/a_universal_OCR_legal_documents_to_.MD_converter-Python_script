"""
deduplicate.py
================================================================================

ENGLISH
-------
Compares the markdown produced WITH the word list against the markdown produced
WITHOUT it, and answers the only question that matters: did the word list
change anything at all?

  identical    -> the WITH-DICT copy is deleted; the word list gained nothing
  different    -> BOTH are kept, and the differing words are reported

The no-dictionary version is the BASELINE and the one kept on a tie, because it
is the plain Tesseract result: fewer moving parts, and reproducible without this
toolset. The WITH-DICT run is the experiment, not the reference.

WHERE IT LOOKS
Two layouts are supported, and both may be present at once:
  1. Two folders side by side:  ./_WITH-DICT.out  and  ./_NO-DICT.out
  2. One folder holding both:   <source>.dic.md   and  <source>.md
Matching ignores the ".dic" marker, so "brief.pdf.dic.md" pairs with
"brief.pdf.md".

WHAT THIS DOES NOT TELL YOU
A difference is not an improvement. The word list can just as easily have
"corrected" a correctly read word into a wrong one. That is why differing pairs
are kept rather than resolved automatically: you have to read the reported words
and judge the direction yourself. A handful of spot checks against the original
PDF is worth more than any count.

USAGE
Run the dry run first -- it deletes nothing and shows exactly what would happen:

    python deduplicate.py --dry-run
    python deduplicate.py

NEDERLANDS
----------
Vergelijkt de markdown die MET woordenlijst is gemaakt met die ZONDER, en
beantwoordt de enige vraag die telt: veranderde de woordenlijst uberhaupt iets?

  identiek     -> de MET-versie wordt verwijderd; de woordenlijst leverde niets
  verschillend -> BEIDE blijven staan, en de afwijkende woorden worden getoond

De versie zonder woordenlijst is de BASISRUN en blijft bij gelijkspel staan: dat
is het kale Tesseract-resultaat, met minder bewegende delen en reproduceerbaar
zonder deze toolset. De MET-run is het experiment, niet de referentie.

WAAR HET ZOEKT
Twee indelingen worden ondersteund, en ze mogen naast elkaar bestaan:
  1. Twee mappen naast elkaar:  ./_WITH-DICT.out  en  ./_NO-DICT.out
  2. Een map met beide erin:    <bron>.dic.md     en  <bron>.md
Bij het koppelen wordt ".dic" genegeerd, dus "brief.pdf.dic.md" hoort bij
"brief.pdf.md".

WAT DIT NIET ZEGT
Een verschil is geen verbetering. De woordenlijst kan een correct gelezen woord
net zo goed hebben "gecorrigeerd" naar een fout woord. Daarom worden afwijkende
paren bewaard in plaats van automatisch opgelost: u moet de getoonde woorden
zelf beoordelen. Een handvol steekproeven tegen de originele PDF zegt meer dan
welk aantal ook.

GEBRUIK
Draai eerst de proefronde -- die verwijdert niets en toont wat er zou gebeuren:

    python deduplicate.py --dry-run
    python deduplicate.py
================================================================================
"""

import os
import sys
import glob
import re

WITH_DIR = "_WITH-DICT.out"
NO_DIR = "_NO-DICT.out"

# How many differing words to print per file before truncating.
MAX_WORDS_SHOWN = 12


def base_name(filename):
    """
    Strip .md and an optional .dic marker so both variants share one key.

    @inv  base_name("x.pdf.dic.md") == base_name("x.pdf.md") == "x.pdf"
    @seq  .md must be stripped before .dic; the reverse order never matches
    @trap do not use os.path.splitext twice here -- a source name containing
          dots ("v1.2.report.pdf.md") would lose a real component
    """
    name = filename
    if name.lower().endswith(".md"):
        name = name[:-3]
    if name.lower().endswith(".dic"):
        name = name[:-4]
    return name


def collect(root):
    """
    Return {base: {"with": path, "no": path}} for every markdown found.

    A file counts as the WITH-DICT variant when it sits in _WITH-DICT.out or
    carries the .dic.md suffix; as the NO-DICT variant when it sits in
    _NO-DICT.out or is a plain .md in the root folder.

    @edge both layouts may coexist; last writer per (key, kind) wins, and the
          folder scan runs first so folder placement outranks the .dic marker
    @edge README.md and CUSTOMDIC.md are repository docs, not output; skipped
    @ret  {base: {"with": path, "no": path}} -- either key may be absent, and
          the caller reports those as unpaired rather than comparing None
    """
    pairs = {}

    def add(path, kind):
        key = base_name(os.path.basename(path))
        pairs.setdefault(key, {})[kind] = path

    for folder, kind in ((os.path.join(root, WITH_DIR), "with"),
                         (os.path.join(root, NO_DIR), "no")):
        if os.path.isdir(folder):
            for path in glob.glob(os.path.join(folder, "*.md")):
                if os.path.basename(path).lower() in ("readme.md", "customdic.md"):
                    continue
                add(path, kind)

    # Loose files in the script folder, kept for output from older versions
    # that wrote .dic.md and .md side by side instead of into two folders.
    for path in glob.glob(os.path.join(root, "*.md")):
        name = os.path.basename(path)
        if name.lower() in ("readme.md", "customdic.md"):
            continue
        add(path, "with" if name.lower().endswith(".dic.md") else "no")

    return pairs


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return None


def word_changes(no_text, with_text):
    """
    Return a list of (without, with) word pairs that differ.

    Deliberately simple: both texts are split into words and walked in parallel.
    Once the streams fall out of step the comparison degrades, which is why the
    output is capped and framed as a hint, not as a full diff.

    @trap zip() over two token streams is NOT an alignment algorithm. One
          inserted or deleted token shifts everything after it and every
          subsequent pair reads as a difference. Accepted on purpose: a real
          diff (difflib.SequenceMatcher) costs more than the signal is worth
          here, and the cap keeps the noise bounded.
    @post len(result) <= MAX_WORDS_SHOWN
    @edge equal token streams with different whitespace -> empty list, which
          the caller renders as "differs in whitespace or layout only"
    """
    a = re.findall(r"\S+", no_text)
    b = re.findall(r"\S+", with_text)
    out = []
    for left, right in zip(a, b):
        if left != right:
            out.append((left, right))
            if len(out) >= MAX_WORDS_SHOWN:
                break
    return out


def main():
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    root = os.path.abspath(".")
    pairs = collect(root)

    if not pairs:
        print("No markdown files found.")
        print(f"Expected {WITH_DIR}\\ and {NO_DIR}\\ next to this script,")
        print("or .dic.md and .md files together in this folder.")
        return

    identical, different, only_with, only_no, unreadable = [], [], [], [], []

    for key in sorted(pairs):
        entry = pairs[key]
        p_with, p_no = entry.get("with"), entry.get("no")

        # @edge unpaired entries are counted and reported but never deleted:
        #       without a counterpart there is nothing to prove redundancy
        if p_with and not p_no:
            only_with.append(key)
            continue
        if p_no and not p_with:
            only_no.append(key)
            continue

        t_with, t_no = read(p_with), read(p_no)
        if t_with is None or t_no is None:
            unreadable.append(key)
            continue

        if t_with == t_no:
            identical.append((key, p_with))
        else:
            different.append((key, p_no, t_no, t_with))

    # ---- act on the identical pairs -----------------------------------------
    # @io   deletes files. Guarded by dry_run.
    # @inv  path is always entry["with"]; entry["no"] is never a delete target
    # @edge a failed unlink is collected, not raised: one locked file must not
    #       abort the pass over the rest
    removed, failed = 0, []
    for key, path in identical:
        if dry_run:
            continue
        try:
            os.remove(path)
            removed += 1
        except Exception as err:
            failed.append((key, err))

    # ---- report --------------------------------------------------------------
    print("=" * 70)
    print("DRY RUN - nothing was deleted" if dry_run else "Deduplication complete")
    print("=" * 70)
    print(f"  Pairs compared          : {len(identical) + len(different)}")
    print(f"  Identical               : {len(identical)}"
          + ("  (would be removed)" if dry_run else f"  (removed: {removed})"))
    print(f"  Different, both kept    : {len(different)}")
    if only_with:
        print(f"  Only a WITH-DICT copy   : {len(only_with)}")
    if only_no:
        print(f"  Only a NO-DICT copy     : {len(only_no)}")
    if unreadable:
        print(f"  Could not be read       : {len(unreadable)}")

    total = len(identical) + len(different)
    if total:
        pct = 100.0 * len(different) / total
        print(f"\n  The word list changed something in {len(different)} of {total} "
              f"documents ({pct:.1f}%).")
        if not different:
            print("  On this sample it made no measurable difference at all.")

    if different:
        print("\n" + "-" * 70)
        print("DIFFERENCES  (left = without word list, right = with)")
        print("-" * 70)
        for key, _p_no, t_no, t_with in different:
            print(f"\n{key}")
            changes = word_changes(t_no, t_with)
            if not changes:
                print("    (differs in whitespace or layout only)")
            for left, right in changes:
                print(f"    {left!r:>28}  ->  {right!r}")
            if len(changes) >= MAX_WORDS_SHOWN:
                print(f"    ... truncated at {MAX_WORDS_SHOWN} words")
        print("\n" + "-" * 70)
        print("A change is not automatically an improvement. Check a few of these")
        print("against the original PDF before drawing any conclusion.")

    if failed:
        print("\nCould not delete:")
        for key, err in failed:
            print(f"  - {key}: {err}")

    if only_with:
        print("\nOnly a WITH-DICT copy exists for these (no counterpart to compare):")
        for key in only_with[:20]:
            print(f"  - {key}")
        if len(only_with) > 20:
            print(f"  ... and {len(only_with) - 20} more")

    if dry_run:
        print("\nRun again without --dry-run to actually delete the identical copies.")


if __name__ == "__main__":
    main()
