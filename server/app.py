from flask import Flask, render_template
import os
import json
from flask_socketio import SocketIO
import subprocess
import rtsp
import threading

app = Flask(__name__, static_url_path="", static_folder="static")

socket = SocketIO(app)


class VHS_Record:
    settings_loc = "/config/settings.json"
    ffmpeg_settings = dict(
        vcodec="h264",
        extension="mp4",
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

    def __init__(self, app, socket):
        self.recording = False
        self.process = None
        self.filename = ""
        self.clients = 0
        self.connected = False
        self.rtsp_client = None
        self.thread = threading.Thread(target=self.rtp_handler, daemon=True)
        if os.path.isfile(self.settings_loc):
            with open(self.settings_loc) as f:
                self.settings = json.load(f)
        else:
            self.settings = self.default_settings
            settings_dir = os.path.split(self.settings_loc)[0]
            if not os.path.exists(settings_dir):
                os.makedirs(settings_dir)

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
        if self.clients > 0:
            self.connected = True

    def disconnect(self, *args, **kwargs):
        self.clients -= 1
        if self.clients < 1:
            self.connected = False

    def start(self):
        if len(self.filename) == 0:
            return dict(error="Invalid Filename"), 409
        if not self.filename.endswith(self.ffmpeg_settings["extension"]):
            self.filename += "." + self.ffmpeg_settings["extension"]
        print("starting")
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
                self.ffmpeg_settings["vcodec"],
                self.filename,
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
        self.thread.start()
        return {}

    def stop(self):
        print("stopping")
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
            "index.html", settings=self.settings, filename=self.filename
        )

    def rtp_handler(self):
        while self.recording:
            data = self.rtsp_client.read()
            if data is not None:
                print("got image")


recorder = VHS_Record(app, socket)


if __name__ == "__main__":
    socket.run(app, host="0.0.0.0")
