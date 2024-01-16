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
import signal

app = Flask(__name__, static_url_path="", static_folder="static")

socket = SocketIO(app)


class VHS_Record:
    settings_loc = "/config/settings.json"
    default_env_settings = dict(
        INPUT_FMT="v4l2",
        V4L2_FMT="",
        V4L2_RES="",
        V4L2_FPS="",
        V4L2_TIMESTAMPS="default",
        INPUT_PATH="/dev/video0",
        VCODEC="h264",
        ACODEC="aac",
        OUTPUT_RES="640x480",
        CRF="",
        PIX_FMT="",
        VIDEO_THREAD_QUEUE_SIZE="64",
        VIDEO_FILTER="",
        AUDIO_FILTER="",
        ALSA_AUDIO="false",
        AUDIO_THREAD_QUEUE_SIZE="2048",
        AUDIO_DEVICE="1",
        AUDIO_CHANNELS="",
        EXTENSION="mp4",
        FFMPEG_LOG_LEVEL="info",
        SETUP_COMMAND="",
        SETUP_SUCCESS="0",
        SETUP_DELAY="0",
        MIN_LENGTH="30",
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
        self.stderr_thread = None
        self.detector = Detector()
        self.time = 0
        self.log_buffer = []

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
        self.log_buffer = []
        if len(self.env_settings["SETUP_COMMAND"]) > 0:
            setup_command = self.env_settings["SETUP_COMMAND"].split(" ")
            self.log("Running command: " + self.env_settings["SETUP_COMMAND"])
            process = subprocess.run(setup_command, capture_output=True)
            self.log(process.stdout.decode("utf-8"), newline=False)
            self.log(process.stderr.decode("utf-8"), newline=False)
            if process.returncode != int(self.env_settings["SETUP_SUCCESS"]):
                self.log("Setup command returned {}".format(process.returncode))
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
            *(
                ("-r", self.env_settings["V4L2_FPS"])
                if self.env_settings["V4L2_FPS"]
                else []
            ),
            "-f",
            self.env_settings["INPUT_FMT"],
            *(
                ("-input_format", self.env_settings["V4L2_FMT"])
                if self.env_settings["V4L2_FMT"]
                else []
            ),
            *(
                ("-video_size", self.env_settings["V4L2_RES"])
                if self.env_settings["V4L2_RES"]
                else []
            ),
            "-ts",
            self.env_settings["V4L2_TIMESTAMPS"],
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
                    *(
                        ("-channels", self.env_settings["AUDIO_CHANNELS"])
                        if self.env_settings["AUDIO_CHANNELS"]
                        else []
                    ),
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
            + "split=2[in1][in2];[in2]fps=1[out2];"
            + ("[0:a]" if self.env_settings["ALSA_AUDIO"] == "false" else "[1:a]")
            + (
                self.env_settings["AUDIO_FILTER"]
                if self.env_settings["AUDIO_FILTER"]
                else "anull"
            )
            + "[audio]",
            "-map",
            "[in1]",
            "-map",
            "[audio]",
            "-vcodec",
            self.env_settings["VCODEC"],
            *(
                ("-crf", self.env_settings["CRF"])
                if len(self.env_settings["CRF"])
                else []
            ),
            *(
                ("-pix_fmt", self.env_settings["PIX_FMT"])
                if len(self.env_settings["PIX_FMT"])
                else []
            ),
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
        self.log("Running command: " + " ".join(command))
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=False,
        )
        self.recording = True
        self.time = 0
        self.img_thread = threading.Thread(target=self.img_handler, daemon=True)
        self.process_thread = threading.Thread(target=self.process_handler, daemon=True)
        self.stderr_thread = threading.Thread(target=self.stderr_handler, daemon=True)
        self.img_thread.start()
        self.process_thread.start()
        self.stderr_thread.start()
        return {}

    def stop(self):
        if not self.recording:
            return dict(error="Not currently recording"), 409
        self.recording = False
        self.log("Stopping due to button press")
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
            labels=self.labels[:2],
            log=self.log_buffer,
        )

    def img_handler(self):
        img_size = 921600
        while self.recording:
            data = self.process.stdout.read(img_size)
            self.time += 1
            if len(data) != img_size:
                continue
            image = Image.frombytes("RGB", (640, 480), data)
            raw_levels = itemgetter("black", "blue", "noise")(
                self.detector.detect(image)
            )
            if self.time > int(self.env_settings["MIN_LENGTH"]):
                for i in range(len(self.levels)):
                    self.filters[i].timeconstant = self.settings["filter_level"]
                    self.levels[i] = self.filters[i].filter(raw_levels[i])
                    if (
                        self.settings[self.labels[i] + "_enable"]
                        and self.levels[i] > self.settings[self.labels[i] + "_level"]
                    ):
                        self.recording = False
                        self.log("Stopping due to {} level".format(self.labels[i]))
                        break
            if self.clients >= 1:
                img_buffer = BytesIO()
                image.save(img_buffer, format="png")
                img_str = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
                sec = self.time % 60
                min = (self.time - sec) // 60
                socket.emit(
                    "state",
                    dict(
                        img=img_str,
                        recording=self.recording,
                        levels=self.levels[:2],
                        time="{:02d}:{:02d}".format(min, sec),
                    ),
                )

    def process_handler(self):
        while self.recording:
            sleep(0.1)
            if self.process.poll() is not None:
                self.recording = False
        self.log("Starting FFmpeg shutdown sequence")
        if self.process.returncode is None:
            i = 0
            while self.process.poll() is None:
                if i >= 1200 and i % 10 == 0:
                    self.log("Sending SIGKILL to FFmpeg")
                    self.process.send_signal(signal.SIGKILL)
                elif i % 100 == 0 and i < 300:
                    self.log("Sending SIGINT to FFmpeg")
                    self.process.send_signal(signal.SIGINT)
                i += 1
                sleep(0.1)
        self.log("FFmpeg returned {}".format(self.process.returncode))
        try:
            self.img_thread.join(timeout=2)
        except:
            self.log("Image handler thread didn't terminate")
        try:
            self.stderr_thread.join(timeout=2)
        except:
            self.log("Stderr handler thread didn't terminate")
        socket.emit(
            "recording",
            dict(
                recording=False,
            ),
        )

    def stderr_handler(self):
        buffer = b""
        while self.process.poll() is None:
            buffer += self.process.stderr.read(1)
            if buffer.endswith(b"\n"):
                self.log(buffer.decode("utf-8"), newline=False)
                buffer = b""

    def log(self, message, newline=True):
        if newline:
            message += "\n"
        self.log_buffer.append(message)
        socket.emit("log", dict(message=message))


recorder = VHS_Record(app, socket)

if __name__ == "__main__":
    socket.run(app, host="0.0.0.0", allow_unsafe_werkzeug=True)
