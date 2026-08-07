(function () {
  "use strict";

  var LANGUAGES = ["pl", "en", "es", "ca", "lt", "sk", "cs", "pt"];
  var MACHINES = ["48", "128"];
  var params = new URLSearchParams(window.location.search);
  var requestedLanguage = params.get("lang");
  var requestedMachine = params.get("machine");
  var language = LANGUAGES.indexOf(requestedLanguage) >= 0 ? requestedLanguage : "pl";
  var machine = MACHINES.indexOf(requestedMachine) >= 0 ? requestedMachine : "128";
  var tapePath = "taps/spectrle-" + language + "-" + machine + ".tap";

  var form = document.getElementById("edition-form");
  var languageSelect = document.getElementById("language");
  var machineInput = document.querySelector('input[name="machine"][value="' + machine + '"]');
  var loadButton = form.querySelector(".load-button");
  var buttonLabel = loadButton.querySelector(".button-label");
  var tapeName = document.getElementById("tape-name");
  var releaseName = document.getElementById("release-name");
  var releaseLink = document.getElementById("release-link");
  var emulatorStatus = document.getElementById("emulator-status");
  var downloadTape = document.getElementById("download-tape");

  function setButtonState(state, label) {
    loadButton.dataset.state = state;
    loadButton.setAttribute("aria-busy", state === "loading" ? "true" : "false");
    buttonLabel.textContent = label;
  }

  function setEmulatorState(state, message) {
    emulatorStatus.dataset.state = state;
    emulatorStatus.textContent = message;
  }

  languageSelect.value = language;
  machineInput.checked = true;
  tapeName.textContent = tapePath.split("/").pop();
  downloadTape.href = tapePath;

  form.addEventListener("submit", function () {
    setButtonState("loading", "Loading tape");
    setEmulatorState("loading", "switching edition…");
  });

  fetch("release.json", { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) {
        throw new Error("release metadata unavailable");
      }
      return response.json();
    })
    .then(function (release) {
      releaseName.textContent = release.tagName || "latest";
      if (release.url) {
        releaseLink.href = release.url;
      }
    })
    .catch(function () {
      releaseName.textContent = "latest";
    });

  if (typeof window.JSSpeccy !== "function") {
    setEmulatorState("error", "emulator failed to load");
    setButtonState("error", "Retry load");
    return;
  }

  setButtonState("loading", "Loading tape");
  setEmulatorState("loading", "loading " + machine + "K tape…");

  try {
    var emulator = window.JSSpeccy(document.getElementById("jsspeccy"), {
      machine: Number(machine),
      openUrl: tapePath,
      autoLoadTapes: true,
      zoom: window.matchMedia("(min-width: 60rem)").matches ? 2 : 1
    });

    emulator.onReady(function () {
      setEmulatorState("success", "ready — press Play");
      setButtonState("success", "Tape ready — reload");
    });
  } catch (error) {
    setEmulatorState("error", "emulator failed to start");
    setButtonState("error", "Retry load");
  }
})();
