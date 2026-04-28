# Windows OCR Setup

ABW image and screenshot ingest uses local OCR before any provider-assisted path.
On Windows, the recommended local stack is Tesseract OCR plus the existing Python image libraries.

## Recommended Stack

- Python: 3.13
- Tesseract OCR: 5.x, UB Mannheim Windows build
- Python packages already used by ABW image/PDF ingest: `pillow`, `opencv-python`, `PyMuPDF`, `pdf2image`

PaddleOCR is intentionally optional. It is heavier, pulls a larger runtime stack, and is less predictable on Python 3.13 Windows machines. Use Tesseract as the default MOM rollout path unless a specific machine needs higher OCR accuracy and can tolerate the extra dependency footprint.

## Install Tesseract

Preferred manual install:

1. Download the Windows installer from the UB Mannheim Tesseract build page.
2. Install to the default path:

```powershell
C:\Program Files\Tesseract-OCR\tesseract.exe
```

3. Open a new terminal and verify:

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

Optional PATH setup:

```powershell
setx PATH "$env:PATH;C:\Program Files\Tesseract-OCR"
```

ABW does not require PATH if Tesseract is installed in the default location. It also honors these explicit overrides:

```powershell
$env:ABW_TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:TESSERACT_EXE = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Validate

```powershell
.\abw.bat doctor
.\abw.bat ingest raw\screenshot.png
```

The ingest draft should include `local_ocr_provider_chain`, a selected provider of `tesseract`, and an OCR token count greater than zero for readable screenshots.
