import os
import time
from collections import Counter
from dataclasses import dataclass
from typing import Dict

import cv2
import torch
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtGui import QImage
from ultralytics import YOLO

from app_style import color_for_class
from model_info import collect_model_info
from settings import CAMERA_CONTROLS

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720


def select_device():
    if torch.cuda.is_available():
        return 0
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def available_devices():
    options = []
    if torch.cuda.is_available():
        options.append(("CUDA:0", 0))
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        options.append(("MPS", "mps"))
    options.append(("CPU", "cpu"))
    return options


@dataclass
class FrameResult:
    raw_image: QImage
    processed_image: QImage
    current_counts: Dict[str, int]
    frame_width: int
    frame_height: int
    fps: float
    inference_ms: float


def draw_detections(frame, result, class_names, show_coordinates):
    """Draws boxes/labels/center markers in-place and returns the frame.

    Kept close to the original ultralytics-style annotation, but with a
    percentage confidence label, per-class consistent colors, box
    thickness that scales with resolution, and an optional center
    marker (for the future robotic-arm pickup coordinates).
    """
    height, width = frame.shape[:2]
    thickness = max(1, round(width / 480))
    font_scale = max(0.4, width / 1600)

    for box in result.boxes:
        x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        name = class_names[cls_id]
        color = color_for_class(name)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)

        label = f"{name} {round(conf * 100)}%"
        (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        label_y = max(text_h + 6, y1)
        cv2.rectangle(frame, (x1, label_y - text_h - 6), (x1 + text_w + 8, label_y), color, -1, cv2.LINE_AA)
        cv2.putText(
            frame, label, (x1 + 4, label_y - 4),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (15, 15, 15), 1, cv2.LINE_AA,
        )

        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        marker_size = max(6, thickness * 4)
        cv2.drawMarker(
            frame, (cx, cy), color,
            markerType=cv2.MARKER_CROSS, markerSize=marker_size, thickness=max(1, thickness - 1),
        )
        if show_coordinates:
            cv2.putText(
                frame, f"({cx}, {cy})", (cx + 6, cy - 6),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.85, color, 1, cv2.LINE_AA,
            )

    return frame


class CameraWorker(QObject):
    """Owns the webcam and the YOLO model; runs entirely off the GUI thread.

    A zero-interval QTimer (started once this object is moved to its own
    QThread and start() runs there) drives the capture/inference loop,
    while leaving the thread's Qt event loop free to deliver queued
    slot calls (camera control changes, model reload, etc.) in between
    frames without blocking on a plain `while True` loop.
    """

    frameReady = Signal(object)
    cameraStateChanged = Signal(bool)
    modelStateChanged = Signal(str)
    modelInfoReady = Signal(str, object)
    errorOccurred = Signal(str)

    def __init__(self, model_path, camera_index=0):
        super().__init__()
        self._model_path = model_path
        self._camera_index = camera_index
        self._resolution = (CAMERA_WIDTH, CAMERA_HEIGHT)

        self.camera = None
        self.model = None
        self.device = select_device()

        self._running_inference = True
        self._show_coordinates = False
        self._confidence = 0.60
        self._iou = 0.45
        self._camera_values = {}
        self._brightness = 0
        self._contrast = 100

        self._frame_times = []
        self._last_inference_ms = 0.0
        self._timer = None

    @Slot()
    def start(self):
        try:
            self.model = YOLO(self._model_path)
            self.modelStateChanged.emit(os.path.basename(self._model_path))
            self._emit_model_info(self._model_path)
        except Exception as exc:
            self.errorOccurred.emit(f"Failed to load model: {exc}")

        self._open_camera(self._camera_index)

        self._timer = QTimer()
        self._timer.timeout.connect(self._process_frame)
        self._timer.start(0)

    @Slot()
    def stop(self):
        if self._timer is not None:
            self._timer.stop()
        if self.camera is not None:
            self.camera.release()

    def _open_camera(self, index):
        if self.camera is not None:
            self.camera.release()
        # CAP_DSHOW gives much more reliable access to exposure/focus/white
        # balance controls on Windows than the default MSMF backend.
        self.camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        connected = self.camera.isOpened()
        self.cameraStateChanged.emit(connected)
        if connected:
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])
            for name, value in self._camera_values.items():
                self._apply_camera_value(name, value)

    @Slot(int)
    def switch_camera(self, index):
        self._camera_index = index
        self._open_camera(index)

    @Slot(int, int)
    def set_resolution(self, width, height):
        self._resolution = (width, height)
        if self.camera is not None and self.camera.isOpened():
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    @Slot(str, object)
    def set_camera_control(self, name, value):
        self._camera_values[name] = value
        if self.camera is not None and self.camera.isOpened():
            self._apply_camera_value(name, value)

    def _apply_camera_value(self, name, value):
        for control_name, prop, _lo, _hi, _default in CAMERA_CONTROLS:
            if control_name == name:
                self.camera.set(prop, value)
                break

    @Slot(str, object)
    def set_image_adjustment(self, name, value):
        if name == "Brightness":
            self._brightness = int(value)
        elif name == "Contrast":
            self._contrast = int(value)

    @Slot(bool)
    def set_running(self, running):
        self._running_inference = running

    @Slot(bool)
    def set_show_coordinates(self, show):
        self._show_coordinates = show

    @Slot(float)
    def set_confidence(self, value):
        self._confidence = value

    @Slot(float)
    def set_iou(self, value):
        self._iou = value

    @Slot(object)
    def set_device(self, device):
        self.device = device

    @Slot(str)
    def load_model(self, path):
        try:
            self.model = YOLO(path)
            self._model_path = path
            self.modelStateChanged.emit(os.path.basename(path))
            self._emit_model_info(path)
        except Exception as exc:
            self.errorOccurred.emit(f"Failed to load model: {exc}")

    def _emit_model_info(self, path):
        # Metadata is informational; a failure here must not count as a failed model load.
        try:
            self.modelInfoReady.emit(os.path.basename(path), collect_model_info(self.model, path))
        except Exception as exc:
            self.errorOccurred.emit(f"Could not read model metadata: {exc}")

    def _apply_image_adjustments(self, frame):
        if self._brightness == 0 and self._contrast == 100:
            return frame
        alpha = self._contrast / 100.0
        return cv2.convertScaleAbs(frame, alpha=alpha, beta=self._brightness)

    @staticmethod
    def _to_qimage(frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        # .copy() so the QImage owns its buffer once `rgb` goes out of scope.
        return QImage(rgb.data, width, height, channels * width, QImage.Format_RGB888).copy()

    def _process_frame(self):
        if self.camera is None or not self.camera.isOpened():
            return
        success, frame = self.camera.read()
        if not success:
            return

        # Brightness/contrast are applied only to the copy that feeds
        # inference and the "Detections" pane; the "Camera Feed" pane
        # always shows the untouched raw frame.
        adjusted = self._apply_image_adjustments(frame)

        current_counts = Counter()
        if self._running_inference and self.model is not None:
            start = time.perf_counter()
            result = self.model(
                adjusted,
                conf=self._confidence,
                iou=self._iou,
                device=self.device,
                verbose=False,
            )[0]
            self._last_inference_ms = (time.perf_counter() - start) * 1000
            current_counts = Counter(self.model.names[int(c)] for c in result.boxes.cls)
            processed = draw_detections(adjusted.copy(), result, self.model.names, self._show_coordinates)
        else:
            processed = adjusted

        height, width = frame.shape[:2]

        self._frame_times.append(time.perf_counter())
        self._frame_times = self._frame_times[-30:]
        fps = 0.0
        if len(self._frame_times) >= 2:
            fps = (len(self._frame_times) - 1) / (self._frame_times[-1] - self._frame_times[0])

        self.frameReady.emit(FrameResult(
            raw_image=self._to_qimage(frame),
            processed_image=self._to_qimage(processed),
            current_counts=dict(current_counts),
            frame_width=width,
            frame_height=height,
            fps=fps,
            inference_ms=self._last_inference_ms,
        ))
