"""
check_markdown.py
================================================================================

ENGLISH
-------
Scans the markdown already produced and flags files that may be missing pages.

This exists because of a failure mode the converter used to have: Docling can
drop individual pages (typically std::bad_alloc when RAM runs out) without
raising an exception. The old converter then wrote a .md containing only the
surviving pages and reported success. A partial document is indistinguishable
from a complete one when you read it later, which is the worst kind of error in
a case file.

The current jpg.pdf.convert.py refuses to write markdown in that situation, so
this tool is for output produced by earlier versions, or for a second opinion.

It MOVES NOTHING and DELETES NOTHING. It prints a list of suspects and leaves
every decision to you.

WHAT IT CAN AND CANNOT DO
This is a HEURISTIC, not proof. It cannot re-OCR anything. It compares the page
count of the source PDF against the amount of text in the .md and reports a low
ratio as suspicious. A short but complete letter can be flagged wrongly; a long
document missing one blank page can slip through.

When in doubt: delete the .md and convert that document again.

USAGE
    python check_markdown.py

NEDERLANDS
----------
Loopt de reeds geproduceerde markdown na en markeert bestanden waarin mogelijk
pagina's ontbreken.

Dit bestaat vanwege een faalwijze die de converter vroeger had: Docling kan
losse pagina's laten vallen (meestal std::bad_alloc bij geheugengebrek) zonder
een exception te gooien. De oude converter schreef dan een .md met alleen de
overgebleven pagina's en meldde succes. Een half document is bij later lezen
niet te onderscheiden van een heel document, en dat is in een dossier de
gevaarlijkste soort fout.

De huidige jpg.pdf.convert.py weigert in die situatie markdown te schrijven,
dus dit gereedschap is bedoeld voor uitvoer van oudere versies, of als
second opinion.

Het VERPLAATST NIETS en VERWIJDERT NIETS. Het toont een lijst met verdachte
bestanden en laat elke beslissing aan u.

WAT DIT WEL EN NIET KAN
Dit is een HEURISTIEK, geen bewijs. Het kan niets opnieuw OCR'en. Het
vergelijkt het aantal pagina's in de bron-PDF met de hoeveelheid tekst in de
.md en meldt een lage verhouding als verdacht. Een korte maar volledige brief
kan onterecht opvallen; een lang document waarvan een lege pagina ontbreekt kan
worden gemist.

Bij twijfel: gooi de .md weg en converteer dat document opnieuw.

GEBRUIK
    python check_markdown.py
================================================================================

# ===[ AGENT-NOTES ]===========================================================
# Machine-oriented annotation grammar used throughout this repository:
#   @inv   invariant that must hold at that point
#   @pre   precondition assumed by the following block
#   @post  guaranteed state after the block
#   @edge  edge case and how it is handled
#   @trap  known footgun; do not "simplify" without reading
#   @seq   ordering constraint between statements
#   @io    filesystem or process side effect
#   @why   non-obvious rationale, usually earned by a past bug
#
# @role   read-only auditor over converted output; zero mutations
# @inv    no code path in this module writes, moves, or deletes a file
# @inv    exit code is always 0; findings are advisory, never fatal
# @dep    optional: pypdf | PyPDF2. Absent -> byte-scan fallback, lower accuracy
# ============================================================================
"""

import os
import glob

# @state module-level, rebound inside main(). Holds the resolved source folder.
#        Default "." serves the legacy flat layout where documents sat beside
#        the scripts.
SOURCE_DIR = "."

# @tuning Expected characters of text per page. Below this, pages may be
#         missing. Deliberately generous: legal letters with a lot of white
#         space legitimately fall under it, and a false positive costs the
#         reader one look while a false negative hides a truncated document.
MIN_CHARS_PER_PAGE = 250

# @inv these must match the extensions list in jpg.pdf.convert.py, otherwise a
#      source file exists but is never matched to its markdown.
SOURCE_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".webp")

OUTPUT_DIRS = ("_WITH-DICT.out", "_NO-DICT.out", ".")


def pdf_page_count(path):
    """
    Return the page count of a PDF, or None when it cannot be determined.

    @seq  three strategies in descending reliability; first success wins
    @dep  pypdf and PyPDF2 are optional. Neither installed -> byte scan.
    @trap the byte scan counts "/Type /Page" minus "/Type /Pages". It is a
          heuristic on raw bytes: compressed object streams and unusual
          producers can defeat it. It is a floor on confidence, not a fact.
    @edge encrypted or malformed PDF -> every strategy fails -> None, which the
          caller reports as "not checkable" rather than as a finding.
    """
    for module in ("pypdf", "PyPDF2"):
        try:
            reader = __import__(module, fromlist=["PdfReader"]).PdfReader
            return len(reader(path).pages)
        except Exception:
            continue

    try:
        with open(path, "rb") as handle:
            data = handle.read()
        count = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
        return count if count > 0 else None
    except Exception:
        return None


def find_source(md_path):
    """
    Locate the source document a markdown file was produced from.

    Two naming schemes are supported:
      current:  "scan.pdf.md"  -> source is "scan.pdf"   (extension embedded)
      legacy:   "scan.md"      -> try each known extension

    @pre  SOURCE_DIR resolved by main()
    @edge ".dic.md" is stripped by splitext only once, leaving "scan.pdf.dic".
          Handled explicitly below, otherwise every dictionary-run file would
          be reported as having no source.
    @ret  absolute path, or None when nothing matches
    """
    base = os.path.splitext(os.path.basename(md_path))[0]

    # @edge strip the .dic marker left behind by a word-list run
    if base.lower().endswith(".dic"):
        base = base[:-4]

    direct = os.path.join(SOURCE_DIR, base)
    if os.path.splitext(base)[1].lower() in SOURCE_EXTENSIONS and os.path.exists(direct):
        return direct

    for extension in SOURCE_EXTENSIONS:
        candidate = os.path.join(SOURCE_DIR, base + extension)
        if os.path.exists(candidate):
            return candidate

    return None


def main():
    global SOURCE_DIR

    here = os.path.abspath(".")

    # @seq must precede find_source(); that function reads SOURCE_DIR
    # @edge no _SOURCE-DOCS folder -> legacy flat layout, sources sit here
    SOURCE_DIR = os.path.join(here, "_SOURCE-DOCS")
    if not os.path.isdir(SOURCE_DIR):
        SOURCE_DIR = here

    # @why "." is included so output from the older flat layout is not silently
    #      skipped. set() because "." can duplicate an output folder entry when
    #      this is run from inside one.
    markdown_files = []
    for folder in OUTPUT_DIRS:
        markdown_files.extend(glob.glob(os.path.join(here, folder, "*.md")))
    markdown_files = sorted(set(markdown_files))

    # @edge repository documentation is not converted output
    markdown_files = [p for p in markdown_files
                      if os.path.basename(p).lower() not in ("readme.md", "customdic.md")]

    if not markdown_files:
        print("No markdown files found in _WITH-DICT.out, _NO-DICT.out or here.")
        return

    print(f"{len(markdown_files)} markdown file(s) found. Checking...\n")

    suspect = []
    unverifiable = []
    looks_complete = 0

    for md_path in markdown_files:
        label = os.path.basename(md_path)

        try:
            with open(md_path, encoding="utf-8") as handle:
                text = handle.read()
        except Exception as err:
            print(f"  [?] {label}: could not read markdown ({err})")
            continue

        char_count = len(text.strip())
        source = find_source(md_path)

        # @edge source deleted or renamed -> nothing to compare against
        if source is None:
            unverifiable.append(label)
            continue

        # @edge a standalone image is always exactly one page
        if not source.lower().endswith(".pdf"):
            if char_count < MIN_CHARS_PER_PAGE:
                suspect.append((label, "little text for a single image"))
            else:
                looks_complete += 1
            continue

        pages = pdf_page_count(source)
        if pages is None:
            unverifiable.append(f"{label} (page count failed)")
            continue

        if char_count < pages * MIN_CHARS_PER_PAGE:
            ratio = char_count / pages if pages else 0
            suspect.append((label, f"{ratio:.0f} chars/page across {pages} page(s)"))
        else:
            looks_complete += 1

    print("=" * 60)
    print(f"  Looks complete   : {looks_complete}")
    print(f"  Suspect          : {len(suspect)}")
    print(f"  Not checkable    : {len(unverifiable)}")

    if suspect:
        print("\nSUSPECT -- pages may be missing:")
        for label, reason in suspect:
            print(f"  - {label}")
            print(f"      {reason}")
        print("\nWhat to do: delete these .md files and convert them again.")
        print("The current jpg.pdf.convert.py refuses to write partial output.")

    if unverifiable:
        print("\nNOT CHECKABLE (source missing or unreadable):")
        for label in unverifiable[:20]:
            print(f"  - {label}")
        if len(unverifiable) > 20:
            print(f"  ... and {len(unverifiable) - 20} more")

    print("\nNote: this is an estimate, not proof. When in doubt, convert again.")


if __name__ == "__main__":
    main()
