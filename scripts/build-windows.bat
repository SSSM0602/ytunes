@echo off
setlocal enabledelayedexpansion

echo ==^> Building yTunes for Windows x86_64...
echo     Requires: VLC installed at C:\Program Files\VideoLAN\VLC

set VLC_DIR=C:\Program Files\VideoLAN\VLC
if not exist "%VLC_DIR%" (
    echo ERROR: VLC not found at %VLC_DIR%
    echo        Install VLC from https://videolan.org
    exit /b 1
)

if exist build\pyinstaller rmdir /s /q build\pyinstaller
if exist build\pyinstaller-work rmdir /s /q build\pyinstaller-work

pyinstaller ^
    --onefile ^
    --windowed ^
    --name ytunes ^
    --add-binary "%VLC_DIR%\libvlc.dll;." ^
    --add-binary "%VLC_DIR%\libvlccore.dll;." ^
    --add-binary "%VLC_DIR%\vlc.exe;." ^
    --add-data "%VLC_DIR%\plugins;vlc\plugins" ^
    --collect-all PyQt6 ^
    --hidden-import yt_dlp ^
    --hidden-import vlc ^
    --hidden-import requests ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --distpath build\pyinstaller ^
    --workpath build\pyinstaller-work ^
    --noconfirm ^
    main.py

echo.
echo ==^> Done! Executable: build\pyinstaller\ytunes.exe
for %%f in (build\pyinstaller\ytunes.exe) do echo Size: %%~zf bytes
