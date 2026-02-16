@echo off
setlocal
python -m pip install -r requirements.txt
pyinstaller --noconfirm --onefile --windowed --name CarouselGenerator main.py
echo Done. EXE: dist\CarouselGenerator.exe
