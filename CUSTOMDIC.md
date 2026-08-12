# Building Your Own Custom Dictionary

## What the word list actually is

`dutch_legal_lean.words` is a plain text file. One word per line, nothing else. No weights, no frequencies, no structure.

Tesseract accepts such a file through `--user-words`. The words in it are added to the dictionary its decoder consults when it is unsure what it just read. When the shapes on the page could plausibly be `huipofficier` or `hulpofficier`, a dictionary hit tips the balance.

Getting that file to Tesseract is the awkward part. Docling calls Tesseract internally and exposes no way to pass extra command-line flags, so `ocr_words_patch.py` intercepts the `subprocess.run` call and inserts `--user-words <path>` at the correct position — after the input and output arguments, before any config file. Docling appends `tsv`; options placed after it are ignored.

You control it with one environment variable:

```
OCR_WORDS set and the file exists  ->  the flag is added
OCR_WORDS empty or unset           ->  nothing happens
```

That is the entire mechanism. `ocr-without-dict.cmd` clears the variable (the baseline), `ocr-with-dict.cmd` sets it, and the two write to different output folders so you can compare them.

---

## Set your expectations first

On Tesseract 4 and 5 the LSTM engine weights its own visual recognition far above dictionary hints. A word list nudges; it does not correct.

Measured over 249 documents: **247 identical, 2 different (0.8%)**. Of those two, one was a genuine fix and the other an artefact of the comparison. Across the whole batch the word list improved exactly one word. Net effect: roughly zero, and the run without the word list was also faster.

That is not a reason to skip this. It is a reason to **measure** rather than assume. `deduplicate.py` gives you the number for your own material in one command, and a domain with heavier jargon than Dutch legal Dutch may well do better.

---

## You do not have to stay in law

There is nothing legal about the machinery. The word list is just vocabulary Tesseract does not already know.

Any field with its own terminology works the same way, and the further your vocabulary sits from everyday language, the more a dictionary has to offer:

- medicine, pharmacology, veterinary
- shipping, aviation, rail
- chemistry, materials, engineering
- accounting, insurance, tax
- archaeology, taxonomy, botany
- genealogy and historical records
- a single company's product names, part numbers, and internal jargon

That last one is often the strongest case. A generic language model has never seen your internal abbreviations; a word list is the cheapest way to teach it.

---

## The prompt

Fill in the two bracketed values and hand this to a capable AI agent — one with web search, so it can verify the environment rather than rely on memory.

Then read the result critically. An agent producing 1,700 lines of vocabulary is producing 1,700 opportunities to be confidently wrong.

---

```
I need you to build a custom word list for Tesseract OCR.

    LANGUAGE: [fill in — e.g. German, Portuguese, Japanese]
    COUNTRY:  [fill in — e.g. Austria, Brazil, Japan]

===========================================================================
PART 1 — CHECK THE ENVIRONMENT BEFORE YOU START
===========================================================================

This word list will be used in the following pipeline. Before writing a
single word, verify that this stack is still current and that none of the
technical claims below have been superseded. Search the web; do not answer
from memory. Software moves, and a word list built against wrong assumptions
is wasted effort.

    Windows x64
    Python 3.9+ (Microsoft Store build)
    Tesseract OCR 5.x, installed via the UB Mannheim Windows installer
    IBM Docling (layout analysis, calls Tesseract internally)
    Word list passed via --user-words

Report on each of the following, and say plainly when something has changed:

  1. Is Tesseract 5.x still current? Has a version 6 shipped, and if so does
     --user-words still behave the same way?
  2. On the LSTM engine, how much influence does --user-words actually have?
     Confirm or correct this claim: the visual recognition layer heavily
     outweighs dictionary hints, so a word list nudges rather than corrects.
  3. Is there now a better mechanism than --user-words for the same goal —
     for example a compiled word_dawg built with combine_lang_model, or
     lightweight fine-tuning? If so, say so, and say what it costs.
  4. Does Docling still call Tesseract through subprocess.run, and does it
     still append a "tsv" config argument after the options?
  5. Is there a maintained public word list for [LANGUAGE] that would make
     part of this work redundant?

If any answer changes what the word list should look like, say so before
you build it.

===========================================================================
PART 2 — WHAT TO COLLECT
===========================================================================

Build a vocabulary of terms specific to the legal system of [COUNTRY],
written in [LANGUAGE]. Work systematically through that country's actual
legal landscape rather than producing a generic list. Cover at minimum:

  - civil law, obligations, property
  - criminal law and criminal procedure
  - civil procedure and the court hierarchy
  - administrative law
  - employment law
  - family law and succession
  - corporate and insolvency law
  - tax law
  - the areas that are distinctive to [COUNTRY] specifically

That last point matters most. Every country has institutions, procedures,
and offices that exist nowhere else, and those are exactly the words a
general-purpose language model has never seen. Find them.

Include:
  - the names of courts, tribunals, and supervisory bodies
  - names of the statutes and codes as practitioners actually write them
  - procedural terms of art
  - the job titles of legal professionals
  - Latin terms that appear as standalone words in that country's rulings

===========================================================================
PART 3 — CHARACTER RULES (STRICT)
===========================================================================

One word per line. No line may contain a space.

ALLOWED:
  - letters, including the diacritics of [LANGUAGE]
  - the hyphen "-", but only inside genuinely hyphenated words
  - the period ".", but only inside abbreviations (see Part 4)

NOT ALLOWED, anywhere:
  - spaces, tabs
  - / \ : ; , ' " ( ) [ ] { } < > | & * ? ! # @ € $ % + =
  - digits
  - multi-word phrases

On hyphens, be careful. Only include one where the word is genuinely written
with a hyphen. Do NOT invent hyphens as a way of smuggling in a multi-word
phrase: writing "kort-geding" for what is actually written "kort geding"
teaches the OCR to expect a hyphen that is not on the page. In an earlier
version of this list, dozens of such fabricated hyphens had to be removed.

On diacritics, include BOTH forms of every word that carries one:

    beëindiging      (correct)
    beeindiging      (same word, diacritics stripped)

The reason is not sloppy typing. It is that a diaeresis or accent is a few
pixels tall. On a fax, a third-generation photocopy, or a phone snapshot,
those pixels are simply not there. The OCR must be able to read what is
physically on the page. Fidelity to the document beats orthographic
correctness in a pipeline whose output may be used as evidence.

There is a real trade-off here: with both forms present, a damaged accent
will no longer be corrected back to the right spelling. That is the intended
choice. Note it in your output so the user makes it knowingly.

===========================================================================
PART 4 — ABBREVIATIONS: USEFUL, BUT THE MAIN RISK
===========================================================================

Include the abbreviations practitioners actually use, WITH their periods.
Tesseract treats "art." as a single token, and having it in the dictionary
helps it understand that the period belongs to the word rather than ending
the sentence.

But understand what you are doing. Short entries are where a word list does
its damage:

  - A two- or three-letter token resembles a great many other short strings.
    Every one you add is another candidate the decoder can wrongly settle on.
  - Common abbreviations such as "e.g." or "etc." are already in the base
    language model. Adding them gains nothing and costs decoder weight.
  - Bare short words are worse still. Standalone Latin fragments such as
    "in", "pro", "res", "ex", "sub" overlap with ordinary words and with
    noise. If you include Latin, prefer complete distinctive terms over
    fragments, and flag the short ones separately so the user can drop them.

Rule of thumb: include a short entry only when it is genuinely specific to
[COUNTRY]'s legal domain AND unlikely to already be in the base dictionary.
"drs." earns its place in Dutch; "e.g." does not.

Where a country has an authoritative citation guide for abbreviations, use
it and say which one you used. Do not invent abbreviations that look
plausible — an invented abbreviation is worse than a missing one, because
it teaches the OCR to expect something that never appears.

===========================================================================
PART 5 — CAPITALISATION (LEARN FROM OUR MISTAKE)
===========================================================================

Include BOTH forms of every word:

    piketadvocaat
    Piketadvocaat

This is not padding. We originally lowercased the entire list, on the
assumption that Tesseract's dictionary lookup handles a leading capital by
itself. Measurement proved otherwise: across a 249-document batch, the list
actively rewrote "Piketadvocaat" to "piketadvocaat" — a real regression, in a
document type where a sentence-initial capital carries meaning. Adding the
capitalised variant removed it, confirmed by re-converting that document.

So: for every entry, add the variant with the first letter capitalised.
Capitalise the FIRST LETTER ONLY. Do not title-case the rest:

    advocaat-generaal  ->  Advocaat-generaal    correct
    advocaat-generaal  ->  Advocaat-Generaal    wrong

For statute abbreviations that are conventionally written in capitals,
supply the canonical form as practitioners write it, plus lower and upper
variants, since these appear both mid-sentence and at the start of one.

===========================================================================
PART 6 — SIZE, AND WHY BIGGER IS NOT BETTER
===========================================================================

A larger word list is not a better one. Every entry is another string the
decoder may wrongly settle on, so a list padded with ordinary vocabulary
makes recognition worse while appearing more thorough.

Leave out words any general dictionary for [LANGUAGE] already knows. The
list should contain what the base model does NOT know: domain terms,
institution names, statute abbreviations, terms of art.

For calibration, here is the reference list this project actually uses:

    1,715 lines total
      875 base entries, each with a capitalised variant
       34 entries carrying diacritics (each with an ASCII twin)
       64 entries containing a period (abbreviations)
       23 entries containing a hyphen
      875 entries beginning with a capital
    Average length 14.3 characters; shortest 2, longest 33

That average is the number to notice. A list averaging six characters is
full of ordinary short words and will hurt more than it helps.

===========================================================================
PART 7 — THE DATA SET IT WAS BUILT AGAINST
===========================================================================

Context for what this vocabulary was tuned to, anonymised:

  - 249 documents in one batch
  - a mix of PDFs and phone photographs (.pdf, .jpg)
  - scanned correspondence, court filings, email threads printed to PDF,
    and long AI-chat transcripts exported as PDF
  - largest document: over 150 pages in a single PDF
  - typical document: 1 to 10 pages
  - some file names ran past 150 characters
  - image sources ranged from clean 300 dpi scans to handheld phone
    snapshots with uneven lighting; some pages carried no resolution
    metadata at all, and Tesseract fell back to 70 dpi
  - hardware: a consumer Windows desktop with roughly 8 GB usable RAM,
    which was the binding constraint throughout — documents beyond about
    150 pages failed with std::bad_alloc

Outcome with the word list active, across those 249 documents:

    247 identical to the run without the list
      2 different (0.8%), of which:
          1 genuine correction  (huipofficier -> hulpofficier)
          1 artefact of the comparison, not a real difference

That is one improved word in 249 documents. An earlier round of the same
benchmark, before capitalised variants were added, also produced one
regression; see Part 5. Net effect: approximately zero, and the run without
the list was measurably faster.

Do not treat this as a reason to build a bad list. Treat it as the standard
to beat, and as evidence that the honest answer here is a measurement rather
than a promise.

===========================================================================
PART 8 — WHAT TO DELIVER
===========================================================================

  1. The word list itself, one word per line, plain UTF-8 text, as a file
     named <language>_legal.words

  2. A short report stating:
     - your findings from Part 1, especially anything that has changed
     - which sources you used, and which are authoritative versus inferred
     - the entry count, and the breakdown by category as in Part 6
     - which entries you are LEAST confident about, so they can be checked
     - which short entries you would drop first if the list underperforms

  3. An honest statement of what you could not verify. A word list full of
     plausible-looking invented terms is worse than a shorter honest one:
     invented entries actively teach the OCR to expect text that is not
     there. If you are unsure whether a term is real, leave it out and say
     so.

Do not pad the list to reach a number. Quality of entries beats quantity,
and the measurement in Part 7 is what will judge the result.
```

---

## After the agent delivers

1. Save the file next to the scripts.
2. Point `ocr-with-dict.cmd` at it — change the `OCR_WORDS` line to your filename.
3. Convert a representative sample both ways.
4. Run `dedup_outputs.cmd` (or `python deduplicate.py --dry-run`).

That last step gives you a percentage. Under one percent, and the list is not earning its keep — drop it and enjoy the faster runs. Meaningfully higher, and you have found a domain where dictionaries still pay.

Either answer is worth having. Guessing is not.
