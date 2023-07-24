from flask import Flask, render_template
import os
import json
from flask_socketio import SocketIO
import subprocess
import threading
import base64
from io import BytesIO
from detector import Detector
from operator import itemgetter
from cameron.control import Lowpass
from PIL import Image
from time import sleep

app = Flask(__name__, static_url_path="", static_folder="static")

socket = SocketIO(app)


class VHS_Record:
    settings_loc = "/config/settings.json"
    default_env_settings = dict(
        INPUT_FMT="v4l2",
        INPUT_PATH="/dev/video0",
        VCODEC="h264",
        ACODEC="aac",
        OUTPUT_RES="640x480",
        VIDEO_THREAD_QUEUE_SIZE="64",
        VIDEO_FILTER="",
        ALSA_AUDIO="false",
        AUDIO_THREAD_QUEUE_SIZE="2048",
        AUDIO_DEVICE="1",
        EXTENSION="mp4",
        FFMPEG_LOG_LEVEL="info",
        SETUP_COMMAND="",
        SETUP_SUCCESS="0",
        SETUP_DELAY="0",
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
        self.img_thread = None
        self.process_thread = None
        self.detector = Detector()

        if os.path.isfile(self.settings_loc):
            with open(self.settings_loc) as f:
                self.settings = json.load(f)
        else:
            self.settings = self.default_settings
            settings_dir = os.path.split(self.settings_loc)[0]
            if not os.path.exists(settings_dir):
                os.makedirs(settings_dir)

        self.env_settings = dict()
        for var, default in self.default_env_settings.items():
            self.env_settings[var] = os.environ.get(var, default)

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
        if len(self.env_settings["SETUP_COMMAND"]) > 0:
            setup_command = self.env_settings["SETUP_COMMAND"].split(" ")
            print(setup_command)
            process = subprocess.run(setup_command)
            if process.returncode != int(self.env_settings["SETUP_SUCCESS"]):
                return dict(error="Setup command failed"), 409
            sleep(float(self.env_settings["SETUP_DELAY"]))
        command = [
            "ffmpeg",
            "-loglevel",
            self.env_settings["FFMPEG_LOG_LEVEL"],
            "-nostats",
            "-re",
            "-thread_queue_size",
            self.env_settings["VIDEO_THREAD_QUEUE_SIZE"],
            "-f",
            self.env_settings["INPUT_FMT"],
            "-i",
            self.env_settings["INPUT_PATH"],
            *(
                []
                if self.env_settings["ALSA_AUDIO"] == "false"
                else (
                    "-thread_queue_size",
                    self.env_settings["AUDIO_THREAD_QUEUE_SIZE"],
                    "-f",
                    "alsa",
                    "-i",
                    "hw:" + self.env_settings["AUDIO_DEVICE"],
                )
            ),
            "-filter_complex",
            "[0:v]"
            + (
                self.env_settings["VIDEO_FILTER"] + ","
                if len(self.env_settings["VIDEO_FILTER"])
                else ""
            )
            + "split=2[in1][in2];[in2]fps=1[out2]",
            "-map",
            "[in1]",
            "-map",
            "0:a" if self.env_settings["ALSA_AUDIO"] == "false" else "1:a",
            "-vcodec",
            self.env_settings["VCODEC"],
            "-acodec",
            self.env_settings["ACODEC"],
            "-s",
            self.env_settings["OUTPUT_RES"],
            path,
            "-map",
            "[out2]",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            "640x480",
            "-f",
            "image2pipe",
            "-",
        ]
        print(" ".join(command))
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=False,
        )
        self.recording = True
        self.img_thread = threading.Thread(target=self.img_handler, daemon=True)
        self.process_thread = threading.Thread(target=self.process_handler, daemon=True)
        self.img_thread.start()
        self.process_thread.start()
        return {}

    def stop(self):
        if not self.recording:
            return dict(error="Not currently recording"), 409
        self.recording = False
        try:
            self.img_thread.join(timeout=2)
            self.process_thread.join(timeout=2)
        except:
            pass
        self.process.terminate()
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
        return {}

    def root(self):
        return render_template(
            "index.html",
            settings=self.settings,
            filename=self.filename,
            labels=self.labels,
        )

    def img_handler(self):
        img_size = 921600
        while self.recording:
            data = self.process.stdout.read(img_size)
            if len(data) != img_size:
                continue
            image = Image.frombytes("RGB", (640, 480), data)
            raw_levels = itemgetter("black", "blue", "noise")(
                self.detector.detect(image)
            )
            for i in range(len(self.levels)):
                self.filters[i].timeconstant = self.settings["filter_level"]
                self.levels[i] = self.filters[i].filter(raw_levels[i])
                if (
                    self.settings[self.labels[i] + "_enable"]
                    and self.levels[i] > self.settings[self.labels[i] + "_level"]
                ):
                    self.recording = False
                    self.process.terminate()
                    break
            if self.clients >= 1:
                img_buffer = BytesIO()
                image.save(img_buffer, format="png")
                img_str = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
                socket.emit(
                    "state",
                    dict(
                        img=img_str,
                        recording=self.recording,
                        levels=self.levels,
                    ),
                )

    def process_handler(self):
        while self.recording:
            self.recording = self.process.poll() == None
        socket.emit(
            "recording",
            dict(
                recording=False,
            ),
        )


recorder = VHS_Record(app, socket)


if __name__ == "__main__":
    socket.run(app, host="0.0.0.0", allow_unsafe_werkzeug=True)
