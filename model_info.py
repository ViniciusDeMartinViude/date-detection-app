import os
from datetime import datetime

from ultralytics.utils.torch_utils import get_flops, get_num_gradients, get_num_params

MAX_LIST_PREVIEW = 8


def _format_value(value):
    """Render checkpoint values compactly; long numeric histories are summarized."""
    if isinstance(value, float):
        return f"{value:.5g}"
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(v, (int, float)) for v in value) and len(value) > MAX_LIST_PREVIEW:
            return f"{len(value)} values, first={_format_value(value[0])}, last={_format_value(value[-1])}"
        return "[" + ", ".join(_format_value(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {_format_value(v)}" for k, v in value.items()) + "}"
    return str(value)


def _flatten(mapping):
    return [(str(k), _format_value(v)) for k, v in mapping.items()]


def _human_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# Checkpoint entries that are weights/optimizer state or already shown in their own section.
_HANDLED_CKPT_KEYS = {
    "date", "version", "license", "docs", "epoch", "best_fitness", "updates", "model", "ema",
    "optimizer", "scaler", "modelopt", "train_args", "train_metrics", "train_results", "git",
}


def collect_model_info(model, path):
    """Gather every piece of metadata available for a loaded ultralytics YOLO model.

    Returns an ordered list of (section title, [(key, value string), ...]).
    """
    sections = []

    stat = os.stat(path)
    sections.append(("File", [
        ("Path", os.path.abspath(path)),
        ("Size", _human_size(stat.st_size)),
        ("Modified", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")),
    ]))

    ckpt = getattr(model, "ckpt", None) or {}
    general = [("Task", str(getattr(model, "task", "-")))]
    for key in ("date", "version", "license", "docs", "epoch", "best_fitness", "updates"):
        if key in ckpt:
            general.append((key, _format_value(ckpt[key])))
    sections.append(("General", general))

    net = model.model
    arch = []
    # model.info(verbose=False) returns None, so compute the same figures directly.
    arch += [("Layers", str(len(list(net.modules())))),
             ("Parameters", f"{get_num_params(net):,}"),
             ("Gradients", f"{get_num_gradients(net):,}")]
    try:
        arch.append(("GFLOPs", f"{get_flops(net, imgsz=640):.1f}"))
    except Exception:
        pass
    stride = getattr(net, "stride", None)
    if stride is not None:
        arch.append(("Stride", _format_value([int(s) for s in stride.tolist()])))
    if getattr(net, "yaml", None):
        arch += [(f"yaml.{k}", _format_value(v)) for k, v in net.yaml.items() if k not in ("backbone", "head")]
    if arch:
        sections.append(("Architecture", arch))

    names = getattr(model, "names", None) or {}
    sections.append((f"Classes ({len(names)})", [(str(i), str(n)) for i, n in names.items()]))

    for title, key in (
        ("Training arguments", "train_args"),
        ("Training metrics", "train_metrics"),
        ("Training results", "train_results"),
        ("Git", "git"),
    ):
        data = ckpt.get(key)
        if isinstance(data, dict) and data:
            sections.append((title, _flatten(data)))

    extra = [(k, _format_value(v)) for k, v in ckpt.items() if k not in _HANDLED_CKPT_KEYS and v is not None]
    if extra:
        sections.append(("Other", extra))

    return sections
