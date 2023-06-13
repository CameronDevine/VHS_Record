// socket = io();
// socket.on("state", (data) => {
//   console.log(data);
// });

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

  // set_state();
});

// function set_state() {
//   let request = new XMLHttpRequest();
//   request.open("GET", "/state");
//   request.send();
//   request.onload = () => {
//     if (request.status != 200) {
//       console.log(request.response);
//     } else {
//       data = JSON.parse(request.response);
//       console.log(data);
//       (new Map(Object.entries(data.settings))).forEach((value, key) => {
//         if (key.endsWith("_enable")) {
//           element = document.getElementById(key);
//           element.checked = value;
//           if (value) {
//             element.parentElement.classList.add("is-checked");
//           } else {
//             element.parentElement.classList.remove("is-checked");
//           }
//           disable_slider(key);
//         } else if (key == "filter_level") {
//           element = document.getElementById(key);
//           if (element.classList.contains("is-upgraded")) {
//             element.MaterialSlider.change(10 * value);
//           } else {
//             console.log("setting listener")
//             element.addEventListener("mdl-componentupgraded", (event) => {
//               event.srcElement.MaterialSlider.change(10 * value);
//             });
//           }
//         } else if (key.endsWith("_level")) {
//           document.getElementById(key).value = 100 * value;
//         }
//       });
//       document.getElementById("filename").value = data.filename;
//     }
//   }
// }

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
  document.getElementById("filename").setAttribute("disabled", "");
}

function stop() {
  post("/stop")
  document.getElementById("stop_button").setAttribute("disabled", "");
  document.getElementById("record_button").removeAttribute("disabled");
  document.getElementById("filename").removeAttribute("disabled");
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
