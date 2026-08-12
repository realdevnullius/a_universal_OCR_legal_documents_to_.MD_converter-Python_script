@echo off
REM ============================================================================
REM  BASELINE run: conversion WITHOUT the word list. This is the recommended
REM  default; the WITH-DICT run is compared against this one.
REM  BASISRUN: conversie ZONDER woordenlijst. Dit is de aanbevolen standaard;
REM  de WITH-DICT-run wordt hiermee vergeleken.
REM
REM  FOLDER LAYOUT / MAPPENSTRUCTUUR
REM    .\                  scripts only / alleen de scripts
REM    .\_SOURCE-DOCS\     documents to convert / de te converteren documenten
REM    .\_FAILED\          documents that failed / mislukte documenten
REM    .\_WITH-DICT.out\   markdown from a run WITH the word list
REM    .\_NO-DICT.out\     markdown from a run WITHOUT the word list
REM
REM  The Python script writes its markdown straight into the output folder, so
REM  this wrapper no longer moves anything. Nothing is stranded by a crash and a
REM  second run can tell exactly what was already done.
REM
REM  Het Python-script schrijft de markdown rechtstreeks in de uitvoermap, dus
REM  deze wrapper verplaatst niets meer. Een crash laat niets achter op de
REM  verkeerde plek en een tweede run ziet precies wat al gedaan is.
REM ============================================================================
setlocal enabledelayedexpansion

REM ---------------------------------------------------------------------------
REM Always work in the folder this .cmd lives in, whatever launched it.
REM Double-clicking in Explorer already does this, but "Run as administrator"
REM starts in C:\Windows\System32 and a shortcut can start anywhere.
REM ---------------------------------------------------------------------------
cd /d "%~dp0"

REM Fail early and clearly if something is missing, instead of letting Python
REM produce a confusing traceback.
if not exist "%~dp0jpg.pdf.convert.py" (
    echo [CMD] ERROR: jpg.pdf.convert.py not found next to this .cmd file.
    echo [CMD] All files of the toolset must sit in the same folder.
    goto :done
)
if not exist "%~dp0ocr_words_patch.py" (
    echo [CMD] ERROR: ocr_words_patch.py not found next to this .cmd file.
    echo [CMD] All files of the toolset must sit in the same folder.
    goto :done
)
REM No word list needed for the baseline run.
where python >nul 2>&1
if errorlevel 1 (
    echo [CMD] ERROR: "python" was not found on your PATH.
    echo [CMD] Install Python, or edit this .cmd to use the full path to python.exe.
    goto :done
)

set "OCR_WORDS="

REM Language of the script's messages: EN or NL
set "SCRIPT_LANG=EN"

set "FLAG=%CD%\_run_complete.flag"
if exist "%FLAG%" del /q "%FLAG%"

python "%~dp0jpg.pdf.convert.py" %*

REM A hard crash can leave the exit code at 0, so the marker is the real test.
if not exist "%FLAG%" (
    echo.
    echo [CMD] The Python script did not finish cleanly.
    echo [CMD] Markdown produced up to that point is already in _NO-DICT.out -
    echo [CMD] simply run this again and it will resume where it stopped.
    echo.
    echo [CMD] No final report above? The most likely cause is RAM running out.
    echo [CMD] A failed allocation inside Tesseract or PyTorch can kill Python
    echo [CMD] outright, leaving it no chance to report anything. What helps:
    echo [CMD]   - close other programs and simply run this again
    echo [CMD]   - set LIMIT_MEMORY_USAGE = True in jpg.pdf.convert.py
    echo [CMD]   - split very large PDFs into smaller parts
    goto :done
)
del /q "%FLAG%"

:done
endlocal
pause
