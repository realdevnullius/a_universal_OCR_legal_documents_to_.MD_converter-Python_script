"""
================================================================================
LEGAL & JUDICIAL DOCUMENT TO MARKDOWN BATCH CONVERTER (DOCLING + TESSERACT OCR)
================================================================================

1. WHAT THIS SCRIPT DOES:
-------------------------
This utility batch-converts complex legal files, judicial correspondence, court 
decisions, and photographed case evidence into structured, LLM-ready Markdown (.md). 
It is explicitly optimized for privacy-centric offline processing on Windows x64 
systems running Microsoft Store isolated Python 3.9 and native Tesseract OCR.
Key features include:
  - Advanced layout analysis to cleanly preserve text hierarchy (e.g., email threads).
  - Pristine extraction of AI-generated ASCII tables without breaking cells or alignments.
  - Custom path-routing to bypass Windows Store AppContainer sandbox lookup failures.
  - Native Dutch language ('nld') text, character, and legal term recognition.

2. SUPPORTING OTHER FILE TYPES:
------------------------------
Thanks to Docling's robust multi-format document assembly backend, you can ingest 
many other legal data inputs without installing any extra software on your computer. 
The system inherently reads and parses Word Documents (.docx), Powerpoint Slides 
(.pptx), Web and Rich Content (.html, .xhtml, .rtf).
To activate these file extensions, simply look at Section 2 in the script below 
and append any of these formats to the 'extensions' list (e.g., adding "*.docx").

3. AVAILABLE OCR LANGUAGES (TESSERACT SELECTION):
-------------------------------------------------
When installing Tesseract OCR on Windows via the binary installer, you can select 
from 41 layout, script, and language data packs. This script targets Dutch ('nld') 
by default, but any of the following shorthand codes can be added to 'lang=["..."]' 
to process international legal strategies, cross-border correspondence, or scripts:
  - Core Languages: 
    'eng' (English), 'nld' (Dutch), 'equ' (Math/Equations), 'osd' (Orientation/Script)
  - Regional Alphabets & Scripts:
    'script\\Arabic', 'script\\Armenian', 'script\\Bengali', 'script\\Cyrillic',
    'script\\Devanagari', 'script\\Ethiorig', 'script\\Fraktur' (Gothic text), 
    'script\\Georgian', 'script\\Greek', 'script\\Gujarati', 'script\\Gurmukhi', 
    'script\\Hebrew', 'script\\Kannada', 'script\\Khmer', 'script\\Lao', 'script\\Latin', 
    'script\\Malayalam', 'script\\Myanmar', 'script\\Oriya', 'script\\Sinhala', 
    'script\\Syriac', 'script\\Tamil', 'script\\Telugu', 'script\\Thaana', 
    'script\\Thai', 'script\\Tibetan', 'script\\Vietnamese'
  - East Asian Layouts (Standard & Vertical):
    'script\\HanS' / 'script\\HanS_vert' (Simplified Chinese)
    'script\\HanT' / 'script\\HanT_vert' (Traditional Chinese)
    'script\\Hangul' / 'script\\Hangul_vert' (Korean)
    'script\\Japanese' / 'script\\Japanese_vert' (Japanese)
    'script\\Canadian_Aboriginal', 'script\\Cherokee'

4. THE '_FAILED' RECOVERY WORKFLOW (MULTI-ROUND OPTIMIZATION):
--------------------------------------------------------------
Processing hundreds of dense scans can trigger unpredictable OS memory allocation bottlenecks. 
If a specific document encounters a system failure (like an "std::bad_alloc" heap ceiling), 
the script automatically isolates the problematic source file into a specialized 
subfolder named './_FAILED'. This prevents a single corrupt document from freezing the main queue.

Experience demonstrates that sequential passes frequently succeed where primary rounds fail, 
due to system memory freeing up. Follow this recovery loop:
  1. Let the primary script execution complete its pass over the main directory.
  2. Copy this script ('jpg.pdf.convert.py') directly into the newly created './_FAILED' folder.
  3. Run the script inside the '_FAILED' folder via PowerShell: python .\\jpg.pdf.convert.py
  4. The script will dynamically adjust its context. Any file successfully parsed during this 
     second pass will automatically have its newly minted '.md' output AND its original source 
     document migrated back up to your root project directory cleanly.
  5. (Optional) For highly stubborn files, change the 'LIMIT_MEMORY_USAGE' variable below to 
     True to downscale the image parser resolution to 150 DPI and save memory.

================================================================================
"""

import os
import glob
import sys
import shutil
import signal
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions

# ==============================================================================
# CONFIGURATION SETTINGS
# ==============================================================================
LIMIT_MEMORY_USAGE = False 
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# ==============================================================================

# Global exit flag for graceful intercept
shutdown_requested = False

def handle_ctrl_c(signum, frame):
    global shutdown_requested
    if shutdown_requested:
        print("\n[CRITICAL] Force quitting immediately...")
        sys.exit(1)
    print("\n[INTERRUPT] Ctrl+C detected! Completing current file action and shutting down gracefully...")
    print("Press Ctrl+C again to force exit immediately.")
    shutdown_requested = True

# Register the custom signal handler for clean user termination
signal.signal(signal.SIGINT, handle_ctrl_c)

print("Initializing Robust Legal Docling Pipeline...")

ocr_options = TesseractCliOcrOptions(
    lang=["nld"],
    tesseract_cmd=TESSERACT_PATH
)

pipeline_options = PdfPipelineOptions()
pipeline_options.ocr_options = ocr_options

if LIMIT_MEMORY_USAGE:
    print("[INFO] Low-RAM Optimization enabled. Scaling layout resolution to ~150 DPI.")
    pipeline_options.images_scale = 150 / 72
else:
    print("[INFO] Maximum performance mode active. High-resolution scaling unconstrained.")

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options)
    }
)

current_dir = os.path.abspath(".")
is_in_failed_folder = os.path.basename(current_dir) == "_FAILED"
main_dir = os.path.dirname(current_dir) if is_in_failed_folder else current_dir
failed_dir = current_dir if is_in_failed_folder else os.path.join(current_dir, "_FAILED")

if not os.path.exists(failed_dir):
    os.makedirs(failed_dir)

extensions = ["*.pdf", "*.png", "*.jpg", "*.jpeg", "*.webp"]
document_files = []
for ext in extensions:
    document_files.extend(glob.glob(os.path.join(current_dir, ext)))

if not document_files:
    print("No supported files found in this directory!")
    exit()

print(f"Found {len(document_files)} document(s)/photo(s) to process.")
if is_in_failed_folder:
    print("[CONTEXT] Running inside the _FAILED folder. Successful recoveries will move back up.")
print("="*40)

# Main process loop
for index, file_path in enumerate(document_files, start=1):
    # Intercept queue right before opening a file if termination flag is thrown
    if shutdown_requested:
        break

    file_title = os.path.basename(file_path)
    base_name, _ = os.path.splitext(file_title)
    
    if is_in_failed_folder:
        target_md_path = os.path.join(main_dir, f"{base_name}.md")
        target_source_path = os.path.join(main_dir, file_title)
    else:
        target_md_path = os.path.join(current_dir, f"{base_name}.md")
        target_source_path = file_path

    if os.path.exists(target_md_path):
        print(f"[{index}/{len(document_files)}] Skipping (Already Converted): {file_title}")
        continue
        
    print(f"[{index}/{len(document_files)}] Opening: {file_title}")
    sys.stdout.flush()
    
    try:
        print("   -> Parsing layout and executing Tesseract Dutch OCR...")
        sys.stdout.flush()
        
        result = converter.convert(file_path)
        
        print("   -> Writing Markdown data...")
        sys.stdout.flush()
        
        with open(target_md_path, "w", encoding="utf-8") as f:
            f.write(result.document.export_to_markdown())
            
        print(f"   [SUCCESS] Saved Markdown successfully.")
        
        if is_in_failed_folder:
            print("   -> Moving source file back to main directory...")
            shutil.move(file_path, target_source_path)
            print(f"   [SUCCESS] Cleanly moved {file_title} back to root folder.\n")
        else:
            print(f"   [SUCCESS] Saved to: {os.path.basename(target_md_path)}\n")
            
    except (Exception, BaseException) as e:
        # Check if the error caught was actually the user typing Ctrl+C during file action
        if shutdown_requested:
            print(f"   [INTERRUPT] Conversion paused on user request.\n")
            break
            
        print(f"   [ERROR] Failed during conversion. Reason: {e}")
        sys.stdout.flush()
        
        if not is_in_failed_folder:
            quarantine_path = os.path.join(failed_dir, file_title)
            print(f"   -> Isolating failed document to: .\\_FAILED\\{file_title}")
            try:
                shutil.move(file_path, quarantine_path)
                print("   [SUCCESS] File moved safely.\n")
            except Exception as move_err:
                print(f"   [ERROR] Could not isolate file: {move_err}\n")
        else:
            print("   [RETRY FAILED] File remains locked inside the _FAILED cache directory.\n")
            
    sys.stdout.flush()

if shutdown_requested:
    print("="*40 + "\nPipeline execution suspended cleanly by user. Safe to close.")
else:
    print("="*40 + "\nBatch directory iteration complete!")
