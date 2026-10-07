import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from hardware_profile import get_camera_profile, read_model
from face_recognition_whitelist import FaceWhitelist
from utils.config_manager import _get_default_config


class HardwareProfileTests(unittest.TestCase):
    def test_profiles_match_supported_raspberry_pi_models(self):
        expected = {
            "Raspberry Pi Zero 2 W Rev 1.0": ("1536x864", 15, 30),
            "Raspberry Pi 4 Model B Rev 1.5": ("1920x1080", 30, 60),
            "Raspberry Pi 5 Model B Rev 1.0": ("1920x1080", 30, 60),
        }

        for model, values in expected.items():
            with self.subTest(model=model):
                profile = get_camera_profile(model)
                self.assertEqual(
                    (profile["resolution"], profile["fps"], profile["max_fps"]),
                    values,
                )
                self.assertEqual(profile["face_recognition"], "Pi 4" in model or "Pi 5" in model)

    def test_read_model_removes_device_tree_null_terminator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = f"{temp_dir}/model"
            with open(model_path, "w", encoding="utf-8") as model_file:
                model_file.write("Raspberry Pi 5 Model B Rev 1.0\x00")
            self.assertEqual(read_model(model_path), "Raspberry Pi 5 Model B Rev 1.0")

    def test_camera_config_defaults_follow_detected_hardware(self):
        profile = {"resolution": "1920x1080", "fps": 30, "face_recognition": True}
        with patch("utils.config_manager.get_camera_profile", return_value=profile):
            defaults = _get_default_config()
        self.assertEqual(defaults["stream_resolution"], "1920x1080")
        self.assertEqual(defaults["stream_fps"], 30)

    def test_face_whitelist_returns_name_for_matching_face(self):
        class FakeFaceRecognition:
            @staticmethod
            def load_image_file(path):
                return path

            @staticmethod
            def face_encodings(image, locations=None):
                return ["known"] if isinstance(image, str) else ["match"]

            @staticmethod
            def face_locations(image, model="hog"):
                return [(0, 1, 1, 0)]

            @staticmethod
            def face_distance(known_encodings, encoding):
                return np.array([0.1])

        with tempfile.TemporaryDirectory() as temp_dir:
            with open(f"{temp_dir}/front_door.jpg", "wb") as image_file:
                image_file.write(b"test")
            with patch("face_recognition_whitelist.face_recognition", FakeFaceRecognition):
                whitelist = FaceWhitelist(temp_dir, enabled=True)
                fake_cv2 = SimpleNamespace(COLOR_BGR2RGB=0, cvtColor=lambda frame, color: frame)
                with patch.dict("sys.modules", {"cv2": fake_cv2}):
                    self.assertEqual(whitelist.recognize(np.zeros((2, 2, 3))), ["front_door"])


if __name__ == "__main__":
    unittest.main()