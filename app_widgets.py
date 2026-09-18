from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractButton,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app_style import COLOR_ACCENT, COLOR_BORDER


class ToggleSwitch(QAbstractButton):
    """A compact ON/OFF switch used for boolean camera/model settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(42, 22)

    def sizeHint(self):
        return QSize(42, 22)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(COLOR_ACCENT if self.isChecked() else COLOR_BORDER))
        painter.drawRoundedRect(rect, radius, radius)

        handle_d = rect.height() - 6
        x = rect.right() - handle_d - 3 if self.isChecked() else rect.left() + 3
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(int(x), int(rect.top() + 3), int(handle_d), int(handle_d))


class LabeledSlider(QWidget):
    """Name + numeric entry on one line, a slider on the line below.

    `scale` lets the same widget back a float value (e.g. confidence,
    0.05 steps) using an integer QSlider internally.
    """

    valueChanged = Signal(object)

    def __init__(self, name, minimum, maximum, value, step=1, scale=1, suffix="", parent=None):
        super().__init__(parent)
        self.scale = scale

        name_label = QLabel(name)
        name_label.setProperty("role", "dim")

        if scale == 1:
            self.spin = QSpinBox()
            self.spin.setRange(int(minimum), int(maximum))
            self.spin.setSingleStep(int(step))
        else:
            self.spin = QDoubleSpinBox()
            self.spin.setDecimals(2)
            self.spin.setRange(minimum, maximum)
            self.spin.setSingleStep(step)
        self.spin.setSuffix(suffix)
        self.spin.setFixedWidth(84)
        self.spin.setValue(value)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(round(minimum * scale)), int(round(maximum * scale)))
        self.slider.setValue(int(round(value * scale)))

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.addWidget(name_label)
        top_row.addStretch(1)
        top_row.addWidget(self.spin)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(top_row)
        layout.addWidget(self.slider)

        self._syncing = False
        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)

    def _from_slider(self, raw):
        if self._syncing:
            return
        value = raw / self.scale
        self._syncing = True
        self.spin.setValue(value)
        self._syncing = False
        self.valueChanged.emit(value)

    def _from_spin(self, value):
        if self._syncing:
            return
        self._syncing = True
        self.slider.setValue(int(round(value * self.scale)))
        self._syncing = False
        self.valueChanged.emit(value)

    def set_value(self, value):
        self._syncing = True
        self.spin.setValue(value)
        self.slider.setValue(int(round(value * self.scale)))
        self._syncing = False

    def set_enabled_state(self, enabled):
        self.setEnabled(enabled)


class StatusDot(QLabel):
    """Small colored circle used as a connection/state indicator."""

    def __init__(self, color="#9aa0a8", parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self.set_color(color)

    def set_color(self, color):
        self.setStyleSheet(f"background-color: {color}; border-radius: 5px;")


class AspectRatioVideoLabel(QLabel):
    """Displays frames scaled to fit while always preserving aspect ratio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(280, 160)
        self.setStyleSheet("background-color: #000000; border-radius: 8px;")
        self._pixmap = None

    def set_frame(self, qimage):
        self._pixmap = QPixmap.fromImage(qimage)
        self._update_pixmap()

    def resizeEvent(self, event):
        self._update_pixmap()
        super().resizeEvent(event)

    def _update_pixmap(self):
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)


class DualCameraView(QWidget):
    """Stacked comparison: the raw camera feed above its detections.

    The top pane is the untouched camera frame, so it is unaffected by
    the brightness/contrast sliders. The bottom pane is what actually
    gets adjusted and sent to YOLO, with detections drawn on it.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.raw_view, top_pane = self._build_pane("Camera Feed")
        self.processed_view, bottom_pane = self._build_pane("Detections")
        layout.addWidget(top_pane, stretch=1)
        layout.addWidget(bottom_pane, stretch=1)

    @staticmethod
    def _build_pane(title):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        caption = QLabel(title)
        caption.setProperty("role", "dim")
        caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(caption)

        video_label = AspectRatioVideoLabel()
        layout.addWidget(video_label, stretch=1)

        return video_label, container

    def set_frames(self, raw_qimage, processed_qimage):
        self.raw_view.set_frame(raw_qimage)
        self.processed_view.set_frame(processed_qimage)
