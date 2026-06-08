#!/usr/bin/env python3
import sys
import os
import ctypes


def _get_base():
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


_base = _get_base()
_vlc_dir = os.path.join(_base, "vlc")

if os.path.exists(_vlc_dir):
    libvlccore = os.path.join(_base, "libvlccore.so.9")
    if os.path.exists(libvlccore):
        ctypes.CDLL(libvlccore)
    libvlc = os.path.join(_base, "libvlc.so.5")
    if os.path.exists(libvlc):
        os.environ["PYTHON_VLC_LIB_PATH"] = libvlc
    plugins = os.path.join(_vlc_dir, "plugins")
    if os.path.exists(plugins):
        os.environ["PYTHON_VLC_MODULE_PATH"] = plugins
        os.environ["VLC_PLUGIN_PATH"] = plugins
else:
    os.environ["VLC_PLUGIN_PATH"] = "/usr/lib/vlc/plugins"

os.environ["PYTHONUNBUFFERED"] = "1"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.main_window import MainWindow


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("yTunes")
    app.setOrganizationName("ytunes")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
