@echo off
REM ============================================================================
REM  dedup_outputs.cmd
REM
REM  ENGLISH
REM  Wrapper around deduplicate.py. Compares _WITH-DICT.out against
REM  _NO-DICT.out, deletes the WITH-DICT copy of every byte-identical pair, and
REM  leaves differing pairs alone.
REM
REM  It runs the dry run first, always. Deletion only happens after you confirm.
REM  Before comparing it counts both output folders, because the comparison is
REM  only meaningful when the two runs covered the same documents - an aborted
REM  batch is the usual reason for a mismatch, and it silently skews the result.
REM
REM  NEDERLANDS
REM  Wrapper om deduplicate.py. Vergelijkt _WITH-DICT.out met _NO-DICT.out,
REM  verwijdert de MET-kopie van elk byte-identiek paar, en laat afwijkende
REM  paren staan.
REM
REM  De proefronde draait altijd eerst. Er wordt pas verwijderd na uw
REM  bevestiging. Vooraf worden beide uitvoermappen geteld, want de
REM  vergelijking zegt alleen iets als beide runs dezelfde documenten hebben
REM  gehad - een afgebroken batch is de gebruikelijke oorzaak van een verschil,
REM  en dat vertekent het resultaat ongemerkt.
REM ============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "WITHDIR=%CD%\_WITH-DICT.out"
set "NODIR=%CD%\_NO-DICT.out"

if not exist "%~dp0deduplicate.py" (
    echo [CMD] ERROR: deduplicate.py not found next to this .cmd file.
    goto :done
)
where python >nul 2>&1
if errorlevel 1 (
    echo [CMD] ERROR: "python" was not found on your PATH.
    goto :done
)
if not exist "%WITHDIR%" (
    echo [CMD] ERROR: _WITH-DICT.out does not exist. Run ocr-with-dict.cmd first.
    goto :done
)
if not exist "%NODIR%" (
    echo [CMD] ERROR: _NO-DICT.out does not exist. Run ocr-without-dict.cmd first.
    goto :done
)

REM --- pre-flight -------------------------------------------------------------
REM %%F is never expanded inside these loops, only counted, so file names
REM containing brackets or semicolons cannot break the parser here.
set /a WITHN=0
for %%F in ("%WITHDIR%\*.md") do set /a WITHN+=1
set /a NON=0
for %%F in ("%NODIR%\*.md") do set /a NON+=1

echo ============================================================
echo  BEFORE
echo ============================================================
echo   _WITH-DICT.out : !WITHN! markdown file^(s^)
echo   _NO-DICT.out   : !NON! markdown file^(s^)

if !WITHN! EQU 0 goto :nothing
if !NON! EQU 0 goto :nothing

if not !WITHN! EQU !NON! (
    echo.
    echo   [WARNING] The two folders hold different numbers of files.
    echo   Only documents present in BOTH can be compared; the rest are
    echo   reported as unpaired and are never deleted. The usual cause is a
    echo   run that was interrupted. Re-run the shorter side for a complete
    echo   picture - already converted documents are skipped, so it is cheap.
)

echo.
echo ============================================================
echo  DRY RUN - nothing will be deleted yet
echo ============================================================
python "%~dp0deduplicate.py" --dry-run
if errorlevel 1 (
    echo.
    echo [CMD] deduplicate.py exited with an error. Nothing was deleted.
    goto :done
)

echo.
set "ANSWER="
set /p "ANSWER=Delete the identical WITH-DICT copies now? [y/N] "
if /i not "!ANSWER!"=="y" (
    echo.
    echo [CMD] Nothing deleted. Both output folders are untouched.
    goto :done
)

echo.
echo ============================================================
echo  DELETING IDENTICAL COPIES
echo ============================================================
python "%~dp0deduplicate.py"
if errorlevel 1 (
    echo.
    echo [CMD] deduplicate.py exited with an error partway through.
    echo [CMD] Run it again; it is safe to repeat.
    goto :done
)

REM --- after ------------------------------------------------------------------
REM What survives in _WITH-DICT.out is exactly the set of documents where the
REM word list changed the output. That count IS the answer to "did it help".
set /a WITHLEFT=0
for %%F in ("%WITHDIR%\*.md") do set /a WITHLEFT+=1
set /a REMOVED=WITHN-WITHLEFT

echo.
echo ============================================================
echo  AFTER
echo ============================================================
echo   Identical copies removed : !REMOVED!
echo   Still in _WITH-DICT.out  : !WITHLEFT!
echo   Baseline in _NO-DICT.out : !NON!  ^(untouched^)

if !WITHN! GTR 0 (
    REM Integer maths only: promille first, then split into whole and tenth.
    set /a PERMILLE=WITHLEFT*1000/WITHN
    set /a WHOLE=PERMILLE/10
    set /a TENTH=PERMILLE-WHOLE*10
    echo.
    echo   The word list changed the output of !WITHLEFT! of !WITHN! documents
    echo   ^(!WHOLE!.!TENTH!%%^).
)

if !WITHLEFT! EQU 0 (
    echo.
    echo   Every pair was identical. On this material the word list made no
    echo   measurable difference at all, and the baseline run is also faster.
) else (
    echo.
    echo   A difference is not automatically an improvement - the word list can
    echo   just as easily rewrite a correctly read word into a wrong one. Check
    echo   a few of the differences listed above against the original document
    echo   before drawing a conclusion.
)
goto :done

:nothing
echo.
echo [CMD] One of the output folders is empty, so there is nothing to compare.
echo [CMD] Run both ocr-without-dict.cmd and ocr-with-dict.cmd over the same
echo [CMD] documents first.

:done
echo.
endlocal
pause
