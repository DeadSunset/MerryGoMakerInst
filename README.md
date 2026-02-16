# Carousel Generator

Windows desktop app for generating Instagram carousels (1080x1350) locally.

## Stack
- Python 3.11+
- PySide6 (UI)
- skia-python (render)
- PyInstaller (one-file EXE)

## Run
```bash
python -m pip install -r requirements.txt
python main.py
```

## Build EXE
Run `build.bat` on Windows. It generates:
- `dist/CarouselGenerator.exe`

## Features implemented
- Local project folder bootstrap (`Project/` with templates/styles/jobs/output/assets/settings)
- Template support with text/image regions
- Text style presets with Windows font family names
- Two synchronized editing modes:
  - Block editor (`Карточки` tab)
  - Human-readable script (`Сценарий` tab)
- Slide reorder-related ops: add/delete/duplicate
- Live preview with zoom
- Overflow-safe text rendering (`wrap`, `clip`, `ellipsis`, `shrink-to-fit`)
- Image fit modes (`cover`, `contain`, `stretch`)
- Per-slide crop state (`scale`, `offsetX`, `offsetY`) editable in crop dialog
- Export PNG/JPG rendering all slides into timestamped output folder
- Error handling with warnings for missing image/style/font fallback
