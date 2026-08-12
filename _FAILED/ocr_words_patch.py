"""
ocr_words_patch.py  --  VERSION 3
================================================================================

ENGLISH
-------
Injects --user-words into the Tesseract call that Docling makes internally.

Why this way: Docling's TesseractCliOcrOptions does not (as far as is known)
pass extra command-line flags through. Rather than replacing Docling -- and
losing its layout analysis and markdown export -- this module intercepts the
subprocess call itself and adds the flag in the right position.

v3: report() accepts the number of documents converted, so a count of
zero interceptions is not flagged as a fault when nothing needed doing.
If you see "report() takes 0 positional arguments", this file is older
than jpg.pdf.convert.py -- replace it.

IMPORTANT (v2): only subprocess.run is replaced.
An earlier version also replaced subprocess.Popen. That broke Python's
asyncio, which does this at import time:

    class Popen(subprocess.Popen):

You can only inherit from a class, not from a function. The old patch turned
it into a function, producing:

    TypeError: function() argument 'code' must be code, not str

Popen is therefore left alone. Docling calls Tesseract via subprocess.run,
so that is sufficient. If the end-of-run report says no calls were
intercepted, your Docling version uses a different route -- report that back.

Position in the command matters. Tesseract's syntax is:
    tesseract INPUT OUTPUT [options...] [configfile...]
Options MUST come before any configfile (Docling appends "tsv"). The flag is
therefore inserted at position 3, right after input and output.

Controlled by the OCR_WORDS environment variable:
    OCR_WORDS set and file exists  -> flag is added
    OCR_WORDS empty or unset       -> nothing happens (clean baseline run)

At the end of the run, report() states whether anything was actually
intercepted. That is the only reliable check: Tesseract itself reports
NOTHING when a word list is missing or fails to load.

NEDERLANDS
----------
Schuift --user-words in de Tesseract-aanroep die Docling intern doet.

Waarom zo: Docling's TesseractCliOcrOptions laat (voor zover bekend) geen
extra command-line vlaggen door. In plaats van Docling te vervangen -- en
daarmee de layoutanalyse en markdown-uitvoer kwijt te raken -- onderschept
deze module de subprocess-aanroep zelf en voegt de vlag op de juiste plek toe.

v3: report() accepteert het aantal geconverteerde documenten, zodat nul
onderschepte aanroepen niet als fout wordt gemeld als er niets te doen was.
Ziet u "report() takes 0 positional arguments", dan is dit bestand ouder
dan jpg.pdf.convert.py -- vervang het.

BELANGRIJK (v2): alleen subprocess.run wordt vervangen.
Een eerdere versie verving ook subprocess.Popen. Dat brak Python's asyncio,
dat op importmoment dit doet:

    class Popen(subprocess.Popen):

Erven kan alleen van een klasse, niet van een functie. De oude patch maakte
er een functie van, met als gevolg:

    TypeError: function() argument 'code' must be code, not str

Popen blijft daarom ongemoeid. Docling roept Tesseract via subprocess.run
aan, dus dat volstaat. Meldt het eindrapport dat er geen enkele aanroep is
onderschept, dan gebruikt uw Docling-versie een andere weg -- meld dat terug.

De plek in het commando is belangrijk. Tesseract's syntax is:
    tesseract INVOER UITVOER [opties...] [configfile...]
Opties MOETEN voor een eventuele configfile staan (Docling zet er "tsv"
achteraan). De vlag wordt daarom ingevoegd op positie 3, direct na invoer
en uitvoer.

Aansturing via de omgevingsvariabele OCR_WORDS:
    OCR_WORDS gevuld en bestand bestaat  -> vlag wordt toegevoegd
    OCR_WORDS leeg of niet gezet         -> niets gebeurt (schone basisrun)

Aan het eind van de run vertelt report() of er daadwerkelijk iets is
onderschept. Dat is de enige betrouwbare controle: Tesseract zelf meldt
NIETS als een woordenlijst ontbreekt of niet geladen wordt.
================================================================================
"""

import os
import subprocess

PATCH_VERSION = "3"

_words_path = (os.environ.get("OCR_WORDS") or "").strip().strip('"')
_hits = 0
_active = False

# Language of this module's messages. Follows SCRIPT_LANG so it matches the
# main script's LANGUAGE setting. "EN" (default) or "NL".
_LANG = (os.environ.get("SCRIPT_LANG") or "EN").strip().upper()
if _LANG not in ("EN", "NL"):
    _LANG = "EN"

_MSG = {
    "off":       {"EN": "[WORDLIST v{v}] Off -- OCR_WORDS not set. This is the baseline run.",
                  "NL": "[WOORDENLIJST v{v}] Uit -- OCR_WORDS niet gezet. Dit is de basisrun."},
    "missing":   {"EN": "[WORDLIST v{v}] ERROR: file not found: {p}",
                  "NL": "[WOORDENLIJST v{v}] FOUT: bestand niet gevonden: {p}"},
    "aborted":   {"EN": "                Run aborted; otherwise you would measure something else.",
                  "NL": "                Run afgebroken; anders meet u iets anders dan u denkt."},
    "on":        {"EN": "[WORDLIST v{v}] On -- {n} entries from {f}",
                  "NL": "[WOORDENLIJST v{v}] Aan -- {n} regels uit {f}"},
    "warn_none": {"EN": "[WORDLIST v{v}] WARNING: no Tesseract call was intercepted.\n"
                        "                The word list was NOT used. Docling apparently calls\n"
                        "                Tesseract differently than expected -- please report this.",
                  "NL": "[WOORDENLIJST v{v}] WAARSCHUWING: geen enkele Tesseract-aanroep onderschept.\n"
                        "                De woordenlijst is NIET gebruikt. Docling roept Tesseract\n"
                        "                kennelijk anders aan dan verwacht -- meld dit terug."},
    "done":      {"EN": "[WORDLIST v{v}] {n} Tesseract call(s) given --user-words.",
                  "NL": "[WOORDENLIJST v{v}] {n} Tesseract-aanroep(en) voorzien van --user-words."},
    "nothing_to_do": {"EN": "[WORDLIST v{v}] Nothing was converted this run, so Tesseract was never\n"
                            "                called. That is expected -- not a problem with the list.",
                      "NL": "[WOORDENLIJST v{v}] Er is niets geconverteerd, dus Tesseract is niet\n"
                            "                aangeroepen. Dat hoort zo -- geen probleem met de lijst."},
}


def _t(key, **kw):
    """Look up a message in the configured language and fill in placeholders."""
    entry = _MSG.get(key, {})
    text = entry.get(_LANG) or entry.get("EN") or key
    return text.format(v=PATCH_VERSION, **kw)


def _looks_like_tesseract(cmd):
    """
    Recognise a Tesseract call by its first argument.

    @pre  cmd is whatever the caller passed to subprocess.run
    @edge shell string form is rejected outright: rewriting a quoted command
          line by string surgery is not safely reversible, and docling does
          not use that form
    @edge empty list / None -> False, so an unrelated malformed call passes
          through untouched rather than raising inside the patch
    """
    if not cmd:
        return False
    if isinstance(cmd, (list, tuple)):
        first = cmd[0]
    else:
        return False  # shell string: left alone, too risky to rewrite
    return "tesseract" in str(first).lower()


def _inject(cmd):
    """
    Insert --user-words after INPUT and OUTPUT (index 1 and 2).

    @inv  idempotent: an argv already carrying --user-words is returned as-is
    @inv  never mutates the caller's list; operates on a copy
    @edge argv shorter than 3 elements -> append at the end. Tesseract will
          reject such a call anyway; the patch must not be what raises.
    @post _hits incremented exactly once per genuine injection
    """
    global _hits
    cmd = list(cmd)
    if "--user-words" in cmd:
        return cmd
    pos = 3 if len(cmd) >= 3 else len(cmd)
    cmd[pos:pos] = ["--user-words", _words_path]
    _hits += 1
    return cmd


def enable():
    """
    Activate the patch. Does nothing when OCR_WORDS is empty.

    @ret  True when patched, False for a deliberate no-dictionary run
    @io   raises SystemExit(2) when OCR_WORDS names a file that is not there
    @why  hard exit rather than a warning: a run that silently measures the
          wrong thing is worse than a run that does not start
    @inv  the original subprocess.run is captured in a closure, so a second
          enable() would stack rather than replace -- call it exactly once
    """
    global _active

    if not _words_path:
        print(_t("off"))
        return False

    if not os.path.isfile(_words_path):
        print(_t("missing", p=_words_path))
        print(_t("aborted"))
        raise SystemExit(2)

    with open(_words_path, encoding="utf-8") as fh:
        n = sum(1 for line in fh if line.strip())
    print(_t("on", n=n, f=os.path.basename(_words_path)))

    # ONLY subprocess.run. Popen stays a class -- see the note at the top.
    _original_run = subprocess.run

    def patched_run(*args, **kwargs):
        if args and _looks_like_tesseract(args[0]):
            args = (_inject(args[0]),) + args[1:]
        elif "args" in kwargs and _looks_like_tesseract(kwargs["args"]):
            kwargs["args"] = _inject(kwargs["args"])
        return _original_run(*args, **kwargs)

    subprocess.run = patched_run
    _active = True
    return True


def report(conversions_attempted=None, *_ignored, **_kwargs):
    """
    Print whether the flag was actually passed through.

    Pass the number of documents that were actually converted this run. When
    that is 0 (everything was skipped as already done), no Tesseract call was
    ever made, so a count of zero interceptions means nothing is wrong and no
    warning is printed.
    """
    if not _active:
        return
    if _hits == 0:
        if conversions_attempted == 0:
            print(_t("nothing_to_do"))
        else:
            print(_t("warn_none"))
    else:
        print(_t("done", n=_hits))
