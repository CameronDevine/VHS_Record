socket = io();//.connect(window.location.href);
socket.on("state", (data) => {
  console.log(data);
  (new Map(Object.entries(data.settings))).forEach((value, key) => {
    if (key.endsWith("_enable")) {
      element = document.getElementById(key);
      console.log(element.checked, value)
      if (element.checked != value) {
        element.click();
      }
    } else if (key == "filter_level") {
      element = document.getElementById(key);
      if (element.classList.contains("is-upgraded")) {
        element.MaterialSlider.change(10 * value);
      } else {
        console.log("setting listener")
        element.addEventListener("mdl-componentupgraded", (event) => {
          event.srcElement.MaterialSlider.change(10 * value);
        });
      }
    } else if (key.endsWith("_level")) {
      document.getElementById(key).value = 100 * value;
    }
  })
});

window.addEventListener("load", (event) => {
  document.getElementById("filename").addEventListener("focusout", filename);
  document.getElementById("record_button").addEventListener("click", start);
  document.getElementById("stop_button").addEventListener("click", stop);
  document.getElementById("black_enable").addEventListener("click", enable_switch);
  document.getElementById("blue_enable").addEventListener("click", enable_switch);
  document.getElementById("noise_enable").addEventListener("click", enable_switch);
  document.getElementById("filter_level").addEventListener("change", level_slider);
  document.getElementById("black_level").addEventListener("change", level_slider);
  document.getElementById("blue_level").addEventListener("change", level_slider);
  document.getElementById("noise_level").addEventListener("change", level_slider);

  document.getElementById("black_level").addEventListener("mdl-componentupgraded", (event) => format_slider(event.srcElement));
  document.getElementById("blue_level").addEventListener("mdl-componentupgraded", (event) => format_slider(event.srcElement));
  document.getElementById("noise_level").addEventListener("mdl-componentupgraded", (event) => format_slider(event.srcElement));

  element = document.getElementById("black_level");
  if ("MaterialSlider" in element) {
    format_slider(element);
  }
  element = document.getElementById("blue_level");
  if ("MaterialSlider" in element) {
    format_slider(element)
  }
  element = document.getElementById("noise_level");
  if ("MaterialSlider" in element) {
    format_slider(event);
  }
});

function post(url) {
  let request = new XMLHttpRequest();
  request.open("POST", url);
  request.send();
  request.onload = () => {
    if (request.status != 200) {
      console.log(request.response);
    }
  }
}

function start() {
  post("/start");
  document.getElementById("record_button").setAttribute("disabled", "");
  document.getElementById("stop_button").removeAttribute("disabled");
}

function stop() {
  post("/stop")
  document.getElementById("stop_button").setAttribute("disabled", "");
  document.getElementById("record_button").removeAttribute("disabled");
}

function enable_switch(event) {
  post("/" + event.srcElement.id + "/" + event.srcElement.checked);
  slider = document.getElementById(event.srcElement.id.split("_")[0] + "_level");
  if (event.srcElement.checked) {
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
}

function set_switch(id, state) {

}
