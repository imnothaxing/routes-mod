# Routes Mod Overlay 😎

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/OS-Windows-green)](https://www.microsoft.com/windows)

Python component of Routes Mod Overlay. Works with CTJS to display route videos in-game. 

---

## Features

- Overlay/window that can sit on top of other applications
- Settings can be changed via settings.txt
- Navigate route videos with Back / Next buttons  
- Dynamic overlay scaling  
- Filters routes based on available items  
- Uses a local HTTP server (`127.0.0.1:8123`) for proper YouTube referrer support  

---

## Requirements

- **Python 3.11+**  
- **Windows OS** (requires `pywin32`)  
- Recommended: use a virtual environment  

---

## Installation

```bash
git clone https://github.com/imnothaxing/routes-mod.git
cd routes-mod
pip install -r requirements.txt
```

## Build

use build.bat to compile(assuming you have nuitka installed. if you dont make sure to)

if you prefer to use pyinstaller

```bash
pyinstaller --onefile main.py
```

## Notes

- Ensure ports 8080 (TCP server) and 8123 (Flask server) are free.

- Port 8123 is also used for YouTube referrer support and for reloading videos.

- Overlay scaling can be adjusted with the in-app controls.

- Make sure to launch the exe once so windows trusts it.

- Customize your experience via settings.txt.

## Contributing 

Pull requests and issues are welcome. Please test on Windows before submitting.



