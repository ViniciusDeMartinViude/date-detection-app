import os
from collections import Counter

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app_panels import (
    CameraSettingsPanel,
    DetectionResultsPanel,
    ImageAdjustmentsPanel,
    ModelInfoDialog,
    ModelSettingsPanel,
)
from app_style import COLOR_ERROR, COLOR_SUCCESS, COLOR_WARNING
from app_widgets import DualCameraView, StatusDot
from camera_worker import CameraWorker, available_devices
from settings import (
    default_camera_values,
    default_image_values,
    init_camera_values,
    init_image_values,
    load_camera_settings,
    save_camera_settings,
)

MODEL_FILE = os.getenv("MODEL_FILE", "best_bal_1.pt")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), MODEL_FILE)
CAMERA_DEVICE = int(os.getenv("CAMERA_DEVICE", "0"))


class MainWindow(QMainWindow):
    # Forwarded to the CameraWorker living on its own QThread.
    controlChanged = Signal(str, object)
    imageAdjustmentChanged = Signal(str, object)
    runningChanged = Signal(bool)
    showCoordinatesChanged = Signal(bool)
    confidenceChanged = Signal(float)
    iouChanged = Signal(float)
    deviceChanged = Signal(object)
    modelLoadRequested = Signal(str)
    resolutionChanged = Signal(int, int)
    cameraIndexChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Engineering - Live Date Detection")
        self.resize(1600, 900)

        self.total_counts = Counter()
        self.frame_count = 0
        self.model_info = None  # (filename, sections) for the currently loaded model
        self._show_info_when_ready = False

        self._build_ui()
        self._start_worker()

    # ---- UI construction --------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(self._build_title_bar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, stretch=1)

        saved = load_camera_settings()
        self.camera_settings_panel = CameraSettingsPanel(init_camera_values(saved), camera_device=CAMERA_DEVICE)
        self.image_adjustments_panel = ImageAdjustmentsPanel(init_image_values(saved))
        self.model_settings_panel = ModelSettingsPanel(available_devices(), os.path.basename(MODEL_PATH))

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_layout.addWidget(self.camera_settings_panel)
        left_layout.addWidget(self.image_adjustments_panel)
        left_layout.addWidget(self.model_settings_panel)
        left_layout.addStretch(1)

        # The settings column can need more height than a shorter or
        # maximized-but-not-tall-enough window provides; without a
        # scroll area Qt squeezes whichever panel has the most "shrink
        # slack" (camera settings, with its 4 stacked cards) down below
        # its own content, which looks like overlapping/garbled labels.
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setWidget(left)
        left_scroll.setMinimumWidth(260)
        left_scroll.setMaximumWidth(320)

        self.video_view = DualCameraView()

        self.detection_panel = DetectionResultsPanel()
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.addWidget(self.detection_panel, stretch=1)
        right_layout.addWidget(self._build_session_controls())

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setWidget(right)
        right_scroll.setMinimumWidth(260)
        right_scroll.setMaximumWidth(340)

        splitter.addWidget(left_scroll)
        splitter.addWidget(self.video_view)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([280, 1300, 300])

        self.setStatusBar(self._build_status_bar())

        self.camera_settings_panel.controlChanged.connect(self.controlChanged)
        self.camera_settings_panel.resetRequested.connect(self._on_reset_camera_settings)
        self.camera_settings_panel.cameraIndexChanged.connect(self.cameraIndexChanged)
        self.camera_settings_panel.resolutionChanged.connect(self.resolutionChanged)

        self.image_adjustments_panel.adjustmentChanged.connect(self.imageAdjustmentChanged)
        self.image_adjustments_panel.resetRequested.connect(self._on_reset_image_adjustments)

        self.model_settings_panel.confidenceChanged.connect(self.confidenceChanged)
        self.model_settings_panel.iouChanged.connect(self.iouChanged)
        self.model_settings_panel.deviceChanged.connect(self.deviceChanged)
        self.model_settings_panel.inferenceToggled.connect(self._on_inference_toggled)
        self.model_settings_panel.loadModelRequested.connect(self._on_load_model_requested)
        self.model_settings_panel.showModelInfoRequested.connect(self._show_model_info)

        self.detection_panel.showCoordinatesToggled.connect(self.showCoordinatesChanged)

        self._set_running_indicator(True)

    def _build_title_bar(self):
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("AI Engineering – Live Date Detection")
        title.setProperty("role", "title")
        layout.addWidget(title)
        layout.addStretch(1)

        self.run_state_dot = StatusDot()
        self.run_state_label = QLabel()
        self.run_state_label.setProperty("role", "dim")
        layout.addWidget(self.run_state_dot)
        layout.addWidget(self.run_state_label)
        return bar

    def _build_session_controls(self):
        frame = QFrame()
        frame.setProperty("role", "card")
        layout = QHBoxLayout(frame)

        self.start_pause_btn = QPushButton("Pause")
        self.start_pause_btn.setProperty("role", "primary")
        self.start_pause_btn.clicked.connect(self._toggle_running)

        reset_btn = QPushButton("Reset Statistics")
        reset_btn.clicked.connect(self._reset_statistics)

        layout.addWidget(self.start_pause_btn)
        layout.addWidget(reset_btn)
        return frame

    def _build_status_bar(self):
        bar = QStatusBar()

        self.camera_dot = StatusDot()
        self.camera_status_label = QLabel("Camera: Connecting...")
        self.model_status_label = QLabel(f"Model: {os.path.basename(MODEL_PATH)}")
        self.device_status_label = QLabel("Device: -")
        self.resolution_status_label = QLabel("- x -")
        self.fps_status_label = QLabel("FPS: -")
        self.inference_status_label = QLabel("Inference: -")

        for label in (
            self.camera_status_label, self.model_status_label, self.device_status_label,
            self.resolution_status_label, self.fps_status_label, self.inference_status_label,
        ):
            label.setProperty("role", "dim")

        bar.addWidget(self.camera_dot)
        bar.addWidget(self.camera_status_label)
        bar.addWidget(self._vline())
        bar.addWidget(self.model_status_label)
        bar.addWidget(self._vline())
        bar.addWidget(self.device_status_label)
        bar.addPermanentWidget(self.resolution_status_label)
        bar.addPermanentWidget(self._vline())
        bar.addPermanentWidget(self.fps_status_label)
        bar.addPermanentWidget(self._vline())
        bar.addPermanentWidget(self.inference_status_label)
        return bar

    @staticmethod
    def _vline():
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        return line

    # ---- worker wiring -------------------------------------------------
    def _start_worker(self):
        self.worker_thread = QThread(self)
        self.worker = CameraWorker(MODEL_PATH, camera_index=CAMERA_DEVICE)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.start)
        self.worker.frameReady.connect(self._on_frame_ready)
        self.worker.cameraStateChanged.connect(self._on_camera_state_changed)
        self.worker.modelStateChanged.connect(self._on_model_state_changed)
        self.worker.modelInfoReady.connect(self._on_model_info_ready)
        self.worker.errorOccurred.connect(self._on_error)

        self.controlChanged.connect(self.worker.set_camera_control)
        self.imageAdjustmentChanged.connect(self.worker.set_image_adjustment)
        self.runningChanged.connect(self.worker.set_running)
        self.showCoordinatesChanged.connect(self.worker.set_show_coordinates)
        self.confidenceChanged.connect(self.worker.set_confidence)
        self.iouChanged.connect(self.worker.set_iou)
        self.deviceChanged.connect(self.worker.set_device)
        self.modelLoadRequested.connect(self.worker.load_model)
        self.resolutionChanged.connect(self.worker.set_resolution)
        self.cameraIndexChanged.connect(self.worker.switch_camera)

        for name, value in self.camera_settings_panel.current_values().items():
            self.controlChanged.emit(name, value)
        for name, value in self.image_adjustments_panel.current_values().items():
            self.imageAdjustmentChanged.emit(name, value)

        self.worker_thread.start()

        device_label = self.model_settings_panel.device_combo.currentText()
        self.device_status_label.setText(f"Device: {device_label}")

    def closeEvent(self, event):
        self.worker.stop()
        self.worker_thread.quit()
        self.worker_thread.wait(2000)
        combined_settings = {
            **self.camera_settings_panel.current_values(),
            **self.image_adjustments_panel.current_values(),
        }
        save_camera_settings(combined_settings)
        super().closeEvent(event)

    # ---- slots ----------------------------------------------------------
    def _on_reset_camera_settings(self):
        defaults = default_camera_values()
        self.camera_settings_panel.set_values(defaults)
        for name, value in defaults.items():
            self.controlChanged.emit(name, value)

    def _on_reset_image_adjustments(self):
        defaults = default_image_values()
        self.image_adjustments_panel.set_values(defaults)
        for name, value in defaults.items():
            self.imageAdjustmentChanged.emit(name, value)

    def _on_inference_toggled(self, enabled):
        self.runningChanged.emit(enabled)
        self._set_running_indicator(enabled)

    def _toggle_running(self):
        self.model_settings_panel.set_inference_enabled(
            not self.model_settings_panel.inference_toggle.isChecked()
        )

    def _set_running_indicator(self, running):
        self.run_state_dot.set_color(COLOR_SUCCESS if running else COLOR_WARNING)
        self.run_state_label.setText("Running" if running else "Paused")
        self.start_pause_btn.setText("Pause" if running else "Resume")

    def _reset_statistics(self):
        self.frame_count = 0
        self.total_counts = Counter()
        self.detection_panel.update_results({}, self.total_counts, self.frame_count)

    def _on_frame_ready(self, result):
        self.video_view.set_frames(result.raw_image, result.processed_image)
        self.frame_count += 1
        self.total_counts.update(result.current_counts)
        self.detection_panel.update_results(result.current_counts, self.total_counts, self.frame_count)
        self.resolution_status_label.setText(f"{result.frame_width} x {result.frame_height}")
        self.fps_status_label.setText(f"FPS: {result.fps:.1f}")
        self.inference_status_label.setText(f"Inference: {result.inference_ms:.1f} ms")

    def _on_camera_state_changed(self, connected):
        self.camera_dot.set_color(COLOR_SUCCESS if connected else COLOR_ERROR)
        self.camera_status_label.setText("Camera: Connected" if connected else "Camera: Disconnected")

    def _on_model_state_changed(self, filename):
        self.model_status_label.setText(f"Model: {filename}")

    def _on_load_model_requested(self, path):
        self._show_info_when_ready = True
        self.modelLoadRequested.emit(path)

    def _on_model_info_ready(self, filename, sections):
        self.model_info = (filename, sections)
        self.model_settings_panel.set_model_info_available(True)
        if self._show_info_when_ready:
            self._show_info_when_ready = False
            self._show_model_info()

    def _show_model_info(self):
        if self.model_info is None:
            return
        filename, sections = self.model_info
        ModelInfoDialog(filename, sections, self).exec()

    def _on_error(self, message):
        self._show_info_when_ready = False
        self.camera_status_label.setText(message)
