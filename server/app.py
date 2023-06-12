from flask import Flask
import os
import json
from flask_socketio import SocketIO

app = Flask(__name__, static_url_path="", static_folder="static")

socket = SocketIO(app)

class VHS_Record:
    settings_loc = "/config/settings.json"
    default_settings = dict(
        filter_level=0,
        black_enable=False,
        black_level=0,
        blue_enable=False,
        blue_level=0,
        noise_enable=False,
        noise_level=0,
    )

    def __init__(self):
        self.recording = False
        self.filename = ""
        self.clients = 0
        self.connected = False
        if os.path.isfile(self.settings_loc):
            with open(self.settings_loc) as f:
                self.settings = json.load(f)
        else:
            self.settings = self.default_settings
            settings_dir = os.path.split(self.settings_loc)[0]
            if not os.path.exists(settings_dir):
                os.makedirs(settings_dir)

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
        print("starting")
        self.recording = True
        return {}

    def stop(self):
        print("stopping")
        self.recording = False
        return {}

    def set_enable(self, label=None, enable=None):
        assert label is not None
        assert enable is not None
        self.update_settings(label + "_enable", enable.lower() == "true")
        return {}

    def set_level(self, label=None, level=None):
        assert label is not None
        assert level is not None
        self.update_settings(label + "_level", level / (10 if label == "filter" else 100))
        return {}

    def set_filename(self, filename=None):
        assert filename is not None
        self.filename = filename
        print(self.filename)
        return {}

    def state(self):
        return dict(settings=self.settings, filename=self.filename)


recorder = VHS_Record()

app.add_url_rule("/start", "start", recorder.start, methods=["POST"])
app.add_url_rule("/stop", "stop", recorder.stop, methods=["POST"])
app.add_url_rule("/<label>_enable/<enable>", "enable", recorder.set_enable, methods=["POST"])
app.add_url_rule("/<label>_level/<int:level>", "level", recorder.set_level, methods=["POST"])
app.add_url_rule("/filename/<filename>", "filename", recorder.set_filename, methods=["POST"])
app.add_url_rule("/state", "state", recorder.state, methods=["GET"])

socket.on_event("connect", recorder.connect)
socket.on_event("disconnect", recorder.disconnect)

@app.route('/')
def root():
    return app.send_static_file('index.html')


if __name__ == "__main__":
    socket.run(app, host="0.0.0.0")
