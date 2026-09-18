import ctypes
import os
import sys

# Must happen before Qt initializes anything: python.exe itself is not
# marked DPI-aware, so on a fractional display scale (e.g. 125%) Windows
# silently bitmap-stretches the whole window, which is what produces
# blurry/ghosted text and misaligned-looking controls. Per-Monitor-v2
# (not the older shcore v1 API) is what's needed for maximize/resize to
# recompute correctly instead of re-triggering the same scaling glitch.
try:
    DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
    if not ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
        raise OSError("SetProcessDpiAwarenessContext failed")
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE (v1 fallback)
    except Exception:
        pass

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

from app_style import STYLESHEET
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
