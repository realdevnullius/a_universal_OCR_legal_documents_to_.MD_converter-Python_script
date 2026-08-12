# Legal & Judicial Document to Markdown Batch Converter

Batch-converts court decisions, legal correspondence, dense email threads, and photographed case evidence into structured, LLM-ready Markdown.

Built on **IBM Docling** for layout analysis and **Tesseract OCR** for text recognition. Runs entirely offline. Targeted at Windows x64 with Microsoft Store Python, where sandboxed paths tend to break naive setups.

The tool ships with an optional custom Dutch legal word list, and with the tooling to **measure whether that word list actually helps** — including honest results from a 249-document run. See [CUSTOMDIC.md](CUSTOMDIC.md) to build one for your own language and subject area.

---

## Folder layout

The repository root holds only scripts. Everything else lives in four working folders, created automatically on first run:

```
.\                      the scripts
  _SOURCE-DOCS\         put your documents here
  _FAILED\              documents that failed to convert (usually RAM)
  _WITH-DICT.out\       markdown from a run WITH the word list
  _NO-DICT.out\         markdown from a run WITHOUT it
```

Markdown is written straight into its output folder. Nothing is staged and moved afterwards, so an interrupted run leaves no files stranded and simply resumes where it stopped.

---

## Files in this repository

| File | Purpose |
|---|---|
| `jpg.pdf.convert.py` | The converter. All settings live at the top. |
| `ocr_words_patch.py` | Injects `--user-words` into the Tesseract call Docling makes internally. Docling exposes no way to pass extra flags, so this intercepts `subprocess.run`. |
| `ocr-without-dict.cmd` | Runs the conversion **without** the word list. This is the baseline and the recommended default. |
| `ocr-with-dict.cmd` | The same conversion **with** the word list, for comparison. |
| `dutch_legal_lean.words` | 1,715 Dutch legal terms and abbreviations. |
| `deduplicate.py` | Compares the two output folders and reports whether the word list changed anything. |
| `dedup_outputs.cmd` | Wrapper for `deduplicate.py`: pre-flight counts, dry run, confirmation, then a summary. |
| `check_markdown.py` | Flags markdown that may be missing pages. |
| `CUSTOMDIC.md` | How the word list works, and a ready-made AI prompt to build your own. |

---

## Setup (Windows x64)

### 1. Python

Install **Python 3.9 or newer** from the Microsoft Store. The scripts are written to survive the isolated user profile paths that version creates.

### 2. Tesseract OCR

Download the Windows x64 installer, for example from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).

During setup, expand **Additional language data** and tick the language you need — `nld` for Dutch. The default install path is `C:\Program Files\Tesseract-OCR\tesseract.exe`; if you change it, update `TESSERACT_PATH` at the top of `jpg.pdf.convert.py`.

### 3. Python packages

```powershell
pip install docling
```

---

## Usage

1. Put your documents in `.\_SOURCE-DOCS\`
2. Double-click `ocr-without-dict.cmd` (the baseline) or `ocr-with-dict.cmd`, or run either from PowerShell.

Both wrappers force the working directory to their own folder, so launching from Explorer, from a shortcut, or via *Run as administrator* all behave identically.

Supported input: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`. Docling also reads `.docx`, `.pptx`, `.html`, `.rtf` — add the extension to the `extensions` list in the script to enable it.

### Output naming

```
brief.pdf   ->  brief.pdf.md        (no word list)
brief.pdf   ->  brief.pdf.dic.md    (word list active)
```

The source extension is kept, so `scan.pdf` and `scan.jpg` cannot overwrite each other's output. The `.dic` marker lets both versions of the same document be compared, or handed to an AI Agent together.

---

## Settings

All at the top of `jpg.pdf.convert.py`:

| Setting | Default | What it does |
|---|---|---|
| `LANGUAGE` | `"EN"` | Language of the script's own messages. `"EN"` or `"NL"`. Not the OCR language. |
| `LIMIT_MEMORY_USAGE` | `False` | Set to `True` to parse at ~150 DPI instead of full resolution. Roughly quarters memory use per page. |
| `TESSERACT_PATH` | Program Files | Full path to `tesseract.exe`. |
| `QUARANTINE_INCOMPLETE` | `True` | Refuse to write markdown when Docling dropped pages. Leave this on. |
| `MIN_FREE_MB` | `2000` | Warn before a document when usable memory falls below this. `0` disables. |
| `MEM_WARN_STEP_MB` | `500` | After the first warning, stay quiet until memory drops another this much. |

The OCR language is set separately, in `lang=["nld"]`. Add further Tesseract language codes there.

`LANGUAGE` can also be overridden without editing the script, by setting `SCRIPT_LANG=NL` in the `.cmd` wrapper or in your shell. The wrappers set it explicitly, so changing one line there is enough.

---

## Recovery workflow

A document that fails — usually `std::bad_alloc` when RAM runs out — is moved to `_FAILED` and no markdown is written for it. A partial document is indistinguishable from a complete one later on, which is exactly the kind of silent error a legal file cannot afford.

```
_SOURCE-DOCS\  ──►  (conversion fails)  ──►  _FAILED\
                                                │
_SOURCE-DOCS\  ◄──  (succeeds on retry)  ◄──  run the script inside _FAILED\
```

To retry:

1. Copy **both** `jpg.pdf.convert.py` and `ocr_words_patch.py` into `.\_FAILED\`
2. Run the `.cmd` there, or `python .\jpg.pdf.convert.py`

Sources are then read from `_FAILED`, markdown still goes to the output folder one level up, and a document that finally converts moves back to `_SOURCE-DOCS`.

Memory usually frees up between runs, so a second pass often succeeds where the first did not. If a document keeps failing, set `LIMIT_MEMORY_USAGE = True` or split very large PDFs.

---

## What a run reports

Every run ends with a summary:

```
Batch complete!
  Fully processed : 249
  Incomplete      : 0
  Failed          : 0
  Skipped         : 0

  Total running time: 1h 04m 10s
  Average per document: 15.5s  (249 converted)
  Word list was ACTIVE during this run.
```

`Average per document` is the figure to compare between runs, since the counts rarely match exactly.

On a clean finish the script writes `_run_complete.flag`, which the `.cmd` wrapper checks. This matters because a C-level allocation failure inside Tesseract or PyTorch can kill Python with **exit code 0 and no traceback** — the exit code alone cannot be trusted. If the marker is absent, the wrapper says so and tells you the run can simply be started again.

---

## Does the word list actually help?

Run both wrappers over the same documents, then double-click `dedup_outputs.cmd`.

It counts both output folders first — the comparison only means something when the two runs covered the same documents — then shows the dry run, asks before deleting anything, and finishes with the figure that answers the question:

```
  The word list changed the output of 2 of 249 documents (0.8%).
```

The scripted equivalent, if you prefer it:

```powershell
python deduplicate.py --dry-run
python deduplicate.py
```

It pairs `_WITH-DICT.out\<name>.dic.md` with `_NO-DICT.out\<name>.md`. Identical pairs mean the word list changed nothing, and the `.dic.md` copy is deleted. Differing pairs are kept, with the differing words listed.

**Results from the 249-document benchmark:**

| | |
|---|---|
| Identical | 247 |
| Different | 2 (0.8%) |

Of those two: one genuine fix (`huipofficier` → `hulpofficier`), and one artefact of the comparison itself — the baseline emitted one extra token, after which the word-by-word walk falls out of step and reports a cascade of pseudo-differences.

So across 249 documents the word list improved exactly one word, and broke nothing.

An earlier round of the same benchmark also produced a regression (`Piketadvocaat` → `piketadvocaat`), caused by a word list that had been lowercased throughout. Adding the capitalised variant of every entry fixed it, and re-running that document confirmed the fix. This is why `dutch_legal_lean.words` carries both forms.

Net effect: roughly zero. On Tesseract 4 and 5 the LSTM engine weights its visual recognition far above dictionary hints, so `--user-words` nudges rather than corrects. The run without the word list was also measurably faster.

The tooling is here so you can measure this for your own material instead of taking anyone's word for it — including mine.

---

## Known limitations

**The pipeline is not deterministic.** Two runs over the same file produced different output, and in one of them a text block was classified as `<!-- image -->` and its text disappeared. Spot-check anything you intend to rely on.

**Memory is the real bottleneck.** Docling's layout model reserves far more than the document size suggests. PDFs beyond ~150 pages are the usual failure point.

**Not a substitute for reading the original.** OCR output is a search and analysis aid. For anything that matters, check it against the source document.

---

## Privacy

Everything runs locally. No cloud APIs, no telemetry, no document leaves the machine.

The included `.gitignore` uses an allow-list: everything is ignored, and only the project's own files are added back. `_SOURCE-DOCS\` and `_FAILED\` appear on GitHub as empty folders; the output folders are never published at all. If you fork this, keep that arrangement — a deny-list can miss a file type nobody anticipated.
