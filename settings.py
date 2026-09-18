import json
import os

import cv2

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera_settings.json")

# name, cv2 property, min, max, default.
# Auto Exposure/Focus/WB must be turned OFF (0) before the manual
# control next to it will actually take effect on most webcams.
CAMERA_CONTROLS = [
    ("Auto Exposure", cv2.CAP_PROP_AUTO_EXPOSURE, 0, 1, 1),
    ("Exposure", cv2.CAP_PROP_EXPOSURE, -13, 0, -6),
    ("Auto Focus", cv2.CAP_PROP_AUTOFOCUS, 0, 1, 1),
    ("Focus", cv2.CAP_PROP_FOCUS, 0, 255, 0),
    ("Auto White Balance", cv2.CAP_PROP_AUTO_WB, 0, 1, 1),
    ("WB Temperature", cv2.CAP_PROP_WB_TEMPERATURE, 2000, 8000, 4600),
]


def load_camera_settings():
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_camera_settings(values_by_name):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(values_by_name, f, indent=2)


def default_camera_values():
    return {name: default for name, _prop, _lo, _hi, default in CAMERA_CONTROLS}


def init_camera_values(saved_settings):
    values = {}
    for name, _prop, lo, hi, default in CAMERA_CONTROLS:
        values[name] = max(lo, min(hi, saved_settings.get(name, default)))
    return values


# name, min, max, default. These are software adjustments applied with
# OpenCV to the captured frame before it is handed to YOLO - unlike
# CAMERA_CONTROLS above, none of these map to a cv2.VideoCapture
# property, so they work identically regardless of webcam/driver.
IMAGE_ADJUSTMENTS = [
    ("Brightness", -100, 100, 0),
    ("Contrast", 50, 300, 100),
]


def default_image_values():
    return {name: default for name, _lo, _hi, default in IMAGE_ADJUSTMENTS}


def init_image_values(saved_settings):
    values = {}
    for name, lo, hi, default in IMAGE_ADJUSTMENTS:
        values[name] = max(lo, min(hi, saved_settings.get(name, default)))
    return values
