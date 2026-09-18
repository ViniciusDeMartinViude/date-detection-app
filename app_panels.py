import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app_style import bgr_to_hex, color_for_class
from app_widgets import LabeledSlider, ToggleSwitch
from settings import CAMERA_CONTROLS, IMAGE_ADJUSTMENTS

CAMERA_OPTIONS = [("Camera 0 (default)", 0), ("Camera 1", 1), ("Camera 2", 2)]
RESOLUTION_OPTIONS = [("1920 x 1080", (1920, 1080)), ("1280 x 720", (1280, 720)), ("640 x 480", (640, 480))]


class CameraSettingsPanel(QWidget):
    """Camera device/resolution + exposure/focus/white-balance controls.

    Auto Exposure/Focus/White-Balance are boolean, so they're switches;
    the manual values next to them are disabled while their auto switch
    is on, since most webcams ignore the manual value in that state.
    """

    controlChanged = Signal(str, object)
    resetRequested = Signal()
    cameraIndexChanged = Signal(int)
    resolutionChanged = Signal(int, int)

    def __init__(self, initial_values, parent=None):
        super().__init__(parent)
        self._values = dict(initial_values)
        self._toggles = {}
        self._sliders = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(self._build_camera_group())
        layout.addWidget(self._build_control_group("Exposure", "Auto Exposure", "Exposure", "Exposure", ""))
        layout.addWidget(self._build_control_group("Focus", "Auto Focus", "Focus", "Focus", ""))
        layout.addWidget(self._build_control_group(
            "White Balance", "Auto White Balance", "WB Temperature", "Temperature", " K"))

        reset_btn = QPushButton("Reset Camera Settings")
        reset_btn.clicked.connect(self.resetRequested)
        layout.addWidget(reset_btn)

    @staticmethod
    def _card_with_heading(title):
        """A QFrame card with a manual heading label.

        Deliberately not QGroupBox: on this Windows/Qt combination,
        stacked QGroupBoxes render with stale/overlapping pixels after
        the window is maximized (confirmed via screenshot; layout
        geometry itself was always correct, so it's a paint-only
        glitch specific to QGroupBox's native title mechanism). QFrame
        cards use the exact same pattern as DetectionResultsPanel,
        which never showed this issue under the same test.
        """
        frame = QFrame()
        frame.setProperty("role", "card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        heading = QLabel(title.upper())
        heading.setProperty("role", "heading")
        layout.addWidget(heading)

        return frame, layout

    def _build_camera_group(self):
        group, layout = self._card_with_heading("Camera")

        cam_row = QHBoxLayout()
        cam_row.addWidget(QLabel("Camera"))
        cam_combo = QComboBox()
        for label, _index in CAMERA_OPTIONS:
            cam_combo.addItem(label)
        cam_combo.currentIndexChanged.connect(lambda i: self.cameraIndexChanged.emit(CAMERA_OPTIONS[i][1]))
        cam_row.addWidget(cam_combo, stretch=1)
        layout.addLayout(cam_row)

        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Resolution"))
        res_combo = QComboBox()
        for label, _size in RESOLUTION_OPTIONS:
            res_combo.addItem(label)
        res_combo.setCurrentIndex(1)
        res_combo.currentIndexChanged.connect(lambda i: self.resolutionChanged.emit(*RESOLUTION_OPTIONS[i][1]))
        res_row.addWidget(res_combo, stretch=1)
        layout.addLayout(res_row)

        return group

    def _build_control_group(self, title, auto_name, manual_name, slider_label, suffix):
        group, layout = self._card_with_heading(title)

        auto_row = QHBoxLayout()
        auto_row.addWidget(QLabel(auto_name))
        auto_row.addStretch(1)
        toggle = ToggleSwitch()
        auto_default = bool(self._values.get(auto_name, 1))
        toggle.setChecked(auto_default)
        auto_row.addWidget(toggle)
        layout.addLayout(auto_row)

        _name, _prop, lo, hi, default = next(c for c in CAMERA_CONTROLS if c[0] == manual_name)
        slider = LabeledSlider(slider_label, lo, hi, self._values.get(manual_name, default), suffix=suffix)
        slider.set_enabled_state(not auto_default)
        layout.addWidget(slider)

        toggle.toggled.connect(lambda checked: self._on_auto_toggled(auto_name, slider, checked))
        slider.valueChanged.connect(lambda value: self._on_manual_changed(manual_name, value))

        self._toggles[auto_name] = toggle
        self._sliders[manual_name] = slider
        return group

    def _on_auto_toggled(self, auto_name, slider, checked):
        self._values[auto_name] = int(checked)
        slider.set_enabled_state(not checked)
        self.controlChanged.emit(auto_name, int(checked))

    def _on_manual_changed(self, manual_name, value):
        value = int(value)
        self._values[manual_name] = value
        self.controlChanged.emit(manual_name, value)

    def current_values(self):
        return dict(self._values)

    def set_values(self, values):
        self._values.update(values)
        for auto_name, toggle in self._toggles.items():
            if auto_name in values:
                toggle.setChecked(bool(values[auto_name]))
        for manual_name, slider in self._sliders.items():
            if manual_name in values:
                slider.set_value(values[manual_name])


class ImageAdjustmentsPanel(QWidget):
    """Software brightness/contrast, applied with OpenCV before inference.

    Deliberately separate from CameraSettingsPanel: these aren't
    hardware camera properties (no cv2.VideoCapture.set involved), so
    they behave identically on every webcam.
    """

    adjustmentChanged = Signal(str, object)
    resetRequested = Signal()

    def __init__(self, initial_values, parent=None):
        super().__init__(parent)
        self._sliders = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("IMAGE ADJUSTMENTS")
        group_layout = QVBoxLayout(group)

        for name, lo, hi, default in IMAGE_ADJUSTMENTS:
            suffix = " %" if name == "Contrast" else ""
            slider = LabeledSlider(name, lo, hi, initial_values.get(name, default), suffix=suffix)
            slider.valueChanged.connect(lambda value, name=name: self.adjustmentChanged.emit(name, int(value)))
            group_layout.addWidget(slider)
            self._sliders[name] = slider

        reset_btn = QPushButton("Reset Image Adjustments")
        reset_btn.clicked.connect(self.resetRequested)
        group_layout.addWidget(reset_btn)

        layout.addWidget(group)

    def current_values(self):
        return {name: int(slider.spin.value()) for name, slider in self._sliders.items()}

    def set_values(self, values):
        for name, slider in self._sliders.items():
            if name in values:
                slider.set_value(values[name])


class ModelSettingsPanel(QWidget):
    """YOLO model/inference controls: threshold sliders, device, model file."""

    confidenceChanged = Signal(float)
    iouChanged = Signal(float)
    deviceChanged = Signal(object)
    inferenceToggled = Signal(bool)
    loadModelRequested = Signal(str)

    def __init__(self, device_options, model_filename, parent=None):
        super().__init__(parent)
        self._device_options = device_options

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("MODEL / AI")
        group_layout = QVBoxLayout(group)

        model_row = QHBoxLayout()
        self.model_path_edit = QLineEdit(model_filename)
        self.model_path_edit.setReadOnly(True)
        load_btn = QPushButton("Load Model")
        load_btn.clicked.connect(self._on_load_clicked)
        model_row.addWidget(self.model_path_edit, stretch=1)
        model_row.addWidget(load_btn)
        group_layout.addLayout(model_row)

        self.confidence_slider = LabeledSlider("Confidence Threshold", 0.05, 0.95, 0.60, step=0.05, scale=100)
        self.confidence_slider.valueChanged.connect(lambda v: self.confidenceChanged.emit(float(v)))
        group_layout.addWidget(self.confidence_slider)

        self.iou_slider = LabeledSlider("IoU Threshold", 0.05, 0.95, 0.45, step=0.05, scale=100)
        self.iou_slider.valueChanged.connect(lambda v: self.iouChanged.emit(float(v)))
        group_layout.addWidget(self.iou_slider)

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Device"))
        self.device_combo = QComboBox()
        for label, _value in self._device_options:
            self.device_combo.addItem(label)
        self.device_combo.currentIndexChanged.connect(
            lambda i: self.deviceChanged.emit(self._device_options[i][1]))
        device_row.addWidget(self.device_combo, stretch=1)
        group_layout.addLayout(device_row)

        inference_row = QHBoxLayout()
        inference_row.addWidget(QLabel("Inference"))
        inference_row.addStretch(1)
        self.inference_toggle = ToggleSwitch()
        self.inference_toggle.setChecked(True)
        self.inference_toggle.toggled.connect(self.inferenceToggled)
        inference_row.addWidget(self.inference_toggle)
        group_layout.addLayout(inference_row)

        layout.addWidget(group)

    def _on_load_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load YOLO Model", "", "PyTorch Weights (*.pt)")
        if path:
            self.model_path_edit.setText(os.path.basename(path))
            self.loadModelRequested.emit(path)

    def set_inference_enabled(self, enabled):
        self.inference_toggle.setChecked(enabled)


class DetectionResultsPanel(QWidget):
    """Current-frame results (prominent) above cumulative session totals (dim)."""

    showCoordinatesToggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QLabel("Detection Results")
        header.setProperty("role", "heading")
        layout.addWidget(header)

        coord_row = QHBoxLayout()
        self.coord_checkbox = QCheckBox("Show center coordinates")
        self.coord_checkbox.toggled.connect(self.showCoordinatesToggled)
        coord_row.addWidget(self.coord_checkbox)
        coord_row.addStretch(1)
        layout.addLayout(coord_row)

        self.current_card = QFrame()
        self.current_card.setProperty("role", "card")
        self.current_layout = QVBoxLayout(self.current_card)
        layout.addWidget(self.current_card)

        self.session_card = QFrame()
        self.session_card.setProperty("role", "card")
        self.session_layout = QVBoxLayout(self.session_card)
        layout.addWidget(self.session_card)

        layout.addStretch(1)
        self.update_results({}, {}, 0)

    def update_results(self, current_counts, total_counts, frame_count):
        self._clear_layout(self.current_layout)
        title = QLabel("Current Frame")
        title.setProperty("role", "heading")
        self.current_layout.addWidget(title)

        objects_label = QLabel(f"Objects detected: {sum(current_counts.values())}")
        objects_label.setProperty("role", "dim")
        self.current_layout.addWidget(objects_label)

        ranked_current = sorted(current_counts.items(), key=lambda kv: -kv[1])
        for name, count in ranked_current:
            self.current_layout.addWidget(self._class_row(name, count, emphasize=True))
        if not current_counts:
            self.current_layout.addWidget(self._dim_label("No detections"))

        self._clear_layout(self.session_layout)
        session_title = QLabel("Session")
        session_title.setProperty("role", "heading")
        self.session_layout.addWidget(session_title)
        self.session_layout.addWidget(self._dim_label(f"Frames: {frame_count}"))
        self.session_layout.addWidget(self._dim_label(f"Detections: {sum(total_counts.values())}"))

        ranked_total = sorted(total_counts.items(), key=lambda kv: -kv[1])
        for name, count in ranked_total:
            self.session_layout.addWidget(self._class_row(name, count, emphasize=False))
        if not total_counts:
            self.session_layout.addWidget(self._dim_label("No detections yet"))

    @staticmethod
    def _dim_label(text):
        label = QLabel(text)
        label.setProperty("role", "dim")
        return label

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _class_row(name, count, emphasize):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 2, 0, 2)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {bgr_to_hex(color_for_class(name))};")
        row_layout.addWidget(dot)

        name_label = QLabel(name)
        if not emphasize:
            name_label.setProperty("role", "dim")
        row_layout.addWidget(name_label, stretch=1)

        count_label = QLabel(str(count))
        count_label.setAlignment(Qt.AlignRight)
        if not emphasize:
            count_label.setProperty("role", "dim")
        row_layout.addWidget(count_label)

        return row
