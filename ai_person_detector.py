import cv2
import os
import numpy as np
from loguru import logger
import tflite_runtime.interpreter as tflite


class PersonDetector:
    def __init__(self, model_path="models/person_detection.tflite"):
        if not os.path.exists(model_path):
            logger.warning("[AI] Model file missing. Disabling AI features.")
            self.interpreter = None
            self.enabled = False
            return

        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.enabled = True

        input_details = self.interpreter.get_input_details()
        output_details = self.interpreter.get_output_details()
        self.input_index = input_details[0]["index"]
        self.output_index = output_details[0]["index"]
        self.input_shape = input_details[0]["shape"]

    def has_person(self, frame, threshold=0.6):
        if not self.enabled:
            return False

        h, w = self.input_shape[1], self.input_shape[2]
        img = cv2.resize(frame, (w, h))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = np.expand_dims(img, axis=0).astype(np.uint8)

        self.interpreter.set_tensor(self.input_index, img)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_index)

        # Assuming output is [1,1] with probability of person
        prob = float(output.flatten()[0])
        return prob >= threshold
