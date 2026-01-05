from utils.logger import get_logger

logger = get_logger("ai_person_detector")

try:
    import tflite_runtime.interpreter as tflite  # or from tensorflow.lite ...
except ImportError:
    tflite = None
    logger.warning("TFLite not available, person detection will be disabled.")


class PersonDetector:
    def __init__(self, model_path: str, enabled: bool = True):
        self.enabled = enabled and tflite is not None
        self.interpreter = None
        if self.enabled:
            self.interpreter = tflite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            logger.info("PersonDetector initialized.")
        else:
            logger.info("PersonDetector disabled or TFLite missing.")

    def is_person_present(self, frame) -> bool:
        if not self.enabled:
            return True  # fallback: treat motion as valid

        # Minimal stub: resize and run model
        import cv2
        import numpy as np

        input_shape = self.input_details[0]["shape"]
        h, w = input_shape[1], input_shape[2]
        resized = cv2.resize(frame, (w, h))
        input_data = resized.astype("float32") / 255.0
        input_data = input_data.reshape(input_shape)

        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]["index"])

        score = float(output[0][0])  # model-dependent
        logger.info(f"Person detection score: {score:.2f}")
        return score > 0.5
