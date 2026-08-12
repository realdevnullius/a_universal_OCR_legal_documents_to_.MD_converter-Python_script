"""
================================================================================
LEGAL & JUDICIAL DOCUMENT TO MARKDOWN BATCH CONVERTER (DOCLING + TESSERACT OCR)
================================================================================

--------------------------------------------------------------------------------
ENGLISH
--------------------------------------------------------------------------------

TWO CHANGES COMPARED TO THE ORIGINAL SCRIPT:

  A) CUSTOM WORD LIST via the OCR_WORDS environment variable
     ocr-with-dict.cmd     -> runs WITH dutch_legal_lean.words
     ocr-without-dict.cmd  -> runs WITHOUT (baseline)
     Each .cmd moves its .md output into its own folder (_WITH-DICT.out /
     _NO-DICT.out) so you can diff the two runs. README.md is never moved.

  B) PARTIAL_SUCCESS DETECTION  <-- IMPORTANT
     Docling can drop individual pages (e.g. "std::bad_alloc" when RAM runs
     out) without raising an exception. The original script then wrote a .md
     with MISSING PAGES and still reported [SUCCESS]. That is worse than a
     blank page: you cannot see it in the output, and on a second run the
     file is skipped because the .md already exists.

     This version checks result.status. If it is not SUCCESS, then:
       - NO .md is written
       - the source file is moved to ./_FAILED
       - you are told what went wrong

     Re-run _FAILED afterwards (ideally with more free RAM, or with
     LIMIT_MEMORY_USAGE = True).

WHAT THIS SCRIPT DOES:
  Batch-converts legal files, judicial correspondence, court decisions and
  photographed case evidence into structured, LLM-ready Markdown (.md).
  Optimized for offline processing on Windows x64 with Microsoft Store
  Python and native Tesseract OCR.

OTHER FILE TYPES:
  Docling also reads .docx, .pptx, .html, .xhtml and .rtf. Append the
  extension to the 'extensions' list below to activate it.

OCR LANGUAGE:
  Targets Dutch ('nld'). Add further Tesseract language codes to lang=[...].
  Note: this is the OCR language, NOT the language of this script's messages.
  For that, see the LANGUAGE setting in the configuration section.

THE '_FAILED' RECOVERY WORKFLOW:
  1. Let the primary run finish.
  2. Copy jpg.pdf.convert.py AND ocr_words_patch.py into ./_FAILED.
     (Both! Otherwise the recovery run proceeds without the word list.)
  3. Run the .cmd there, or: python .\\jpg.pdf.convert.py
  4. Files that fully succeed move themselves back up to root.
  5. Still failing? Set LIMIT_MEMORY_USAGE = True (parses at ~150 DPI).

--------------------------------------------------------------------------------
NEDERLANDS
--------------------------------------------------------------------------------

TWEE AANPASSINGEN T.O.V. HET ORIGINELE SCRIPT:

  A) WOORDENLIJST via de omgevingsvariabele OCR_WORDS
     ocr-with-dict.cmd     -> draait MET dutch_legal_lean.words
     ocr-without-dict.cmd  -> draait ZONDER (basisrun)
     Elke .cmd verplaatst zijn .md-uitvoer naar een eigen map
     (_WITH-DICT.out / _NO-DICT.out) zodat u beide runs kunt vergelijken.
     README.md wordt nooit verplaatst.

  B) PARTIAL_SUCCESS-DETECTIE  <-- BELANGRIJK
     Docling kan losse pagina's laten vallen (bv. "std::bad_alloc" bij te
     weinig RAM) zonder een exception te gooien. Het origineel schreef dan
     gewoon een .md weg met ONTBREKENDE PAGINA'S en meldde [SUCCESS]. Dat is
     erger dan een blanco pagina: u ziet het niet terug in de uitvoer, en bij
     een tweede ronde wordt het bestand overgeslagen omdat de .md al bestaat.

     Deze versie controleert result.status. Is die niet SUCCESS, dan:
       - wordt er GEEN .md geschreven
       - gaat het bronbestand naar ./_FAILED
       - ziet u wat er misging

     Draai _FAILED daarna opnieuw (bij voorkeur met meer RAM vrij, of met
     LIMIT_MEMORY_USAGE = True).

WAT DIT SCRIPT DOET:
  Zet juridische stukken, correspondentie, uitspraken en gefotografeerde
  dossierstukken in bulk om naar gestructureerde, LLM-klare Markdown (.md).
  Geoptimaliseerd voor offline verwerking op Windows x64 met Microsoft Store
  Python en native Tesseract OCR.

ANDERE BESTANDSTYPEN:
  Docling leest ook .docx, .pptx, .html, .xhtml en .rtf. Voeg de extensie toe
  aan de 'extensions'-lijst hieronder om die te activeren.

OCR-TAAL:
  Ingesteld op Nederlands ('nld'). Voeg verdere Tesseract-taalcodes toe aan
  lang=[...]. Let op: dit is de OCR-taal, NIET de taal van de meldingen van
  dit script. Zie daarvoor de instelling LANGUAGE hieronder.

DE '_FAILED'-HERSTELRONDE:
  1. Laat de eerste ronde aflopen.
  2. Kopieer jpg.pdf.convert.py EN ocr_words_patch.py naar ./_FAILED.
     (Allebei! Anders draait de herstelronde zonder woordenlijst.)
  3. Draai de .cmd daar, of: python .\\jpg.pdf.convert.py
  4. Bestanden die volledig slagen verplaatsen zichzelf terug naar de hoofdmap.
  5. Blijft het misgaan? Zet LIMIT_MEMORY_USAGE = True (verwerkt op ~150 DPI).

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
# @role   batch driver. Owns folder resolution, the quality gate, and all
#         filesystem mutation of source documents.
# @seq    ocr_words_patch.enable() MUST run before the docling imports below.
# @inv    DICT_ACTIVE decides both the output folder and the .md suffix; the
#         two must never disagree or a comparison run silently mixes modes.
# @inv    a document is written to markdown only on ConversionStatus.SUCCESS
# @trap   docling returns PARTIAL_SUCCESS WITHOUT raising when pages are
#         dropped (std::bad_alloc). Writing markdown on that status produces a
#         file indistinguishable from a complete one. Do not relax this.
# @trap   a C-level allocation failure kills the process with exit code 0 and
#         no traceback. _run_complete.flag is the only reliable liveness proof
#         for the .cmd wrapper; every orderly exit path must write it.
# @edge   process is not deterministic across runs: identical input has
#         produced differing layout classification, including a text block
#         becoming "<!-- image -->". Callers must not assume reproducibility.
# ============================================================================
"""

import os
import glob
import sys
import shutil
import signal
import time

# Wall-clock start of the whole run, captured before the heavy docling imports
# so the reported time includes model loading -- that is part of what a user
# waits for, and it is where a slow first run mostly goes.
RUN_STARTED = time.time()

# --- CUSTOM WORD LIST PATCH --------------------------------------------------
# Must come BEFORE the docling imports: the patch replaces a subprocess
# function, and it must already be replaced by the time Docling calls it.
# @seq  this block precedes the docling imports on purpose -- see @seq above
# @edge patch module absent -> DICT_ACTIVE False, run proceeds without a list
#       rather than failing; the .cmd wrapper checks for the file separately
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ocr_words_patch
    # enable() returns True when a word list is actually loaded. That flag
    # decides the output naming below: <source>.dic.md versus <source>.md,
    # so both versions can sit in one folder and stay distinguishable.
    DICT_ACTIVE = bool(ocr_words_patch.enable())
except ImportError:
    print("[WORDLIST] ocr_words_patch.py not found -- running without a word list.")
    ocr_words_patch = None
    DICT_ACTIVE = False
# -----------------------------------------------------------------------------

from docling.datamodel.base_models import InputFormat, ConversionStatus
from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions

# ==============================================================================
# CONFIGURATION SETTINGS
# ==============================================================================

# Language of this script's own messages. "EN" (default) or "NL".
# This is NOT the OCR language -- that is set in ocr_options below.
# Can also be overridden from the command line: set SCRIPT_LANG=NL
LANGUAGE = "EN"

LIMIT_MEMORY_USAGE = False
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Set to False if you want incomplete documents written out anyway.
# Strongly discouraged: you then get .md files with missing pages without
# any way to tell from the content that something is absent.
QUARANTINE_INCOMPLETE = True

# Warn before a file when usable memory drops below this (megabytes).
#
# "Usable" is the remaining Windows COMMIT charge: physical RAM plus pagefile
# that may still be reserved. That is what an allocation actually draws from.
# Free physical RAM is reported too, but it is not the limit -- with a pagefile
# enabled Windows simply pages out, so a low physical figure is not by itself a
# problem. An earlier version took the lower of the two, which on an 8 GB
# machine capped the reading at ~8000 and made the warning fire on every single
# file no matter what.
#
# Set to 0 to switch the check off.
MIN_FREE_MB = 2000

# Once the warning has fired, stay quiet until usable memory has dropped
# another this many megabytes. Without this the same line repeats for every
# document and stops being read at all.
MEM_WARN_STEP_MB = 500
# ==============================================================================

# Allow the .cmd wrapper (or the user's shell) to override the language.
LANGUAGE = (os.environ.get("SCRIPT_LANG") or LANGUAGE).strip().upper()
if LANGUAGE not in ("EN", "NL"):
    LANGUAGE = "EN"

# ==============================================================================
# MESSAGE STRINGS
# Every user-facing message lives here so the script stays readable.
# Add a language by adding a third key to each entry.
# ==============================================================================
MSG = {
    "init":            {"EN": "Initializing Robust Legal Docling Pipeline...",
                        "NL": "Robuuste juridische Docling-pijplijn wordt gestart..."},
    "lowram":          {"EN": "[INFO] Low-RAM mode enabled. Scaling layout resolution to ~150 DPI.",
                        "NL": "[INFO] Zuinige modus aan. Layoutresolutie geschaald naar ~150 DPI."},
    "maxperf":         {"EN": "[INFO] Maximum quality mode active. Resolution unconstrained.",
                        "NL": "[INFO] Maximale kwaliteit actief. Resolutie niet begrensd."},
    "stray_docs":      {"EN": "[NOTE] {n} document(s) found in the script folder itself.\n"
                              "       Documents now belong in .\\{folder}\\ - move them there\n"
                              "       and run again. Nothing was touched.",
                        "NL": "[LET OP] {n} document(en) in de scriptmap zelf gevonden.\n"
                              "         Documenten horen nu in .\\{folder}\\ - verplaats ze\n"
                              "         daarheen en draai opnieuw. Er is niets aangeraakt."},
    "folders":         {"EN": "[FOLDERS] sources: .\\{src}\\   output: .\\{out}\\   failures: .\\{fail}\\",
                        "NL": "[MAPPEN] bron: .\\{src}\\   uitvoer: .\\{out}\\   mislukt: .\\{fail}\\"},
    "nofiles":         {"EN": "No supported files found in this directory!",
                        "NL": "Geen ondersteunde bestanden in deze map gevonden!"},
    "found":           {"EN": "Found {n} document(s)/photo(s) to process.",
                        "NL": "{n} document(en)/foto('s) gevonden om te verwerken."},
    "ctx_failed":      {"EN": "[CONTEXT] Running inside _FAILED. Recovered documents move back to _SOURCE-DOCS.",
                        "NL": "[CONTEXT] Draait in _FAILED. Herstelde documenten gaan terug naar _SOURCE-DOCS."},
    "skipping":        {"EN": "[{i}/{n}] Skipping (already converted): {f}",
                        "NL": "[{i}/{n}] Overgeslagen (al geconverteerd): {f}"},
    "opening":         {"EN": "[{i}/{n}] Opening: {f}",
                        "NL": "[{i}/{n}] Openen: {f}"},
    "parsing":         {"EN": "   -> Parsing layout and running Tesseract OCR...",
                        "NL": "   -> Layout analyseren en Tesseract-OCR uitvoeren..."},
    "writing":         {"EN": "   -> Writing Markdown data...",
                        "NL": "   -> Markdown wegschrijven..."},
    "saved":           {"EN": "   [SUCCESS] Markdown saved.",
                        "NL": "   [GELUKT] Markdown opgeslagen."},
    "saved_to":        {"EN": "   [SUCCESS] Saved to: {f}\n",
                        "NL": "   [GELUKT] Opgeslagen als: {f}\n"},
    "moving_back":     {"EN": "   -> Moving source file back to the main directory...",
                        "NL": "   -> Bronbestand terugverplaatsen naar de hoofdmap..."},
    "moved_back":      {"EN": "   [SUCCESS] Moved {f} back to the root folder.\n",
                        "NL": "   [GELUKT] {f} teruggezet in de hoofdmap.\n"},
    "incomplete":      {"EN": "   [INCOMPLETE] Status: {s}",
                        "NL": "   [ONVOLLEDIG] Status: {s}"},
    "incomplete_why":  {"EN": "   -> Some pages were not processed. NO .md is written, because a\n"
                              "      partial document is indistinguishable from a complete one later on.",
                        "NL": "   -> Er zijn pagina's niet verwerkt. Er wordt GEEN .md geschreven, want een\n"
                              "      half document is later niet te onderscheiden van een heel document."},
    "isolating_inc":   {"EN": "   -> Isolating incomplete document to: .\\_FAILED\\{f}",
                        "NL": "   -> Onvolledig document geïsoleerd naar: .\\_FAILED\\{f}"},
    "isolated_ok":     {"EN": "   [OK] File moved safely. Re-run _FAILED.\n",
                        "NL": "   [OK] Bestand veilig verplaatst. Draai _FAILED opnieuw.\n"},
    "retry_inc":       {"EN": "   [RETRY INCOMPLETE] Staying in _FAILED.\n"
                              "   -> Try LIMIT_MEMORY_USAGE = True, or free up more RAM.\n",
                        "NL": "   [OPNIEUW ONVOLLEDIG] Blijft in _FAILED staan.\n"
                              "   -> Probeer LIMIT_MEMORY_USAGE = True, of maak meer RAM vrij.\n"},
    "saved_anyway":    {"EN": "   [NOTE] Status {s} -- saved anyway (QUARANTINE_INCOMPLETE=False).",
                        "NL": "   [LET OP] Status {s} -- toch opgeslagen (QUARANTINE_INCOMPLETE=False)."},
    "error":           {"EN": "   [ERROR] Conversion failed. Reason: {e}",
                        "NL": "   [FOUT] Conversie mislukt. Reden: {e}"},
    "removed_partial": {"EN": "   -> Removed the partially written .md.",
                        "NL": "   -> Onvolledige .md verwijderd."},
    "isolating_fail":  {"EN": "   -> Isolating failed document to: .\\_FAILED\\{f}",
                        "NL": "   -> Mislukt document geïsoleerd naar: .\\_FAILED\\{f}"},
    "isolate_err":     {"EN": "   [ERROR] Could not isolate file: {e}\n",
                        "NL": "   [FOUT] Kon bestand niet isoleren: {e}\n"},
    "retry_failed":    {"EN": "   [RETRY FAILED] File stays in the _FAILED directory.\n",
                        "NL": "   [OPNIEUW MISLUKT] Bestand blijft in de _FAILED-map.\n"},
    "interrupt1":      {"EN": "\n[INTERRUPT] Ctrl+C detected. Finishing the current file, then stopping.\n"
                              "Press Ctrl+C again to force an immediate exit.",
                        "NL": "\n[ONDERBREKING] Ctrl+C gedetecteerd. Huidig bestand afmaken, daarna stoppen.\n"
                              "Druk nogmaals op Ctrl+C om direct af te breken."},
    "interrupt2":      {"EN": "\n[CRITICAL] Force quitting immediately...",
                        "NL": "\n[KRITIEK] Wordt onmiddellijk afgebroken..."},
    "paused":          {"EN": "   [INTERRUPT] Conversion paused at your request.\n",
                        "NL": "   [ONDERBROKEN] Conversie gepauzeerd op uw verzoek.\n"},
    "suspended":       {"EN": "Pipeline stopped cleanly by user. Safe to close.",
                        "NL": "Pijplijn netjes gestopt door gebruiker. Veilig af te sluiten."},
    "complete":        {"EN": "Batch complete!",
                        "NL": "Batch afgerond!"},
    "stat_ok":         {"EN": "  Fully processed : {n}",
                        "NL": "  Volledig verwerkt : {n}"},
    "stat_inc":        {"EN": "  Incomplete      : {n}",
                        "NL": "  Onvolledig        : {n}"},
    "stat_fail":       {"EN": "  Failed          : {n}",
                        "NL": "  Mislukt           : {n}"},
    "time_total":      {"EN": "  Total running time: {dur}",
                        "NL": "  Totale looptijd   : {dur}"},
    "time_per_doc":    {"EN": "  Average per document: {dur}  ({n} converted)",
                        "NL": "  Gemiddeld per document: {dur}  ({n} verwerkt)"},
    "time_dict_on":    {"EN": "  Word list was ACTIVE during this run.",
                        "NL": "  De woordenlijst was ACTIEF tijdens deze run."},
    "time_dict_off":   {"EN": "  Word list was NOT used during this run.",
                        "NL": "  De woordenlijst is NIET gebruikt tijdens deze run."},
    "stat_skip":       {"EN": "  Skipped         : {n}",
                        "NL": "  Overgeslagen      : {n}"},
    "inc_header":      {"EN": "\n  Incomplete (now in _FAILED, NO .md written):",
                        "NL": "\n  Onvolledig (staan nu in _FAILED, GEEN .md geschreven):"},
    "inc_advice":      {"EN": "\n  Re-run the _FAILED folder. If it keeps failing, set\n"
                              "  LIMIT_MEMORY_USAGE = True or free up more RAM.",
                        "NL": "\n  Draai de _FAILED-map opnieuw. Blijft het misgaan, zet dan\n"
                              "  LIMIT_MEMORY_USAGE = True of maak meer RAM vrij."},
    "pages_in_doc":    {"EN": "      - document contains {n} page(s) in the conversion",
                        "NL": "      - document telt {n} pagina('s) in de conversie"},
    "mem_at_start":    {"EN": "[MEMORY] {free} MB usable of {total} MB total.\n"
                              "         (usable = the lower of free RAM and remaining commit charge)",
                        "NL": "[GEHEUGEN] {free} MB bruikbaar van {total} MB totaal.\n"
                              "           (bruikbaar = laagste van vrij RAM en resterende commit-ruimte)"},
    "mem_unknown":     {"EN": "[MEMORY] Could not read memory status -- low-memory warnings are off.",
                        "NL": "[GEHEUGEN] Kon geheugenstatus niet uitlezen -- waarschuwingen staan uit."},
    "mem_low":         {"EN": "   [LOW MEMORY] Only {free} MB usable (threshold {min} MB).\n"
                              "   -> Docling reserves far more than the document size suggests;\n"
                              "      failures start well before memory looks full.\n"
                              "   -> Close your browser and other large programs, or set\n"
                              "      LIMIT_MEMORY_USAGE = True.",
                        "NL": "   [WEINIG GEHEUGEN] Nog {free} MB bruikbaar (drempel {min} MB).\n"
                              "   -> Docling reserveert veel meer dan de documentgrootte doet vermoeden;\n"
                              "      het gaat al mis ruim voordat het geheugen vol lijkt.\n"
                              "   -> Sluit uw browser en andere grote programma's, of zet\n"
                              "      LIMIT_MEMORY_USAGE = True."},
    "mem_error":       {"EN": "   [OUT OF MEMORY] Allocation refused with {free} MB reported usable.\n"
                              "   -> This number can look generous and still fail: Windows also\n"
                              "      caps the total commit charge, which browsers consume heavily.\n"
                              "   -> Close other programs and re-run, set LIMIT_MEMORY_USAGE = True,\n"
                              "      or split this PDF into parts.",
                        "NL": "   [GEHEUGEN VOL] Toewijzing geweigerd bij {free} MB bruikbaar.\n"
                              "   -> Dat getal kan ruim lijken en tóch tekortschieten: Windows begrenst\n"
                              "      ook de totale commit-ruimte, en browsers slurpen die op.\n"
                              "   -> Sluit andere programma's en draai opnieuw, zet\n"
                              "      LIMIT_MEMORY_USAGE = True, of splits deze PDF op."},
}


def t(key, **kw):
    """Look up a message in the configured language and fill in placeholders."""
    entry = MSG.get(key, {})
    text = entry.get(LANGUAGE) or entry.get("EN") or key
    return text.format(**kw) if kw else text


def memory_status():
    """
    Return (usable_mb, total_mb, phys_free_mb), or (None, None, None).

    'usable' is the remaining COMMIT charge (ullAvailPageFile): physical RAM
    plus pagefile that may still be reserved. An allocation fails when the
    commit limit is reached, so this is the figure that predicts std::bad_alloc.

    'phys_free' (ullAvailPhys) is reported alongside it for context only. With
    a pagefile enabled a low physical figure is normal and harmless -- Windows
    pages out. An earlier version took min() of the two, which meant physical
    RAM silently capped the reading and the warning could never clear on a
    machine with modest RAM.

    Uses no third-party packages: ctypes on Windows, /proc/meminfo on Linux.
    """
    try:
        if os.name == "nt":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return (None, None)
            mb = 1024 * 1024
            return (stat.ullAvailPageFile // mb,
                    stat.ullTotalPhys // mb,
                    stat.ullAvailPhys // mb)

        # Linux / WSL fallback
        info = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])
        phys_kb = info.get("MemAvailable", info.get("MemFree"))
        free_kb = (phys_kb or 0) + info.get("SwapFree", 0)
        total_kb = info.get("MemTotal")
        if phys_kb is None or total_kb is None:
            return (None, None, None)
        limit = info.get("CommitLimit")
        committed = info.get("Committed_AS")
        if limit is not None and committed is not None:
            free_kb = max(limit - committed, 0)
        return (free_kb // 1024, total_kb // 1024, phys_kb // 1024)
    except Exception:
        return (None, None, None)


_last_mem_warning = None


def maybe_warn_memory():
    """
    Warn once when usable memory drops below MIN_FREE_MB, then stay quiet until
    it has fallen another MEM_WARN_STEP_MB. Repeating the same line for every
    document trains the reader to skip it, which defeats the purpose: the point
    is to be noticed BEFORE a crash takes the whole run down.
    """
    global _last_mem_warning
    if not MIN_FREE_MB:
        return
    usable, _total, _phys = memory_status()
    if usable is None or usable >= MIN_FREE_MB:
        return
    if _last_mem_warning is not None and usable > _last_mem_warning - MEM_WARN_STEP_MB:
        return
    _last_mem_warning = usable
    print(t("mem_low", free=usable, min=MIN_FREE_MB))


def format_duration(seconds):
    """Render a duration as 1h 04m 09s / 4m 09s / 9.4s, whichever fits."""
    seconds = max(seconds, 0)
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(round(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s"


def write_completion_marker():
    """
    Drop the marker the .cmd wrapper looks for before moving any .md files.

    A hard crash (e.g. a C-level allocation failure inside Tesseract or PyTorch)
    can kill this process without raising a Python exception and without setting
    a non-zero exit code. In that case this function is never reached, the marker
    stays absent, and the wrapper leaves the output where it is.

    It must therefore be called on EVERY orderly exit -- including the one where
    the folder simply holds no documents. Skipping it there made an empty folder
    look like a crash, which is a confusing first impression for anyone trying
    the tool out.
    """
    try:
        with open(os.path.join(current_dir, "_run_complete.flag"), "w") as flag:
            flag.write("ok")
    except Exception:
        pass


shutdown_requested = False

stats = {"ok": 0, "incomplete": 0, "failed": 0, "skipped": 0}
incomplete_files = []


def handle_ctrl_c(signum, frame):
    global shutdown_requested
    if shutdown_requested:
        print(t("interrupt2"))
        sys.exit(1)
    print(t("interrupt1"))
    shutdown_requested = True


signal.signal(signal.SIGINT, handle_ctrl_c)


def describe_problem(result):
    """Build a readable summary of what went wrong, from result.errors / result.pages."""
    lines = []
    try:
        for err in (result.errors or [])[:6]:
            msg = getattr(err, "error_message", None) or str(err)
            mod = getattr(err, "module_name", "") or ""
            lines.append(f"      - {mod + ': ' if mod else ''}{msg}")
    except Exception:
        pass
    try:
        total = len(result.pages)
        if total:
            lines.append(t("pages_in_doc", n=total))
    except Exception:
        pass
    return lines


print(t("init"))

ocr_options = TesseractCliOcrOptions(
    lang=["nld"],
    tesseract_cmd=TESSERACT_PATH
)

pipeline_options = PdfPipelineOptions()
pipeline_options.ocr_options = ocr_options

if LIMIT_MEMORY_USAGE:
    print(t("lowram"))
    pipeline_options.images_scale = 150 / 72
else:
    print(t("maxperf"))

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options)
    }
)

# ==============================================================================
# FOLDER LAYOUT
#
#   <root>\                 only the scripts live here
#     _SOURCE-DOCS\         the documents to convert
#     _FAILED\              documents that could not be converted
#     _WITH-DICT.out\       markdown from a run WITH the word list
#     _NO-DICT.out\         markdown from a run WITHOUT it
#
# Markdown is written straight into its output folder. An earlier version
# wrote it next to the sources and let the .cmd wrapper move it afterwards,
# which meant a crash left the output stranded and a second run could not tell
# what was already done. Writing to the destination immediately also makes the
# "already converted" check meaningful across runs.
#
# RECOVERY ROUND: copy this script plus ocr_words_patch.py into _FAILED and run
# it there. Sources are then read from _FAILED itself, markdown still goes to
# the output folder one level up, and a document that finally succeeds is moved
# back to _SOURCE-DOCS so the main folder stays the single source of truth.
# ==============================================================================
SOURCE_DIRNAME = "_SOURCE-DOCS"
FAILED_DIRNAME = "_FAILED"
WITH_DICT_DIRNAME = "_WITH-DICT.out"
NO_DICT_DIRNAME = "_NO-DICT.out"

current_dir = os.path.abspath(".")
is_in_failed_folder = os.path.basename(current_dir).upper() == FAILED_DIRNAME

# root_dir is where the four working folders live: one level up during a
# recovery round, otherwise the folder the script was started in.
root_dir = os.path.dirname(current_dir) if is_in_failed_folder else current_dir

source_dir = current_dir if is_in_failed_folder else os.path.join(root_dir, SOURCE_DIRNAME)
failed_dir = current_dir if is_in_failed_folder else os.path.join(root_dir, FAILED_DIRNAME)
output_dir = os.path.join(root_dir, WITH_DICT_DIRNAME if DICT_ACTIVE else NO_DICT_DIRNAME)
# Where a recovered document goes once it converts successfully.
recovered_dir = os.path.join(root_dir, SOURCE_DIRNAME)

for folder in (source_dir, failed_dir, output_dir):
    if not os.path.exists(folder):
        os.makedirs(folder)

extensions = ["*.pdf", "*.png", "*.jpg", "*.jpeg", "*.webp"]
document_files = []
for ext in extensions:
    document_files.extend(glob.glob(os.path.join(source_dir, ext)))

# Documents left over from the old flat layout: report them rather than
# silently ignoring the folder the user has always used.
if not is_in_failed_folder and not document_files:
    stray = []
    for ext in extensions:
        stray.extend(glob.glob(os.path.join(root_dir, ext)))
    if stray:
        print(t("stray_docs", n=len(stray), folder=SOURCE_DIRNAME))

if not document_files:
    print(t("nofiles"))
    # An orderly finish, not a crash -- see write_completion_marker().
    write_completion_marker()
    exit()

print(t("found", n=len(document_files)))

_free, _total, _phys = memory_status()
if _free is None:
    if MIN_FREE_MB:
        print(t("mem_unknown"))
else:
    print(t("mem_at_start", free=_free, total=_total, phys=_phys))

print(t("folders",
        src=os.path.basename(source_dir) if not is_in_failed_folder else FAILED_DIRNAME,
        out=os.path.basename(output_dir),
        fail=FAILED_DIRNAME))
if is_in_failed_folder:
    print(t("ctx_failed"))
print("=" * 40)

for index, file_path in enumerate(document_files, start=1):
    if shutdown_requested:
        break

    file_title = os.path.basename(file_path)
    # Keep the ORIGINAL extension in the .md name, and mark dictionary runs:
    #     no word list -> scan.pdf.md
    #     word list    -> scan.pdf.dic.md
    #
    # Two reasons. First, without the source extension, scan.pdf and scan.jpg
    # would both claim scan.md and one would silently overwrite the other.
    # Second, the .dic marker lets both versions of the same document live in
    # one folder, so they can be compared -- or handed to an agent together,
    # which can then ask for the original PDF when the two disagree.
    md_name = f"{file_title}.dic.md" if DICT_ACTIVE else f"{file_title}.md"

    # Markdown always lands in the output folder for this run's mode.
    target_md_path = os.path.join(output_dir, md_name)
    # During a recovery round the source is moved back to _SOURCE-DOCS once it
    # converts; in a normal round it simply stays where it is.
    target_source_path = os.path.join(recovered_dir, file_title) if is_in_failed_folder else file_path

    # @inv  resume semantics: presence of the target markdown IS the record of
    #       prior work. Output is written straight to its final folder, so this
    #       check survives a crash, a reboot, and a change of wrapper.
    # @edge same source under both modes yields different targets (.dic.md vs
    #       .md), so a dictionary run never skips because of a plain run.
    if os.path.exists(target_md_path):
        print(t("skipping", i=index, n=len(document_files), f=file_title))
        stats["skipped"] += 1
        continue

    print(t("opening", i=index, n=len(document_files), f=file_title))

    # Warn BEFORE the conversion: if the process dies from a C-level
    # allocation failure, nothing further in this script gets to run.
    maybe_warn_memory()

    sys.stdout.flush()

    try:
        print(t("parsing"))
        sys.stdout.flush()

        result = converter.convert(file_path)

        # --- QUALITY GATE ----------------------------------------------------
        # Docling reports PARTIAL_SUCCESS when individual pages were dropped.
        # Without this check a half document would be saved below.
        # @inv  SUCCESS is the ONLY status that may produce markdown
        # @trap PARTIAL_SUCCESS arrives without an exception; the try/except
        #       below never sees it. This comparison is the entire guard.
        status_ok = (result.status == ConversionStatus.SUCCESS)

        if not status_ok and QUARANTINE_INCOMPLETE:
            print(t("incomplete", s=result.status))
            print(t("incomplete_why"))
            for line in describe_problem(result):
                print(line)

            stats["incomplete"] += 1
            incomplete_files.append(file_title)

            if not is_in_failed_folder:
                quarantine_path = os.path.join(failed_dir, file_title)
                print(t("isolating_inc", f=file_title))
                try:
                    shutil.move(file_path, quarantine_path)
                    print(t("isolated_ok"))
                except Exception as move_err:
                    print(t("isolate_err", e=move_err))
            else:
                print(t("retry_inc"))
            sys.stdout.flush()
            continue
        # ---------------------------------------------------------------------

        if not status_ok:
            print(t("saved_anyway", s=result.status))

        print(t("writing"))
        sys.stdout.flush()

        with open(target_md_path, "w", encoding="utf-8") as f:
            f.write(result.document.export_to_markdown())

        print(t("saved"))
        stats["ok"] += 1

        if is_in_failed_folder:
            print(t("moving_back"))
            shutil.move(file_path, target_source_path)
            print(t("moved_back", f=file_title))
        else:
            print(t("saved_to", f=os.path.basename(target_md_path)))

    # @edge BaseException is caught deliberately: docling surfaces some failures
    #       as non-Exception types. KeyboardInterrupt is disambiguated by the
    #       shutdown_requested flag on the first line of the handler.
    except (Exception, BaseException) as e:
        if shutdown_requested:
            print(t("paused"))
            break

        print(t("error", e=e))

        # A MemoryError that Python DID manage to raise: name it plainly,
        # so the cause is not buried in a stack trace.
        if isinstance(e, MemoryError) or "alloc" in str(e).lower() or "memory" in str(e).lower():
            _f, _, _ = memory_status()
            print(t("mem_error", free=_f if _f is not None else "?"))

        sys.stdout.flush()
        stats["failed"] += 1

        # Clean up a half-written .md, otherwise it gets skipped on the next run.
        # @io   removes a half-written target. Without this the next run would
        #       treat the fragment as completed work and skip the document.
        if os.path.exists(target_md_path):
            try:
                os.remove(target_md_path)
                print(t("removed_partial"))
            except Exception:
                pass

        if not is_in_failed_folder:
            quarantine_path = os.path.join(failed_dir, file_title)
            print(t("isolating_fail", f=file_title))
            try:
                shutil.move(file_path, quarantine_path)
                print(t("isolated_ok"))
            except Exception as move_err:
                print(t("isolate_err", e=move_err))
        else:
            print(t("retry_failed"))

    sys.stdout.flush()

# ==============================================================================
# FINAL REPORT
# ==============================================================================
print("=" * 40)
print(t("suspended") if shutdown_requested else t("complete"))

print(t("stat_ok", n=stats["ok"]))
print(t("stat_inc", n=stats["incomplete"]))
print(t("stat_fail", n=stats["failed"]))
print(t("stat_skip", n=stats["skipped"]))

elapsed = time.time() - RUN_STARTED
print()
print(t("time_total", dur=format_duration(elapsed)))
if stats["ok"]:
    print(t("time_per_doc", dur=format_duration(elapsed / stats["ok"]), n=stats["ok"]))
print(t("time_dict_on") if DICT_ACTIVE else t("time_dict_off"))

if incomplete_files:
    print(t("inc_header"))
    for name in incomplete_files:
        print(f"    - {name}")
    print(t("inc_advice"))

if ocr_words_patch:
    # Pass how many documents were actually converted, so a count of zero
    # interceptions is not reported as a fault when nothing needed doing.
    ocr_words_patch.report(stats["ok"] + stats["incomplete"] + stats["failed"])

write_completion_marker()
