# Legal & Judicial Document to Markdown Batch Converter

A robust, privacy-focused tool optimized for batch-converting complex judicial documents, court decisions, legal correspondence (including dense email threads), and photographed case evidence into structured, LLM-ready Markdown (`.md`). 

This script uses **IBM's Docling** for high-fidelity layout preservation and **Tesseract OCR** for absolute text accuracy. It is specifically designed to run on **Windows x64 machines using Microsoft Store Python** without running into sandbox permission errors or path configuration issues.

## Key Features
- **Preserves ASCII Tables:** Accurately extracts AI-generated ASCII formatting tables without breaking cell borders or layouts.
- **Thread Hierarchy Reconstruction:** Identifies email headers (`Fwd:`, dates, metadata) and separates them cleanly from body arguments.
- **Windows Store Sandbox Bypass:** Programmatically maps absolute paths to bypass isolated environment failures.
- **Automated Quarantine & Multi-Pass Recovery:** Automatically separates memory-heavy or problematic files into a `_FAILED` folder so your main queue never locks up.
- **100% Offline & Private:** Keeps sensitive legal strategies and case files entirely on your local machine—zero cloud API data transfers.

---

## Prerequisites (Windows x64 Setup)

### 1. Install Tesseract OCR
1. Download the Windows x64 binaries installer (e.g., from UB Mannheim or official Tesseract repositories).
2. Run the installer. **Important:** During the setup wizard, expand the **Additional Language Data** menu and check the box for **Dutch** (`nld`), or any other required pack from the supported list below.
3. By default, it will install to `C:\Program Files\Tesseract-OCR\tesseract.exe`.

### 2. Install Python Packages
Open Windows PowerShell and run the following command to install the layout extraction frameworks:

```powershell
pip install docling
```

---

## Supported OCR Languages & Scripts

While this pipeline targets Dutch (`nld`) out of the box, you can modify the `lang=["nld"]` array at the top of the script to include any of the **41 language data packs** available during the Tesseract Windows installation:

* **Core Components:** `eng` (English), `nld` (Dutch), `equ` (Math/Equations), `osd` (Orientation & Script Detection)
* **East Asian Layouts (Horizontal & Vertical):** 
  * Simplified Chinese (`script\HanS`, `script\HanS_vert`)
  * Traditional Chinese (`script\HanT`, `script\HanT_vert`)
  * Japanese (`script\Japanese`, `script\Japanese_vert`)
  * Korean (`script\Hangul`, `script\Hangul_vert`)
* **Regional Scripts & Alphabets:** `script\Arabic`, `script\Armenian`, `script\Bengali`, `script\Cyrillic`, `script\Devanagari`, `script\Ethiopic`, `script\Fraktur` (Gothic text), `script\Georgian`, `script\Greek`, `script\Gujarati`, `script\Gurmukhi`, `script\Hebrew`, `script\Kannada`, `script\Khmer`, `script\Lao`, `script\Latin`, `script\Malayalam`, `script\Myanmar`, `script\Oriya`, `script\Sinhala`, `script\Syriac`, `script\Tamil`, `script\Telugu`, `script\Thaana`, `script\Thai`, `script\Tibetan`, `script\Vietnamese`, `script\Canadian_Aboriginal`, `script\Cherokee`

---

## How to Use

1. Place `jpg.pdf.convert.py` into the folder containing your source files.
2. Open PowerShell in that directory and run:
   ```powershell
   python .\jpg.pdf.convert.py
   ```
3. The script will scan for documents, run layout parsing, apply your selected OCR language packs, and save matching `.md` files in place.

### Supported File Formats
By default, the script processes:
- **PDFs:** Digital exports, text reports, or scanned case files (`.pdf`)
- **Images:** Photographed evidence, cellphone snapshots, or page captures (`.png`, `.jpg`, `.jpeg`, `.webp`)

*Tip: To process office assets like Word documents (`*.docx`) or presentations (`*.pptx`), simply open the script and add them to the `extensions` array in Section 2.*

---

## Automated Multi-Round Recovery Lifecycle

Processing hundreds of heavy image scans sequentially can occasionally cause temporary Windows system memory heap bottlenecks (`std::bad_alloc`). This project resolves that issue with a built-in automated quarantine architecture:

```
[Main Folder] ──► (Conversion Fails) ──► [Auto-Moved to _FAILED Subfolder]
                                                    │
[Main Folder] ◄── (Auto-Migrated Back) ◄── [Re-Run Script inside _FAILED]
```

### The 2-Step Recovery Workflow:
1. **First Pass:** Let the primary script finish running in your main directory. Any document that encounters a system processing block is automatically moved down into a newly created `._FAILED/` directory.
2. **Second Pass:** Copy the `jpg.pdf.convert.py` script directly into that `_FAILED` folder and execute it there:
   ```powershell
   cd .\_FAILED
   python .\jpg.pdf.convert.py
   ```
   *System memory usually clears up between runs.* When executed inside the `_FAILED` boundary, any file that successfully completes on this second round will automatically have its newly minted `.md` document **and** its original source file migrated cleanly back up to your root home folder.

### System RAM Constraint Toggle
If you have files that stubbornly fail due to low machine memory, open the script and change the toggle at the top:
```python
LIMIT_MEMORY_USAGE = True
```
This forces the layout pipeline to optimize resources by downscaling processing images to ~150 DPI—saving up to 75% RAM while remaining crisp enough for accurate text decoding.
