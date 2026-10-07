import platform


def read_model(model_path="/proc/device-tree/model"):
    try:
        with open(model_path, "r") as model_file:
            return model_file.read().replace("\x00", "").strip()
    except OSError:
        return ""


def get_camera_profile(model=None):
    model = (model if model is not None else read_model()).lower()

    if "raspberry pi 5" in model:
        return {"model": model, "resolution": "1920x1080", "fps": 30, "max_fps": 60, "face_recognition": True}
    if "raspberry pi 4" in model:
        return {"model": model, "resolution": "1920x1080", "fps": 30, "max_fps": 60, "face_recognition": True}
    if "zero 2" in model:
        return {"model": model, "resolution": "1536x864", "fps": 15, "max_fps": 30, "face_recognition": False}
    return {"model": model or platform.machine(), "resolution": "1536x864", "fps": 15, "max_fps": 30, "face_recognition": False}