import os
from tflite_runtime.interpreter import Interpreter
import numpy as np


class Detector:
    classes = ["black", "blue", "media", "noise"]

    def __init__(self):
        self.interpreter = Interpreter(
            model_path=os.path.join(os.path.split(__file__)[0], "detector.tflite")
        )
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_shape = self.input_details[0]["shape"]

    def detect(self, img):
        resized = img.resize(tuple(self.input_shape[1:3]))
        img_data = np.asarray(resized, dtype=np.float32).reshape(self.input_shape)
        self.interpreter.set_tensor(self.input_details[0]["index"], img_data)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]["index"])
        return dict(zip(self.classes, output.flatten()))
