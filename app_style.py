COLOR_BG = "#1b1e22"
COLOR_PANEL = "#23272d"
COLOR_PANEL_ALT = "#2a2f36"
COLOR_BORDER = "#383e47"
COLOR_TEXT = "#e6e6e6"
COLOR_TEXT_DIM = "#9aa0a8"
COLOR_ACCENT = "#00c2d1"
COLOR_ACCENT_DARK = "#019aa6"
COLOR_SUCCESS = "#3ddc84"
COLOR_WARNING = "#f5a623"
COLOR_ERROR = "#e5484d"

FONT_FAMILY = "Segoe UI"

STYLESHEET = f"""
QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    font-family: "{FONT_FAMILY}";
    font-size: 12px;
}}
QMainWindow {{
    background-color: {COLOR_BG};
}}
QGroupBox {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 10px 12px 10px;
    font-weight: 600;
    font-size: 12px;
    color: {COLOR_TEXT_DIM};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {COLOR_TEXT};
}}
QLabel[role="title"] {{
    font-size: 19px;
    font-weight: 700;
    color: {COLOR_TEXT};
}}
QLabel[role="heading"] {{
    font-size: 14px;
    font-weight: 700;
    color: {COLOR_TEXT};
}}
QLabel[role="dim"] {{
    color: {COLOR_TEXT_DIM};
    font-size: 11px;
}}
QFrame[role="card"] {{
    background-color: {COLOR_PANEL_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}
QPushButton {{
    background-color: {COLOR_PANEL_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    color: {COLOR_TEXT};
}}
QPushButton:hover {{
    border-color: {COLOR_ACCENT};
}}
QPushButton:pressed {{
    background-color: {COLOR_ACCENT_DARK};
}}
QPushButton:disabled {{
    color: {COLOR_TEXT_DIM};
}}
QPushButton[role="primary"] {{
    background-color: {COLOR_ACCENT_DARK};
    border: 1px solid {COLOR_ACCENT};
    font-weight: 600;
}}
QPushButton[role="primary"]:hover {{
    background-color: {COLOR_ACCENT};
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {COLOR_PANEL_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 5px;
    padding: 3px 6px;
    min-height: 22px;
}}
QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {COLOR_TEXT_DIM};
    background-color: {COLOR_PANEL};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {COLOR_BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {COLOR_ACCENT};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {COLOR_ACCENT_DARK};
    border-radius: 2px;
}}
QSlider:disabled::handle:horizontal {{
    background: {COLOR_TEXT_DIM};
}}
QSlider:disabled::sub-page:horizontal {{
    background: {COLOR_BORDER};
}}
QStatusBar {{
    background-color: {COLOR_PANEL};
    border-top: 1px solid {COLOR_BORDER};
}}
QStatusBar QLabel {{
    padding: 0 4px;
}}
QCheckBox {{
    spacing: 6px;
}}
QScrollArea {{
    border: none;
}}
"""

# Deterministic BGR color per class name, used both for OpenCV drawing
# and (converted to hex) for Qt indicator dots, so a class keeps the
# same color everywhere in the UI across the whole session.
_PALETTE = [
    (66, 194, 244), (86, 214, 130), (235, 172, 56), (214, 94, 94),
    (176, 122, 237), (94, 200, 214), (222, 143, 92), (140, 206, 90),
]


def color_for_class(name):
    index = sum(ord(c) for c in name) % len(_PALETTE)
    return _PALETTE[index]


def bgr_to_hex(bgr):
    b, g, r = bgr
    return f"#{r:02x}{g:02x}{b:02x}"
