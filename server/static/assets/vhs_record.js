socket = io();
socket.on("state", (data) => {
  document.getElementById("monitor").src = "data:image/png;charset=utf-8;base64," + data.img;
  set_recording(data.recording);
  if (document.getElementById("black_enable").checked) {
    set_level(document.getElementById("black_level"), data.levels[0]);
  }
  if (document.getElementById("blue_enable").checked) {
    set_level(document.getElementById("blue_level"), data.levels[1]);
  }
  // if (document.getElementById("noise_enable").checked) {
  //   set_level(document.getElementById("noise_level"), data.levels[2]);
  // }
  document.getElementById("time").innerText = data.time;
});
socket.on("recording", (data) => {
  set_recording(data.recording);
  snackbar("Recording stopped");
});
socket.on("log", (data) => {
  document.getElementById("log").innerText += data.message;
});

window.addEventListener("load", (event) => {
  document.getElementById("filename").addEventListener("focusout", filename);
  document.getElementById("record_button").addEventListener("click", start);
  document.getElementById("stop_button").addEventListener("click", stop);
  document.getElementById("black_enable").addEventListener("click", enable_switch);
  document.getElementById("blue_enable").addEventListener("click", enable_switch);
  //document.getElementById("noise_enable").addEventListener("click", enable_switch);
  document.getElementById("filter_level").addEventListener("change", level_slider);
  document.getElementById("black_level").addEventListener("change", level_slider);
  document.getElementById("blue_level").addEventListener("change", level_slider);
  //document.getElementById("noise_level").addEventListener("change", level_slider);

  document.getElementById("black_level").addEventListener("mdl-componentupgraded", (event) => format_slider(event.srcElement));
  document.getElementById("blue_level").addEventListener("mdl-componentupgraded", (event) => format_slider(event.srcElement));
  //document.getElementById("noise_level").addEventListener("mdl-componentupgraded", (event) => format_slider(event.srcElement));

  element = document.getElementById("black_level");
  if ("MaterialSlider" in element) {
    format_slider(element);
  }
  element = document.getElementById("blue_level");
  if ("MaterialSlider" in element) {
    format_slider(element)
  }
  // element = document.getElementById("noise_level");
  // if ("MaterialSlider" in element) {
  //   format_slider(event);
  // }
});

function post(url) {
  let request = new XMLHttpRequest();
  request.open("POST", url);
  request.send();
  request.onload = () => {
    if (request.status != 200) {
      try {
        data = JSON.parse(request.response);
      } catch (error) {
        data = {error: "Error"};
      }
      if ("error" in data) {
        snackbar(data.error);
      }
      return false;
    }
  }
  return true;
}

function snackbar(message) {
  document.getElementById("notification").MaterialSnackbar.showSnackbar({
    message: message,
  });
}

function start() {
  document.getElementById("log").innerText = "";
  set_recording(post("/start"));
}

function stop() {
  set_recording(!post("/stop"));
}

function set_recording(recording) {
  if (recording) {
    document.getElementById("record_button").setAttribute("disabled", "");
    document.getElementById("stop_button").removeAttribute("disabled");
    document.getElementById("filename").setAttribute("disabled", "");
  } else {
    document.getElementById("stop_button").setAttribute("disabled", "");
    document.getElementById("record_button").removeAttribute("disabled");
    document.getElementById("filename").removeAttribute("disabled");
  }
}

function enable_switch(event) {
  post("/" + event.srcElement.id + "/" + event.srcElement.checked);
  disable_slider(event.srcElement.id);
}

function disable_slider(switch_id) {
  slider = document.getElementById(switch_id.split("_")[0] + "_level");
  if (document.getElementById(switch_id).checked) {
    slider.removeAttribute("disabled");
  } else {
    slider.setAttribute("disabled", "");
  }
}

function level_slider(event) {
  post("/" + event.srcElement.id + "/" + event.srcElement.value);
}

function filename() {
  post("/filename/" + document.getElementById("filename").value);
}

function format_slider(element) {
  element.MaterialSlider.updateValueStyles_ = () => null;
  element.classList.remove("is-lowest-value");
  set_level(element, 0);
}

function set_level(element, value) {
  element.parentElement.getElementsByClassName("mdl-slider__background-lower")[0].style.flexGrow = value;
  element.parentElement.getElementsByClassName("mdl-slider__background-upper")[0].style.flexGrow = 1 - value;
}
