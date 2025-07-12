@echo off
nuitka index.py ^
 --onefile ^
 --standalone ^
 --include-package=screeninfo ^
 --include-package=requests ^
 --include-module=win32api ^
 --include-module=win32event ^
 --windows-console-mode=disable ^
 --output-dir=build ^
 --windows-icon-from-ico=fow.ico
pause