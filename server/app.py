from flask import Flask, render_template
import os
import json
from flask_socketio import SocketIO
import subprocess
import rtsp
import threading
import base64
from io import BytesIO
from PIL import ImageChops
from detector import Detector
from operator import itemgetter
from cameron.control import Lowpass

app = Flask(__name__, static_url_path="", static_folder="static")

socket = SocketIO(app)


class VHS_Record:
    settings_loc = "/config/settings.json"
    env_settings = dict(
        VCODEC="h264",
        EXTENSION="mp4",
        SAVE_RTP=True,
    )
    default_settings = dict(
        filter_level=0,
        black_enable=False,
        black_level=0,
        blue_enable=False,
        blue_level=0,
        noise_enable=False,
        noise_level=0,
    )
    labels = ["black", "blue", "noise"]

    def __init__(self, app, socket):
        self.recording = False
        self.process = None
        self.filename = ""
        self.clients = 0
        self.rtsp_client = None
        self.thread = None
        self.detector = Detector()

        if os.path.isfile(self.settings_loc):
            with open(self.settings_loc) as f:
                self.settings = json.load(f)
        else:
            self.settings = self.default_settings
            settings_dir = os.path.split(self.settings_loc)[0]
            if not os.path.exists(settings_dir):
                os.makedirs(settings_dir)

        self.levels = len(self.labels) * [0]
        self.filters = [
            Lowpass(self.settings["filter_level"], dt=1) for i in self.levels
        ]

        app.add_url_rule("/start", "start", self.start, methods=["POST"])
        app.add_url_rule("/stop", "stop", self.stop, methods=["POST"])
        app.add_url_rule(
            "/<label>_enable/<enable>", "enable", self.set_enable, methods=["POST"]
        )
        app.add_url_rule(
            "/<label>_level/<int:level>", "level", self.set_level, methods=["POST"]
        )
        app.add_url_rule(
            "/filename/<filename>", "filename", self.set_filename, methods=["POST"]
        )
        app.add_url_rule("/", "root", self.root, methods=["GET"])

        socket.on_event("connect", self.connect)
        socket.on_event("disconnect", self.disconnect)

    def update_settings(self, setting, value):
        self.settings[setting] = value
        with open(self.settings_loc, "w") as f:
            json.dump(self.settings, f)
        print(self.settings)

    def connect(self, *args, **kwargs):
        self.clients += 1

    def disconnect(self, *args, **kwargs):
        self.clients -= 1

    def start(self):
        if self.recording:
            return dict(error="Already recording"), 409
        if len(self.filename) == 0:
            return dict(error="Invalid filename"), 409
        if not self.filename.endswith(self.env_settings["EXTENSION"]):
            self.filename += "." + self.env_settings["EXTENSION"]
        path = os.path.join("/data", self.filename)
        if os.path.exists(path):
            return dict(error="File already exists"), 409
        for filter in self.filters:
            filter.reset()
        self.process = subprocess.Popen(
            [
                "ffmpeg",
                "-re",
                "-f",
                "v4l2",
                "-i",
                "/dev/video",
                "-filter_complex",
                "[0:v]split=2[in1][in2];[in2]fps=1[out2]",
                "-map",
                "[in1]",
                "-vcodec",
                self.env_settings["VCODEC"],
                path,
                "-map",
                "[out2]",
                "-vcodec",
                "mpeg2video",
                "-f",
                "rtp",
                "rtp://127.0.0.1:8888",
            ],
            stdout=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.recording = True
        self.rtsp_client = rtsp.Client(rtsp_server_uri="rtp://127.0.0.1:8888")
        self.thread = threading.Thread(target=self.rtp_handler, daemon=True)
        self.thread.start()
        return {}

    def stop(self):
        if not self.recording:
            return dict(error="Not currently recording"), 409
        self.recording = False
        self.thread.join(timeout=2)
        self.process.terminate()
        self.rtsp_client.close()
        return {}

    def set_enable(self, label=None, enable=None):
        assert label is not None
        assert enable is not None
        self.update_settings(label + "_enable", enable.lower() == "true")
        return {}

    def set_level(self, label=None, level=None):
        assert label is not None
        assert level is not None
        self.update_settings(
            label + "_level", level / (10 if label == "filter" else 100)
        )
        return {}

    def set_filename(self, filename=None):
        assert filename is not None
        self.filename = filename
        print(self.filename)
        return {}

    def root(self):
        return render_template(
            "index.html",
            settings=self.settings,
            filename=self.filename,
            labels=self.labels,
        )

    def rtp_handler(self):
        last_image = None
        index = 0
        while self.recording:
            image = self.rtsp_client.read()
            if image is not None:
                if (
                    last_image is None
                    or ImageChops.difference(image, last_image).getbbox()
                ):
                    raw_levels = itemgetter("black", "blue", "noise")(
                        self.detector.detect(image)
                    )
                    for i in range(len(self.levels)):
                        self.filters[i].timeconstant = self.settings["filter_level"]
                        self.levels[i] = self.filters[i].filter(raw_levels[i])
                        if (
                            self.settings[self.labels[i] + "_enable"]
                            and self.levels[i]
                            > self.settings[self.labels[i] + "_level"]
                        ):
                            self.recording = False
                            self.process.terminate()
                            self.rtsp_client.close()
                    if self.clients >= 1:
                        img_buffer = BytesIO()
                        image.save(img_buffer, format="png")
                        img_str = base64.b64encode(img_buffer.getvalue()).decode(
                            "utf-8"
                        )
                        socket.emit(
                            "state",
                            dict(
                                img=img_str,
                                recording=self.recording,
                                levels=self.levels,
                            ),
                        )
                    if self.env_settings["SAVE_RTP"]:
                        filename = os.path.join(
                            "/data",
                            self.filename.split(".")[0],
                            "frame{:05d}.png".format(index),
                        )
                        if index == 0:
                            os.makedirs(os.path.split(filename)[0])
                        image.save(filename)
                        index += 1
                    last_image = image


recorder = VHS_Record(app, socket)


if __name__ == "__main__":
    socket.run(app, host="0.0.0.0")
