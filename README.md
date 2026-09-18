# AI Engineering – Live Date Detection

A desktop application that uses a webcam and a YOLO model to detect and
classify date fruits in real time. Built with PySide6, OpenCV and
Ultralytics YOLO.

Features:
- Live video split into two views: the raw camera feed and the
  annotated detection output.
- Camera hardware controls (exposure, focus, white balance) with
  auto/manual switches.
- Software brightness/contrast adjustment applied before inference.
- Adjustable confidence/IoU thresholds, device selection (CPU/CUDA/MPS),
  and the ability to load a different `.pt` model at runtime.
- A detection results panel (current frame + running session totals)
  and a status bar with camera/model/FPS/inference-time info.
- Camera settings persist across runs in `camera_settings.json`.

## 1. Requirements

- Python 3.10–3.12 (tested with 3.11)
- A webcam
- A trained YOLO weights file (`.pt`) for date-fruit detection — **not
  included in this repo** (see step 4)
- Optional: an NVIDIA GPU with CUDA for faster inference (the app falls
  back to CPU automatically if none is found)

## 2. Clone the repository

```bash
git clone https://github.com/ViniciusDeMartinViude/date-detection-app.git
cd date-detection-app
```

## 3. Set up a Python environment

Using `venv`:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

Or using conda:

```bash
conda create -n date-detection python=3.11
conda activate date-detection
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

> **GPU note:** `requirements.txt` installs the default PyPI build of
> PyTorch (CPU-only on most platforms). If you have an NVIDIA GPU and
> want CUDA acceleration, install torch first from the PyTorch CUDA
> index *before* running `pip install -r requirements.txt`, e.g.:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu126
> ```
> (pick the CUDA version matching your driver from
> [pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/)).

## 4. Configure the app (`.env`)

Copy the example env file and edit it:

```bash
cp .env.example .env
```

```dotenv
# .env
MODEL_FILE=best_bal_1.pt
CAMERA_DEVICE=0
```

- `MODEL_FILE` — filename of your YOLO weights (`.pt`). This repo does
  **not** include a trained model, so place your own weights file in
  the project root and set `MODEL_FILE` to match its name.
- `CAMERA_DEVICE` — the OpenCV camera index to open on startup (`0` is
  usually the default/built-in webcam; try `1`, `2`, etc. if you have
  more than one camera attached). This can also be changed later from
  the Camera Settings panel while the app is running.

`.env` is gitignored (it's machine-specific config), which is why
`.env.example` exists as the template to copy.

## 5. Run the app

```bash
python detection.py
```

On first launch a "Camera Controls" allow-access prompt may appear
depending on your OS privacy settings — allow it so OpenCV can open the
webcam.

## 6. Using the app

- **Camera Settings (left panel):** pick a camera index/resolution, and
  toggle Auto Exposure/Focus/White Balance off to unlock the manual
  sliders next to them (most webcams ignore the manual value while
  auto is on).
- **Image Adjustments (left panel):** Brightness/Contrast are applied
  in software (OpenCV) before the frame is sent to the model — these
  affect the "Detections" pane but not the "Camera Feed" pane.
- **Model / AI (left panel):** adjust the confidence/IoU thresholds,
  switch inference device, toggle inference on/off, or load a
  different `.pt` file with **Load Model**.
- **Detection Results (right panel):** live per-class counts for the
  current frame and cumulative session totals. Check **Show center
  coordinates** to overlay each detection's pixel center (useful if a
  downstream system, e.g. a robotic arm, needs pickup coordinates).
- **Session controls:** **Pause/Resume** stops/resumes inference
  without closing the camera; **Reset Statistics** clears the frame and
  detection counters without restarting the camera.
- Camera settings (exposure/focus/white balance/brightness/contrast)
  are saved automatically to `camera_settings.json` on exit and
  restored the next time you launch the app.

## Project structure

| File | Purpose |
|---|---|
| `detection.py` | Application entry point |
| `main_window.py` | Main window: layout, status bar, wiring between UI and the camera worker |
| `camera_worker.py` | Runs camera capture + YOLO inference on a background thread |
| `app_panels.py` | Camera Settings, Image Adjustments, Model/AI, and Detection Results panels |
| `app_widgets.py` | Reusable custom widgets (toggle switch, labeled slider, video view, status dot) |
| `app_style.py` | Dark theme stylesheet and per-class color palette |
| `settings.py` | Camera control definitions and persistence (`camera_settings.json`) |
