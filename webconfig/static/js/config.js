// ===================== Header Secondary Actions =====================

const LogPanel = (() => {
    let autoScrollEnabled = false;
    let isLogHidden = true;
    let isEnvHidden = true;

    // Reboot Billy
    const rebootBilly = async () => {
        if (!confirm("Are you sure you want to reboot Billy? This will reboot the whole system.")) return;
        try {
            const res = await fetch('/reboot', {method: 'POST'});
            const data = await res.json();
            if (data.status === "ok") {
                showNotification("Billy is rebooting!", "success");
                setTimeout(() => {
                    location.reload();
                }, 15000);
            }
            else {
                showNotification(data.error || "Reboot failed", "error");
            }
        } catch (err) {
            console.error("Failed to reboot Billy:", err);
            showNotification("Failed to reboot Billy", "error");
        }
    };

    // Shutdown Billy
    const shutdownBilly = async () => {
        if (!confirm("Are you sure you want to shutdown Billy?\n\nThis will power off the Raspberry Pi but one or more of the motors may remain engaged.\n" +
            "To fully power down, make sure to also switch off or unplug the power supply after shutdown.")) return;
        try {
            const res = await fetch('/shutdown', {method: 'POST'});
            const data = await res.json();
            if (data.status === "ok") {
                showNotification("Billy is shutting down!", "success");
                setTimeout(() => {
                    location.reload();
                }, 3000);
            }
            else {
                showNotification(data.error || "Shutdown failed", "error");
            }
        } catch (err) {
            console.error("Failed to shutdown Billy:", err);
            showNotification("Failed to shutdown Billy", "error");
        }
    };

    // Fetch logs and update UI
    const fetchLogs = async () => {
        const res = await fetch("/logs");
        const data = await res.json();
        const logOutput = document.getElementById("log-output");
        const logContainer = document.getElementById("log-container");

        logOutput.textContent = data.logs || "No logs found.";

        if (autoScrollEnabled) {
            requestAnimationFrame(() => {
                logContainer.scrollTop = logContainer.scrollHeight;
            });
        }
    };

    // Toggle log panel visibility
    const toggleLogPanel = () => {
        isLogHidden = !isLogHidden;
        elements.logPanel.classList.toggle("hidden", isLogHidden);
        elements.toggleBtn.classList.toggle("bg-cyan-500", !isLogHidden);
        elements.toggleBtn.classList.toggle("bg-zinc-700", isLogHidden);
    };

    // Toggle .env editor visibility and fetch content if showing
    const toggleEnvPanel = () => {
        isEnvHidden = !isEnvHidden;
        elements.envPanel.classList.toggle("hidden", isEnvHidden);
        elements.toggleEnvBtn.classList.toggle("bg-amber-500", !isEnvHidden);
        elements.toggleEnvBtn.classList.toggle("bg-zinc-700", isEnvHidden);

        if (!isEnvHidden) {
            fetch('/get-env')
                .then(res => res.text())
                .then(text => elements.envTextarea.value = text.trim())
                .catch(() => showNotification("An error occurred while loading .env", "error"));
        }
    };

    const toggleMotion = () => {
        const btn = elements.toggleMotionBtn;
        const icon = btn.querySelector(".material-icons");

        btn.classList.toggle("bg-zinc-700");
        document.documentElement.classList.toggle("reduce-motion");

        const isReduced = document.documentElement.classList.contains("reduce-motion");
        localStorage.setItem("reduceMotion", isReduced ? "1" : "0");

        // Toggle icon
        if (icon) {
            icon.textContent = isReduced ? "blur_off" : "blur_on";
        }
    };

    // Fullscreen toggle
    const toggleFullscreenLog = () => {
        const icon = document.getElementById("fullscreen-icon");
        const isFullscreen = elements.logContainer.classList.toggle("log-fullscreen");
        icon.textContent = isFullscreen ? "fullscreen_exit" : "fullscreen";
    };

    // Toggle auto-scroll to bottom of log
    const toggleAutoScroll = () => {
        autoScrollEnabled = !autoScrollEnabled;
        elements.scrollBtn.classList.toggle("bg-cyan-500", autoScrollEnabled);
        elements.scrollBtn.classList.toggle("bg-zinc-800", !autoScrollEnabled);
        elements.scrollBtn.title = autoScrollEnabled ? "Auto-scroll ON" : "Auto-scroll OFF";

        if (autoScrollEnabled) {
            elements.logOutput.scrollTop = elements.logOutput.scrollHeight;
        }
    };

    // Save .env file and optionally restart service
    const saveEnv = async () => {
        if (!confirm("Are you sure you want to overwrite the .env file? This may affect how Billy runs.")) return;

        try {
            const res = await fetch('/save-env', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: elements.envTextarea.value})
            });
            const data = await res.json();

            if (data.status === "ok") {
                fetch('/restart', {method: 'POST'})
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === "ok") {
                            showNotification(".env saved. Restarting", "success");
                            setTimeout(() => location.reload(), 3000);
                        } else {
                            showNotification(data.error || "Restart failed", "error");
                        }
                    })
                    .catch(err => showNotification(err.message, "error"));
            } else {
                showNotification(data.error || "Unknown error", "error");
            }
        } catch (err) {
            showNotification(err.message, "error");
        }
    };

    // Cache DOM references after DOMContentLoaded
    let elements = {};
    const bindUI = () => {
        elements = {
            logOutput: document.getElementById("log-output"),
            logContainer: document.getElementById("log-container"),
            toggleFullscreenBtn: document.getElementById("toggle-fullscreen-btn"),
            scrollBtn: document.getElementById("scroll-bottom-btn"),
            toggleBtn: document.getElementById("toggle-log-btn"),
            logPanel: document.getElementById("log-panel"),
            toggleEnvBtn: document.getElementById("toggle-env-btn"),
            envPanel: document.getElementById("env-panel"),
            envTextarea: document.getElementById("env-textarea"),
            saveEnvBtn: document.getElementById("save-env-btn"),
            toggleMotionBtn: document.getElementById("toggle-motion-btn"),
            rebootBillyBtn: document.getElementById("reboot-billy-btn"),
            shutdownBillyBtn: document.getElementById("shutdown-billy-btn"),
        };

        elements.toggleBtn.addEventListener("click", toggleLogPanel);
        elements.toggleFullscreenBtn.addEventListener("click", toggleFullscreenLog);
        elements.scrollBtn.addEventListener("click", toggleAutoScroll);
        elements.toggleEnvBtn.addEventListener("click", toggleEnvPanel);
        elements.toggleMotionBtn.addEventListener("click", toggleMotion);
        elements.saveEnvBtn.addEventListener("click", saveEnv);
        elements.rebootBillyBtn.addEventListener("click", rebootBilly);
        elements.shutdownBillyBtn.addEventListener("click", shutdownBilly);

        if (localStorage.getItem("reduceMotion") === "1") {
            document.documentElement.classList.add("reduce-motion");

            const btn = elements.toggleMotionBtn;
            const icon = btn.querySelector(".material-icons");
            btn.classList.remove("bg-zinc-700");

            if (icon) {
                icon.textContent = "blur_off";
            }
        }
    };

    return {fetchLogs, bindUI};
})();

// ===================== SERVICE STATUS =====================

const ServiceStatus = (() => {
    const fetchStatus = async () => {
        const res = await fetch("/service/status");
        const data = await res.json();
        updateServiceStatusUI(data.status);
    };

    const updateServiceStatusUI = (status) => {
        const statusEl = document.getElementById("service-status");
        const controlsEl = document.getElementById("service-controls");
        statusEl.textContent = `(${status})`;
        statusEl.classList.remove("text-emerald-500", "text-amber-500", "text-rose-500");

        if (status === "active") {
            statusEl.classList.add("text-emerald-500");
        } else if (status === "inactive") {
            statusEl.classList.add("text-amber-500");
        } else if (status === "failed") {
            statusEl.classList.add("text-rose-500");
        }

        controlsEl.innerHTML = "";
        const createButton = (label, action, color, iconName) => {
            const btn = document.createElement("button");
            btn.className = `flex items-center gap-1 bg-${color}-500 hover:bg-${color}-400 text-zinc-800 font-semibold py-1 px-2 rounded`;

            const icon = document.createElement("i");
            icon.className = "material-icons";
            icon.textContent = iconName;
            btn.appendChild(icon);

            const labelSpan = document.createElement("span");
            labelSpan.className = "hidden md:inline";
            labelSpan.textContent = label;
            btn.appendChild(labelSpan);

            btn.onclick = () => handleServiceAction(action);
            return btn;
        };
        if (status === "inactive" || status === "failed") {
            controlsEl.appendChild(createButton("Start", "start", "emerald", "play_arrow"));
        } else if (status === "active") {
            controlsEl.appendChild(createButton("Restart", "restart", "amber", "restart_alt"));
            controlsEl.appendChild(createButton("Stop", "stop", "rose", "stop"));
        } else {
            controlsEl.textContent = "Unknown status.";
        }
    };

    const handleServiceAction = async (action) => {
        const statusEl = document.getElementById("service-status");
        const statusMap = {
            restart: {text: "restarting", color: "text-amber-500"},
            stop: {text: "stopping", color: "text-rose-500"},
            start: {text: "starting", color: "text-emerald-500"}
        };

        if (statusMap[action]) {
            const {text, color} = statusMap[action];
            statusEl.textContent = text;
            statusEl.classList.remove("text-emerald-500", "text-amber-500", "text-rose-500");
            statusEl.classList.add(color);
        }
        try {
            await fetch(`/service/${action}`);
        } catch (err) {
            console.error(`Failed to ${action} service:`, err);
        }
        fetchStatus();
        LogPanel.fetchLogs();
    };

    return {fetchStatus, updateServiceStatusUI};
})();

// ===================== SETTINGS FORM =====================

const SettingsForm = (() => {
    const handleSettingsSave = () => {
        document.getElementById("config-form").addEventListener("submit", async function (e) {
            e.preventDefault();

            const resStatus = await fetch("/service/status");
            const {status: wasActive} = await resStatus.json();

            const formData = new FormData(this);
            const payload = Object.fromEntries(formData.entries());

            const wakeEnabledInput = document.getElementById("WAKE_WORD_ENABLED");
            if (wakeEnabledInput) {
                payload["WAKE_WORD_ENABLED"] = wakeEnabledInput.checked ? "true" : "false";
                const engineInput = document.getElementById("WAKE_WORD_ENGINE");
                if (engineInput) {
                    payload["WAKE_WORD_ENGINE"] = engineInput.value || "";
                }
                const sensitivityInput = document.getElementById("WAKE_WORD_SENSITIVITY");
                if (sensitivityInput) {
                    payload["WAKE_WORD_SENSITIVITY"] = sensitivityInput.value || "0.5";
                }
                const thresholdInput = document.getElementById("WAKE_WORD_THRESHOLD");
                if (thresholdInput) {
                    payload["WAKE_WORD_THRESHOLD"] = thresholdInput.value || "0";
                }
                const endpointInput = document.getElementById("WAKE_WORD_ENDPOINT");
                if (endpointInput) {
                    payload["WAKE_WORD_ENDPOINT"] = endpointInput.value || "";
                }
            }

            const flaskPortInput = document.getElementById("FLASK_PORT");
            const oldPort = parseInt(flaskPortInput.getAttribute("data-original")) || 80;
            const newPort = parseInt(payload["FLASK_PORT"] || "80");

            const hostnameInput = document.getElementById("hostname");
            const oldHostname = (hostnameInput.getAttribute("data-original") || hostnameInput.defaultValue || "").trim();
            const newHostname = (formData.get("hostname") || "").trim();

            let hostnameChanged = false;

            // Save config (.env)
            const saveResponse = await fetch("/save", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });
            const saveResult = await saveResponse.json();
            let portChanged = saveResult.port_changed || (oldPort !== newPort);

            // Only update hostname if it actually changed
            if (newHostname && newHostname !== oldHostname) {
                const hostResponse = await fetch("/hostname", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({hostname: newHostname})
                });
                const hostResult = await hostResponse.json();
                if (hostResult.hostname) {
                    hostnameChanged = true;
                    showNotification(`Hostname updated to ${hostResult.hostname}.local`, "success", 5000);
                }
            }

            if (wasActive === "active") {
                await fetch("/service/restart");
                showNotification("Settings saved – Billy restarted", "success");
            } else {
                showNotification("Settings saved", "success");
            }

            if (portChanged || hostnameChanged) {
                const targetHost = hostnameChanged ? `${newHostname}.local` : window.location.hostname;
                const targetPort = portChanged ? newPort : (window.location.port || 80);

                showNotification(`Redirecting to http://${targetHost}:${targetPort}/...`, "warning", 5000);
                setTimeout(() => {
                    window.location.href = `http://${targetHost}:${targetPort}/`;
                }, 3000);
            }
        });
    };

    // Set hostname field from server
    fetch('/hostname')
        .then(res => res.json())
        .then(data => {
            if (data.hostname) {
                const input = document.getElementById('hostname');
                input.value = data.hostname;
                input.setAttribute('data-original', data.hostname);
            }
        });

    // Set original port attribute for change detection
    const flaskPortInput = document.getElementById("FLASK_PORT");
    if (flaskPortInput) {
        flaskPortInput.setAttribute("data-original", flaskPortInput.value);
    }

    return {handleSettingsSave};
})();

// ===================== PERSONA FORM =====================

const PersonaForm = (() => {
    const addBackstoryField = (key = "", value = "") => {
        const wrapper = document.createElement("div");
        wrapper.className = "flex items-center space-x-2";

        const keyInput = Object.assign(document.createElement("input"), {
            type: "text",
            value: key,
            placeholder: "Key",
            className: "w-1/3 p-1 bg-zinc-800 text-white rounded"
        });

        const valInput = Object.assign(document.createElement("input"), {
            type: "text",
            value: value,
            placeholder: "Value",
            className: "flex-1 p-1 bg-zinc-800 text-white rounded"
        });

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "text-rose-500 hover:text-rose-400 cursor-pointer";
        const icon = document.createElement("span");
        icon.className = "material-icons align-middle";
        icon.textContent = "remove_circle_outline";
        removeBtn.appendChild(icon);
        removeBtn.onclick = () => wrapper.remove();

        wrapper.append(keyInput, valInput, removeBtn);
        document.getElementById("backstory-fields").appendChild(wrapper);
    };

    const renderPersonalitySliders = (personality) => {
        const container = document.getElementById("personality-sliders");
        container.innerHTML = "";

        for (const [key, value] of Object.entries(personality)) {
            const wrapper = document.createElement("div");
            wrapper.className = "flex gap-2 space-y-1";

            // Label column
            const label = document.createElement("div");
            label.className = "flex w-36 justify-between items-center text-sm text-slate-300 font-semibold";
            label.innerHTML = `<span>${key}</span>`;

            // Bar container
            const barContainer = document.createElement("div");
            barContainer.className = "relative w-full rounded-full bg-zinc-700 overflow-hidden cursor-pointer";
            barContainer.style.userSelect = "none";

            // Fill bar
            const fillBar = document.createElement("div");
            fillBar.className = "absolute left-0 top-0 h-full bg-emerald-500 transition-all duration-100";
            fillBar.style.width = `${value}%`;
            fillBar.dataset.fillFor = key;

            barContainer.appendChild(fillBar);

            // Output value
            const valueLabel = document.createElement("span");
            valueLabel.id = `${key}-value`;
            valueLabel.className = "text-zinc-400 w-4";
            valueLabel.textContent = value;

            // Drag interaction
            let isDragging = false;

            const updateValue = (e) => {
                const rect = barContainer.getBoundingClientRect();
                const percent = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
                const newVal = Math.round(percent * 100);
                fillBar.style.width = `${newVal}%`;
                valueLabel.textContent = newVal;
                fillBar.setAttribute("data-value", newVal);
            };

            barContainer.addEventListener("mousedown", (e) => {
                isDragging = true;
                updateValue(e);
            });

            document.addEventListener("mousemove", (e) => {
                if (isDragging) updateValue(e);
            });

            document.addEventListener("mouseup", () => {
                isDragging = false;
            });

            wrapper.appendChild(label);
            wrapper.appendChild(barContainer);
            wrapper.appendChild(valueLabel);

            container.appendChild(wrapper);
        }
    };

    function setupSlider(barId, fillId, inputId, min, max) {
        const bar = document.getElementById(barId);
        const fill = document.getElementById(fillId);
        const input = document.getElementById(inputId);

        let isDragging = false;

        const updateUI = (val) => {
            const percent = ((val - min) / (max - min)) * 100;
            fill.style.width = `${percent}%`;
            fill.dataset.value = val;
        };

        const updateFromMouse = (e) => {
            const rect = bar.getBoundingClientRect();
            const percent = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
            const val = Math.round(min + percent * (max - min));
            input.value = val;
            input.dispatchEvent(new Event("input", {bubbles: true}));
            updateUI(val);
        };

        // Allow dragging
        bar.addEventListener("mousedown", (e) => {
            isDragging = true;
            updateFromMouse(e);
        });

        document.addEventListener("mousemove", (e) => {
            if (isDragging) updateFromMouse(e);
        });

        document.addEventListener("mouseup", () => {
            isDragging = false;
        });

        // Sync with input on load/change (just in case)
        input.addEventListener("input", () => updateUI(Number(input.value)));
        updateUI(Number(input.value));
    }

    setupSlider("mic-gain-bar", "mic-gain-fill", "mic-gain", 0, 16);
    setupSlider("speaker-volume-bar", "speaker-volume-fill",  "speaker-volume", 0, 100);

    const renderBackstoryFields = (backstory) => {
        const container = document.getElementById("backstory-fields");
        container.innerHTML = "";
        Object.entries(backstory).forEach(([k, v]) => addBackstoryField(k, v));
    };

    const loadPersona = async () => {
        const res = await fetch("/persona");
        const data = await res.json();
        renderPersonalitySliders(data.PERSONALITY);
        renderBackstoryFields(data.BACKSTORY);
        document.getElementById("meta-text").value = data.META || "";

        await loadWakeupClips();
    };

    const handlePersonaSave = () => {
        document.getElementById("persona-form").addEventListener("submit", async (e) => {
            e.preventDefault();

            const res = await fetch("/service/status");
            const {status: wasActive} = await res.json();

            const personality = {};
            document.querySelectorAll("#personality-sliders div[data-fill-for]").forEach((bar) => {
                const trait = bar.dataset.fillFor;
                personality[trait] = parseInt(bar.style.width);
            });

            const backstory = {};
            document.querySelectorAll("#backstory-fields > div").forEach((row) => {
                const [keyInput, valInput] = row.querySelectorAll("input");
                if (keyInput.value.trim() !== "") {
                    backstory[keyInput.value.trim()] = valInput.value.trim();
                }
            });

            const meta = document.getElementById("meta-text").value.trim();

            const wakeup = {};
            const rows = document.querySelectorAll("#wakeup-sound-list .flex[data-index]");
            let currentIndex = 1;
            rows.forEach((row) => {
                const phrase = row.querySelector("input[type='text']")?.value?.trim();
                if (phrase) {
                    wakeup[currentIndex++] = phrase;
                }
            });

            await fetch("/persona", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({PERSONALITY: personality, BACKSTORY: backstory, META: meta, WAKEUP: wakeup })
            });

            showNotification("Persona saved", "success");

            if (wasActive === "active") {
                await fetch("/service/restart");
                showNotification("Persona saved – service restarted", "success");
                ServiceStatus.fetchStatus();
            }
        });
    };

    return {addBackstoryField, loadPersona, handlePersonaSave};
})();


// ===================== WAKE WORD PANEL =====================

const WakeWordPanel = (() => {
    const EVENT_LIMIT = 50;
    const BADGE_CLASSES = [
        "text-emerald-400",
        "text-amber-300",
        "text-rose-400",
        "text-slate-300",
        "border-emerald-500",
        "border-amber-500",
        "border-rose-500",
        "border-zinc-700",
    ];

    let elements = {};
    let statusTimer = null;
    let eventsTimer = null;
    let programmaticToggle = false;
    const eventHistory = [];
    const calibrationState = {
        ambient: null,
        phrase: null,
        calibrating: false,
    };

    const setEnabledLabel = (enabled) => {
        if (elements.enabledLabel) {
            elements.enabledLabel.textContent = enabled ? "On" : "Off";
        }
    };

    const setToggle = (enabled) => {
        if (!elements.enabledToggle) return;
        programmaticToggle = true;
        elements.enabledToggle.checked = enabled;
        setEnabledLabel(enabled);
        setTimeout(() => {
            programmaticToggle = false;
        }, 0);
    };

    const setBadge = (label, textClass, borderClass) => {
        if (!elements.statusBadge) return;
        elements.statusBadge.textContent = label;
        elements.statusBadge.classList.remove(...BADGE_CLASSES);
        elements.statusBadge.classList.add(textClass, borderClass);
    };

    const describeStatus = (status) => {
        const items = [];
        items.push(status.enabled ? "Enabled" : "Disabled");
        items.push(status.running ? "listener active" : "listener stopped");
        if (status.session_active) {
            items.push("session in progress");
        }
        if (status.engine) {
            items.push(`engine: ${status.engine}`);
        }
        if (status.detector_mode) {
            items.push(`mode: ${status.detector_mode}`);
        }
        return items.join(" • ");
    };

    const updateError = (message) => {
        if (!elements.lastError) return;
        if (message) {
            elements.lastError.textContent = `⚠️ ${message}`;
            elements.lastError.classList.remove("hidden");
        } else {
            elements.lastError.textContent = "";
            elements.lastError.classList.add("hidden");
        }
    };

    const onToggleChange = () => {
        if (programmaticToggle) return;
        const enabled = elements.enabledToggle.checked;
        setEnabledLabel(enabled);
        applyRuntimeConfig({enabled});
    };

    const applyRuntimeConfig = async (changes, options = {}) => {
        if (!changes || Object.keys(changes).length === 0) return;
        try {
            const res = await fetch("/wake-word/runtime-config", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(changes),
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.error || data.reason || "Runtime update failed");
            }
            if (!options.silent) {
                showNotification("Wake word runtime updated", "success", 2000);
            }
            fetchStatus();
        } catch (err) {
            console.error("Wake word runtime update failed:", err);
            showNotification(`Wake word update failed: ${err.message}`, "error");
            fetchStatus();
        }
    };

    const runTestAction = async (action) => {
        try {
            const res = await fetch("/wake-word/test", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({action}),
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.error || "Wake word test failed");
            }
            const statusText = data.status || action;
            showNotification(`Wake word test: ${statusText}`, "info", 2000);
            fetchStatus();
        } catch (err) {
            console.error("Wake word test action failed:", err);
            showNotification(err.message, "error");
        }
    };

    const formatEvent = (event) => {
        const dt = new Date((event.timestamp || 0) * 1000);
        const time = Number.isNaN(dt.getTime()) ? "--:--:--" : dt.toLocaleTimeString();
        const details = [];
        if (typeof event.level === "number") {
            details.push(`lvl=${event.level.toFixed(0)}`);
        }
        if (typeof event.threshold === "number") {
            details.push(`thr=${event.threshold.toFixed(0)}`);
        }
        const payload = event.payload || {};
        if (payload.label) {
            details.push(`label=${payload.label}`);
        }
        if (typeof payload.score === "number") {
            details.push(`score=${payload.score.toFixed(2)}`);
        }
        if (event.kind === "scores" && payload.best_label) {
            details.push(
                `best=${payload.best_label}:${Number(payload.best_score || 0).toFixed(2)}`
            );
        }
        if (event.message) {
            details.push(event.message);
        }
        return `${time} | ${event.kind}${details.length ? " → " + details.join(" ") : ""}`;
    };

    const renderEvents = () => {
        if (!elements.eventsContainer) return;
        if (eventHistory.length === 0) {
            elements.eventsContainer.textContent = "Waiting for events…";
            return;
        }
        elements.eventsContainer.innerHTML = eventHistory
            .slice(-EVENT_LIMIT)
            .map((evt) => `<div>${formatEvent(evt)}</div>`)
            .join("");
    };

    const fetchEvents = async (force = false) => {
        if (!elements.eventsContainer) return;
        try {
            const res = await fetch("/wake-word/events");
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.error || "Failed to load events");
            }
            const newEvents = Array.isArray(data.events) ? data.events : [];
            if (force) {
                eventHistory.length = 0;
            }
            for (const evt of newEvents) {
                eventHistory.push(evt);
                if (eventHistory.length > EVENT_LIMIT) {
                    eventHistory.shift();
                }
            }
            if (newEvents.length > 0 || force) {
                renderEvents();
            }
        } catch (err) {
            console.error("Wake word events fetch failed:", err);
            elements.eventsContainer.textContent = "Failed to fetch events.";
        }
    };

    const setCalStatus = (message) => {
        if (!elements.calStatus) return;
        elements.calStatus.textContent = message;
    };

    const setButtonState = (btn, enabled) => {
        if (!btn) return;
        if (enabled) {
            btn.disabled = false;
            btn.classList.remove("cursor-not-allowed", "bg-cyan-500/30", "text-slate-300", "opacity-60");
            btn.classList.add("bg-cyan-500/80", "hover:bg-cyan-500", "text-zinc-900");
        } else {
            btn.disabled = true;
            btn.classList.add("cursor-not-allowed", "bg-cyan-500/30", "text-slate-300");
            btn.classList.remove("hover:bg-cyan-500", "text-zinc-900", "bg-cyan-500/80");
        }
    };

    const updateCalibrationButtons = () => {
        const busy = calibrationState.calibrating;
        setButtonState(elements.calAmbientBtn, !busy);
        setButtonState(
            elements.calPhraseBtn,
            !busy && !!calibrationState.ambient && calibrationState.ambient.status === "ok"
        );
        if (!calibrationState.ambient || calibrationState.ambient.status !== "ok") {
            setCalStatus("Step 1: Measure background noise to enable the wake phrase recording.");
        }
    };

    const formatValue = (value, decimals = 0) => {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return "–";
        }
        return Number(value).toFixed(decimals);
    };

    const deriveSuggestedThreshold = () => {
        const ambient = calibrationState.ambient?.rms?.recommended_threshold;
        const phrase = calibrationState.phrase?.rms?.recommended_threshold;
        if (phrase && ambient) {
            return Math.round((Number(phrase) + Number(ambient)) / 2);
        }
        return phrase ?? ambient ?? null;
    };

    const deriveSuggestedSensitivity = () => {
        const phrase = calibrationState.phrase?.openwakeword;
        if (!phrase || phrase.available === false) {
            return null;
        }
        if (phrase.recommended_sensitivity !== null && phrase.recommended_sensitivity !== undefined) {
            return Number(Number(phrase.recommended_sensitivity).toFixed(2));
        }
        const bestScore = typeof phrase.best_score === "number" ? phrase.best_score : null;
        const ambientScore = calibrationState.ambient?.openwakeword?.best_score ?? 0.05;
        if (bestScore === null || Number.isNaN(bestScore)) {
            return null;
        }
        const noise = Math.max(0.02, Number(ambientScore) || 0.05);
        const gap = bestScore - noise;
        if (gap <= 0.02) {
            return Number(Math.max(0.25, Math.min(0.6, bestScore - 0.05)).toFixed(2));
        }
        const suggestion = Math.min(bestScore - 0.05, Math.max(noise + gap * 0.4, 0.2));
        return Number(suggestion.toFixed(2));
    };

    const renderCalibrationSummary = () => {
        if (!elements.calAmbientRms) return;

        const ambient = calibrationState.ambient;
        const phrase = calibrationState.phrase;

        elements.calAmbientRms.textContent = formatValue(ambient?.rms?.percentile_90);
        elements.calAmbientPeak.textContent = formatValue(ambient?.rms?.peak);
        elements.calAmbientThreshold.textContent = formatValue(ambient?.rms?.recommended_threshold);

        elements.calPhrasePeak.textContent = formatValue(phrase?.rms?.peak);
        elements.calPhraseScore.textContent = formatValue(phrase?.openwakeword?.best_score, 2);

        const suggestedSensitivity = deriveSuggestedSensitivity();
        elements.calSensitivity.textContent = suggestedSensitivity !== null ? formatValue(suggestedSensitivity, 2) : "–";

        const suggestedThreshold = deriveSuggestedThreshold();
        const applyReady = suggestedThreshold !== null || suggestedSensitivity !== null;

        if (elements.calApplyContainer) {
            elements.calApplyContainer.classList.toggle("hidden", !applyReady);
        }
        if (applyReady) {
            elements.calApplyThreshold.textContent = suggestedThreshold !== null ? formatValue(suggestedThreshold) : "–";
            elements.calApplySensitivity.textContent = suggestedSensitivity !== null ? formatValue(suggestedSensitivity, 2) : "–";
        }

        updateCalibrationButtons();
    };

    const runCalibration = async (mode) => {
        if (calibrationState.calibrating) return;
        if (mode === "phrase" && (!calibrationState.ambient || calibrationState.ambient.status !== "ok")) {
            showNotification("Run the background measurement first.", "warning");
            return;
        }

        calibrationState.calibrating = true;
        updateCalibrationButtons();
        setCalStatus(mode === "ambient" ? "Recording background noise…" : "Recording wake phrase…" );

        const payload = {
            mode,
            duration: mode === "ambient" ? 6.0 : 4.0,
        };

        const modelPath = elements.endpointInput?.value?.trim();
        if (modelPath) {
            payload.model_path = modelPath;
        }

        if (calibrationState.ambient?.rms?.recommended_threshold) {
            payload.base_threshold = calibrationState.ambient.rms.recommended_threshold;
        }

        if (calibrationState.ambient?.openwakeword?.best_score !== undefined) {
            payload.ambient_score = calibrationState.ambient.openwakeword.best_score;
        }

        try {
            const res = await fetch("/wake-word/calibrate", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });

            const data = await res.json();
            if (!res.ok || data.status !== "ok") {
                throw new Error(data.error || data.message || "Calibration failed");
            }

            if (mode === "ambient") {
                calibrationState.ambient = data;
                calibrationState.phrase = null; // reset phrase when re-running ambient
                setCalStatus("Background noise captured. Proceed to Step 2 when you're ready to say the wake phrase.");
            } else {
                calibrationState.phrase = data;
                setCalStatus("Wake phrase recorded. Review the suggestions below.");
            }

            renderCalibrationSummary();
        } catch (err) {
            console.error("Calibration error:", err);
            showNotification(err.message || "Calibration failed", "error");
            setCalStatus("Calibration failed. Please try again.");
        } finally {
            calibrationState.calibrating = false;
            updateCalibrationButtons();
        }
    };

    const applyCalibration = async () => {
        const threshold = deriveSuggestedThreshold();
        const sensitivity = deriveSuggestedSensitivity();

        if (threshold === null && sensitivity === null) {
            showNotification("No calibration suggestions available yet.", "warning");
            return;
        }

        const payload = {
            persist: elements.calPersistCheckbox ? elements.calPersistCheckbox.checked : true,
        };
        if (threshold !== null) payload.threshold = threshold;
        if (sensitivity !== null) payload.sensitivity = sensitivity;

        try {
            const res = await fetch("/wake-word/calibrate/apply", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!res.ok || data.status !== "ok") {
                throw new Error(data.error || "Failed to apply calibration");
            }

            if (threshold !== null && elements.thresholdInput) {
                elements.thresholdInput.value = threshold;
            }
            if (sensitivity !== null && elements.sensitivityInput) {
                elements.sensitivityInput.value = sensitivity.toFixed(2);
            }

            showNotification("Calibration applied", "success");
            fetchStatus();
        } catch (err) {
            console.error("Apply calibration failed:", err);
            showNotification(err.message, "error");
        }
    };

    const fetchStatus = async () => {
        if (!elements.statusBadge) return;
        try {
            const res = await fetch("/wake-word/status");
            const status = await res.json();
            if (!res.ok) {
                throw new Error(status.error || "Failed to fetch status");
            }

            const controllerAvailable = status.controller_available !== false;
            const hardwareEnabled = status.hardware_enabled !== false;
            const enabled = Boolean(status.enabled);
            setToggle(enabled);

            let badgeLabel = "Disabled";
            let badgeColor = {text: "text-slate-300", border: "border-zinc-700"};

            if (!controllerAvailable) {
                badgeLabel = "Unavailable";
                badgeColor = {text: "text-amber-300", border: "border-amber-500"};
            } else if (!hardwareEnabled) {
                badgeLabel = "Remote";
                badgeColor = {text: "text-indigo-300", border: "border-indigo-500"};
            } else if (status.last_error) {
                badgeLabel = "Error";
                badgeColor = {text: "text-rose-400", border: "border-rose-500"};
            } else if (enabled && status.running) {
                badgeLabel = "Listening";
                badgeColor = {text: "text-emerald-400", border: "border-emerald-500"};
            } else if (enabled && !status.running) {
                badgeLabel = status.session_active ? "Paused" : "Idle";
                badgeColor = {text: "text-amber-300", border: "border-amber-500"};
            }

            setBadge(badgeLabel, badgeColor.text, badgeColor.border);
            if (elements.statusDetail) {
                if (!controllerAvailable) {
                    elements.statusDetail.textContent = "Wake word controller is managed by the Billy service. Restart Billy after saving settings.";
                } else if (!hardwareEnabled) {
                    elements.statusDetail.textContent = "Listener runs inside Billy; web UI cannot stream events directly.";
                } else {
                    elements.statusDetail.textContent = describeStatus(status);
                }
            }
            const errorMessages = [];
            if (status.last_error) {
                errorMessages.push(status.last_error);
            }
            if (status.button_controller_available === false) {
                errorMessages.push("Wake word simulated triggers unavailable in this environment.");
            }
            if (status.engine === "openwakeword" && status.oww_available === false) {
                errorMessages.push("Install the 'openwakeword' package to use this engine.");
            }
            if (!controllerAvailable) {
                errorMessages.push("Web UI cannot reach the live wake word controller. Changes will apply after restarting Billy.");
            } else if (!hardwareEnabled) {
                errorMessages.push("Wake word listener is controlled by the Billy service. Use Billy logs to confirm detections.");
            }
            updateError(errorMessages.join(" | "));
        } catch (err) {
            console.error("Wake word status fetch failed:", err);
            setBadge("Offline", "text-rose-400", "border-rose-500");
            if (elements.statusDetail) {
                elements.statusDetail.textContent = "Wake word service unreachable";
            }
            updateError(err.message);
        }
    };

    const bindEvents = () => {
        if (elements.enabledToggle) {
            elements.enabledToggle.addEventListener("change", onToggleChange);
        }
        elements.engineSelect?.addEventListener("change", () => {
            applyRuntimeConfig({engine: elements.engineSelect.value});
        });
        elements.sensitivityInput?.addEventListener("change", () => {
            const value = parseFloat(elements.sensitivityInput.value);
            if (!Number.isNaN(value)) {
                applyRuntimeConfig({sensitivity: value}, {silent: true});
            }
        });
        elements.thresholdInput?.addEventListener("change", () => {
            const value = parseFloat(elements.thresholdInput.value);
            if (!Number.isNaN(value)) {
                applyRuntimeConfig({threshold: value}, {silent: true});
            }
        });
        elements.endpointInput?.addEventListener("blur", () => {
            applyRuntimeConfig({endpoint: elements.endpointInput.value || ""}, {silent: true});
        });
        elements.simulateBtn?.addEventListener("click", () => runTestAction("simulate"));
        elements.stopBtn?.addEventListener("click", () => runTestAction("stop"));
        elements.refreshBtn?.addEventListener("click", () => fetchEvents(true));
        elements.calAmbientBtn?.addEventListener("click", () => runCalibration("ambient"));
        elements.calPhraseBtn?.addEventListener("click", () => runCalibration("phrase"));
        elements.calApplyBtn?.addEventListener("click", applyCalibration);
    };

    const init = () => {
        elements = {
            enabledToggle: document.getElementById("WAKE_WORD_ENABLED"),
            enabledLabel: document.getElementById("wake-word-enabled-label"),
            engineSelect: document.getElementById("WAKE_WORD_ENGINE"),
            sensitivityInput: document.getElementById("WAKE_WORD_SENSITIVITY"),
            thresholdInput: document.getElementById("WAKE_WORD_THRESHOLD"),
            endpointInput: document.getElementById("WAKE_WORD_ENDPOINT"),
            statusBadge: document.getElementById("wake-word-state-badge"),
            statusDetail: document.getElementById("wake-word-status-detail"),
            lastError: document.getElementById("wake-word-last-error"),
            eventsContainer: document.getElementById("wake-word-events"),
            simulateBtn: document.getElementById("wake-word-test-trigger"),
            stopBtn: document.getElementById("wake-word-test-stop"),
            refreshBtn: document.getElementById("wake-word-events-refresh"),
            calAmbientBtn: document.getElementById("wake-word-cal-ambient"),
            calPhraseBtn: document.getElementById("wake-word-cal-phrase"),
            calStatus: document.getElementById("wake-word-cal-status"),
            calAmbientRms: document.getElementById("wake-word-cal-ambient-rms"),
            calAmbientPeak: document.getElementById("wake-word-cal-ambient-peak"),
            calAmbientThreshold: document.getElementById("wake-word-cal-ambient-threshold"),
            calPhrasePeak: document.getElementById("wake-word-cal-phrase-peak"),
            calPhraseScore: document.getElementById("wake-word-cal-phrase-score"),
            calSensitivity: document.getElementById("wake-word-cal-sensitivity"),
            calApplyContainer: document.getElementById("wake-word-cal-apply"),
            calApplyThreshold: document.getElementById("wake-word-cal-apply-threshold"),
            calApplySensitivity: document.getElementById("wake-word-cal-apply-sensitivity"),
            calApplyBtn: document.getElementById("wake-word-cal-apply-btn"),
            calPersistCheckbox: document.getElementById("wake-word-cal-apply-persist"),
        };

        if (!elements.enabledToggle || !elements.statusBadge) {
            return;
        }

        bindEvents();
        updateCalibrationButtons();
        renderCalibrationSummary();
        fetchStatus();
        fetchEvents(true);
        statusTimer = setInterval(fetchStatus, 5000);
        eventsTimer = setInterval(fetchEvents, 3000);
    };

    return {init};
})();


// ===================== WAKEUP CLIPS =====================

async function loadWakeupClips() {
    const container = document.getElementById("wakeup-sound-list");
    container.innerHTML = ""; // clear previous rows

    try {
        const res = await fetch("/wakeup");
        const { clips } = await res.json();

        if (clips.length === 0) {
            const message = document.createElement("div");
            message.className = "text-sm text-zinc-400 italic py-2";
            message.textContent = "No custom wake-up clips added. Using the default sounds.";
            container.appendChild(message);
            return;
        }
        else {
            const label = document.createElement("label");
            label.className = "flex items-center justify-between font-semibold text-sm text-slate-300 mb-1"
            label.innerHtml = `Words or phrases that Billy will randomly say on activation:`;
            container.appendChild(label);
        }

        clips.sort((a, b) => a.index - b.index).forEach(({ index, phrase, has_audio }) => {
            const row = document.createElement("div");
            row.className = "flex items-center space-x-2";
            row.dataset.index = index;

            row.innerHTML = `
                <input type="text" class="text-input w-full rounded bg-zinc-800 border border-zinc-700 px-2 py-1" value="${phrase}">
                <button type="button" class="wakeup-generate-btn text-white hover:text-amber-400" title="Generate .wav">
                    <i class="material-icons align-middle">auto_fix_high</i>
                </button>
                <button type="button" class="wakeup-play-btn text-white hover:text-emerald-400 ${!has_audio ? 'invisible' : ''}" title="Play .wav">
                    <i class="material-icons align-middle">play_arrow</i>
                </button>
                <button type="button" class="remove-wakeup-row text-rose-500 hover:text-rose-400" title="Remove">
                    <i class="material-icons align-middle">remove_circle_outline</i>
                </button>
            `;

            container.appendChild(row);
        });
    } catch (err) {
        console.error("Failed to load wakeup clips:", err);
        showNotification("Failed to load wakeup clips", "error");
    }
}

function addWakeupSound(index = null, phrase = "", hasAudio = false) {
    const container = document.getElementById("wakeup-sound-list");
    const rows = container.querySelectorAll("div[data-index]");
    const usedIndices = Array.from(rows).map(row => parseInt(row.dataset.index));
    const nextIndex = index ?? (usedIndices.length > 0 ? Math.max(...usedIndices) + 1 : 1);

    const row = document.createElement("div");
    row.className = "flex items-center space-x-2";
    row.dataset.index = nextIndex;

    row.innerHTML = `
        <input type="text" class="text-input w-full rounded bg-zinc-800 border border-zinc-700 px-2 py-1" value="${phrase}" placeholder="word or phrase">
        <button type="button" class="wakeup-generate-btn text-white hover:text-amber-400" title="Generate .wav">
            <i class="material-icons align-middle">auto_fix_high</i>
        </button>
        <button type="button" class="wakeup-play-btn text-white hover:text-emerald-400 ${!hasAudio ? 'invisible' : ''}" title="Play .wav">
            <i class="material-icons align-middle">play_arrow</i>
        </button>
        <button type="button" class="remove-wakeup-row text-rose-500 hover:text-rose-400" title="Remove">
            <i class="material-icons align-middle">remove_circle_outline</i>
        </button>
    `;

    container.appendChild(row);
}

document.getElementById("wakeup-sound-list").addEventListener("click", async (e) => {
    const row = e.target.closest(".flex");
    if (!row) return;

    const clipIndex = row.dataset.index;
    const input = row.querySelector("input[type='text']");
    const phrase = input?.value?.trim();

    // === Play button ===
    if (e.target.closest(".wakeup-play-btn")) {
        const clipIndex = e.target.closest("div[data-index]")?.dataset.index;
        if (!clipIndex) return;

        const tryPlay = async () => {
            const res = await fetch("/wakeup/play", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ index: parseInt(clipIndex) }),
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Failed to play audio");

            showNotification(data.status, "success");
        };

        try {
            await tryPlay();
        } catch (err) {
            console.warn("Initial play failed, trying to stop service and retry:", err.message);
            try {
                await fetch("/service/stop");
                await ServiceStatus.fetchStatus();
                await tryPlay(); // retry after stopping
                showNotification("Billy was active. Stopped and retried clip.", "warning");
            } catch (retryErr) {
                console.error("Retry failed:", retryErr);
                showNotification("Play failed after retry: " + retryErr.message, "error");
            }
        }

        return;
    }

    // === Generate button ===
    if (e.target.closest(".wakeup-generate-btn")) {
        const generateBtn = e.target.closest("button");
        generateBtn.disabled = true;
        generateBtn.classList.add("opacity-50");
        generateBtn.querySelector("i").textContent = "hourglass_empty";

        if (!phrase) {
            showNotification("Please enter a phrase", "warning");
            return;
        }

        try {
            const res = await fetch("/wakeup/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: phrase, index: parseInt(clipIndex) }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || "Failed to generate audio");
            }

            const resPersona = await fetch("/persona/wakeup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ index: clipIndex, phrase: phrase }),
            });

            if (!resPersona.ok) {
                const err = await resPersona.json();
                throw new Error(err.error || "Failed to update persona");
            }

            showNotification(`Clip ${clipIndex} generated and saved!`, "success");

            await loadWakeupClips();

        } catch (err) {
            console.error("Generate error:", err);
            showNotification("Generate failed: " + err.message, "error");
        } finally {
            generateBtn.disabled = false;
            generateBtn.classList.remove("opacity-50");
            generateBtn.querySelector("i").textContent = "auto_fix_high";
        }
        return;
    }

    if (e.target.closest(".remove-wakeup-row")) {
        const row = e.target.closest("div[data-index]");
        const clipIndex = row?.dataset.index;

        if (!clipIndex) return;

        if (!confirm("Are you sure you want to delete this wake-up clip?")) return;

        try {
            const res = await fetch("/wakeup/remove", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ index: parseInt(clipIndex) }),
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Failed to remove clip");

            showNotification(`Clip ${clipIndex} removed`, "success");

            await loadWakeupClips();
        } catch (err) {
            console.error("Remove error:", err);
            showNotification("Remove failed: " + err.message, "error");
        }
    }
});

// ===================== UI HELPERS =====================

function showNotification(message, type = "info", duration = 2500) {
    const bar = document.getElementById("notification");
    bar.textContent = message;
    bar.classList.remove("hidden", "opacity-0", "bg-cyan-500/80", "bg-emerald-500/80", "bg-amber-500/80", "bg-rose-500/80");
    const typeClass = {
        info: "bg-cyan-500/80",
        success: "bg-emerald-500/80",
        warning: "bg-amber-500/80",
        error: "bg-rose-500/80",
    }[type] || "bg-cyan-500/80";
    bar.classList.add(typeClass, "opacity-100");
    setTimeout(() => {
        bar.classList.remove("opacity-100");
        bar.classList.add("opacity-0");
        setTimeout(() => bar.classList.add("hidden"), 300);
    }, duration);
}

// Toggle password input visibility
function toggleInputVisibility(inputId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(`${inputId}_icon`);
    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";
    icon.textContent = isHidden ? "visibility_off" : "visibility";
}

function toggleDropdown(btn) {
    // Close all other dropdowns first
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
        // Only close menus not related to this button
        if (!menu.classList.contains('hidden') && !menu.parentElement.contains(btn)) {
            menu.classList.add('hidden');
            const arrow = menu.parentElement.querySelector('.dropdown-toggle .material-icons');
            if (arrow) arrow.classList.remove('rotate-180');
        }
    });

    // Find this button's dropdown menu (assumes menu is sibling or child)
    let dropdown = btn.closest('.relative').querySelector('.dropdown-menu');
    if (!dropdown) return;

    dropdown.classList.toggle('hidden');

    // Toggle arrow rotation
    const arrow = btn.querySelector('.material-icons');
    if (arrow) arrow.classList.toggle('rotate-180');
}

function toggleTooltip(el) {
    el.classList.toggle("text-cyan-400")
    const container = el.closest("label")?.parentElement;
    if (!container) return;

    const tooltip = container.querySelector("[data-tooltip]");
    if (tooltip) {
        const visible = tooltip.getAttribute("data-visible") === "true";
        tooltip.setAttribute("data-visible", visible ? "false" : "true");
    }
}


// Close on click outside
document.addEventListener('click', (e) => {
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
        // If the click is outside the .relative container
        if (!menu.classList.contains('hidden') && !menu.closest('.relative').contains(e.target)) {
            menu.classList.add('hidden');
            const arrow = menu.parentElement.querySelector('.dropdown-toggle .material-icons');
            if (arrow) arrow.classList.remove('rotate-180');
        }
    });
});

// ===================== VERSION & UPDATE =====================

(() => {
    fetch("/version")
        .then(res => res.json())
        .then(data => {
            document.getElementById("current-version").textContent = `${data.current}`;
            if (data.update_available) {
                const latestSpan = document.getElementById("latest-version");
                const updateBtn = document.getElementById("update-btn");
                latestSpan.textContent = `Update to: ${data.latest}`;
                latestSpan.classList.remove("hidden");
                updateBtn.classList.add('flex');
                updateBtn.classList.remove("hidden");
            }
        })
        .catch(err => {
            console.error("Failed to load version info", err);
        });

    document.getElementById("update-btn").addEventListener("click", () => {
        if (!confirm("Are you sure you want to update Billy to the latest version?")) return;
        showNotification("Update started");
        fetch("/update", {method: "POST"})
            .then(res => res.json())
            .then(data => {
                if (data.message) {
                    showNotification(data.message);
                }
                let attempts = 0, maxAttempts = 24;
                const checkForUpdate = async () => {
                    try {
                        const res = await fetch("/version");
                        const data = await res.json();
                        if (data.update_available === false) {
                            showNotification("Update complete. Reloading...", "info");
                            setTimeout(() => location.reload(), 1500);
                            return;
                        }
                    } catch (err) {
                        console.error("Version check failed:", err);
                    }
                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(checkForUpdate, 5000);
                    } else {
                        showNotification("Update timed out after 2 minutes. Reloading");
                        setTimeout(() => location.reload(), 1500);
                    }
                };
                setTimeout(checkForUpdate, 5000);
            })
            .catch(err => {
                console.error("Failed to update:", err);
                showNotification("Failed to update", "error");
            });
    });
})();

// ===================== AUDIO =====================

const AudioPanel = (() => {
    let micCheckSource = null;

    const micCheckBtn = document.getElementById("mic-check-btn");
    micCheckBtn.addEventListener("click", toggleMicCheck);

    document.getElementById("speaker-check-btn").addEventListener("click", async () => {
        try {
            const res = await fetch("/service/status");
            const {status} = await res.json();
            if (status === "active") {
                showNotification("⚠️ Please stop the Billy service before running speaker test.", "warning");
                return;
            }
            await fetch("/speaker-test", {method: "POST"});
            showNotification("Speaker test triggered");
        } catch (err) {
            console.error("Failed to trigger speaker test:", err);
            showNotification("Failed to trigger speaker test", "error");
        }
    });

    async function toggleMicCheck() {
        const btn = micCheckBtn;
        const isActive = btn.classList.contains("bg-emerald-600");
        if (isActive) {
            stopMicCheck();
            btn.classList.remove("bg-emerald-600");
            btn.classList.add("bg-zinc-800");
            showNotification("Mic check stopped");
        } else {
            try {
                const res = await fetch("/service/status");
                const {status} = await res.json();
                if (status === "active") {
                    await fetch("/service/stop");
                    showNotification("Billy was stopped for mic check. You’ll need to start it again afterwards.", "warning");
                }
                startMicCheck();
                btn.classList.remove("bg-zinc-800");
                btn.classList.add("bg-emerald-600");
                if (status !== "active") {
                    showNotification("Mic check started");
                }
            } catch (err) {
                console.error("Failed to toggle mic check:", err);
                showNotification("Mic check failed", "error");
            }
        }
    }

    function stopMicCheck() {
        micCheckSource?.close();
        fetch("/mic-check/stop");
        micCheckSource = null;
        updateMicBar(0);
    }

    function startMicCheck() {
        let maxRms = 0;
        const SCALING_FACTOR = 32768;
        micCheckSource = new EventSource("/mic-check");
        micCheckSource.onmessage = (e) => {
            let data;
            try {
                data = JSON.parse(e.data);
            } catch (err) {
                console.error("Invalid JSON from /mic-check:", e.data);
                return;
            }
            if (data.error) {
                console.error("Mic check error:", data.error);
                return;
            }
            const rms = data.rms * SCALING_FACTOR;
            const threshold = data.threshold;
            maxRms = Math.max(maxRms, rms);
            const percent = Math.min((rms / threshold) * 100, 100);
            const thresholdPercent = Math.min((threshold / SCALING_FACTOR) * 100, 100);
            updateMicBar(percent, thresholdPercent);
        };
        micCheckSource.onerror = () => {
            console.error("Mic check connection error.");
            stopMicCheck();
        };
    }

    function updateMicBar(percentage, thresholdPercent = 0) {
        const bar = document.getElementById("mic-level-bar");
        bar.style.width = `${percentage}%`;
        bar.classList.toggle("bg-zinc-500", percentage < thresholdPercent);
        bar.classList.toggle("bg-emerald-500", percentage < 70);
        bar.classList.toggle("bg-amber-500", percentage >= 70 && percentage < 90);
        bar.classList.toggle("bg-red-500", percentage >= 90);
    }

    // Mic gain UI
    async function loadMicGain() {
        const label = document.getElementById("mic-gain-value");
        const slider = document.getElementById("mic-gain");
        const fill = document.getElementById("mic-gain-fill");

        try {
            const res = await fetch("/mic-gain");
            const data = await res.json();
            if (data.gain !== undefined) {
                slider.value = data.gain;
                label.textContent = data.gain;

                const percent = (data.gain / 16) * 100;
                fill.style.width = `${percent}%`;
                fill.dataset.value = data.gain;
            } else {
                label.textContent = "Unavailable";
            }
        } catch (err) {
            label.textContent = "Error";
        }
    }

    document.getElementById("mic-gain").addEventListener("input", async () => {
        const value = parseInt(document.getElementById("mic-gain").value, 10);
        await fetch("/mic-gain", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({value})
        });
        document.getElementById("mic-gain-value").textContent = value;
    });

    // Silence threshold drag interaction
    let micBar = document.getElementById("mic-bar-container");
    let thresholdLine = document.getElementById("threshold-line");
    let silenceThresholdInput = document.getElementById("SILENCE_THRESHOLD");
    let dragging = false;

    thresholdLine.addEventListener("mousedown", (e) => {
        dragging = true;
        e.preventDefault();
    });

    document.addEventListener("mousemove", (e) => {
        if (!dragging) return;
        const rect = micBar.getBoundingClientRect();
        if (rect.width === 0) return;
        let offsetX = e.clientX - rect.left;
        offsetX = Math.max(0, Math.min(offsetX, rect.width));
        const percent = offsetX / rect.width;
        const scaledThreshold = Math.round(percent * 32768);
        thresholdLine.style.left = `${percent * 100}%`;
        silenceThresholdInput.value = scaledThreshold;
    });

    document.addEventListener("mouseup", () => {
        dragging = false;
    });

    window.addEventListener("load", () => {
        const threshold = parseInt(silenceThresholdInput.value || "1000", 10);
        thresholdLine.style.left = `${(threshold / 32768) * 100}%`;
    });

    // Speaker volume
    const speakerSlider = document.getElementById("speaker-volume");
    fetch("/volume")
        .then(res => res.json())
        .then(data => {
            if (data.volume !== undefined) {
                speakerSlider.value = data.volume;
                const fill = document.getElementById("speaker-volume-fill");
                const percent = (data.volume / 100) * 100;
                fill.style.width = `${percent}%`;
                fill.dataset.value = data.volume;
            }
        });
    let volumeDebounceTimeout;

    speakerSlider.addEventListener("input", () => {
        clearTimeout(volumeDebounceTimeout);
        volumeDebounceTimeout = setTimeout(() => {
            fetch("/volume", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({volume: parseInt(speakerSlider.value)})
            }).catch(err => console.error("Failed to set speaker volume:", err));
        }, 500);
    });

    // Device labels
    async function updateDeviceLabels() {
        try {
            const res = await fetch("/device-info");
            const data = await res.json();
            const updateParentClass = (id, value) => {
                const el = document.getElementById(id);
                if (el && el.parentElement) {
                    el.textContent = value;
                    el.parentElement.classList.add("text-emerald-500");
                }
            };
            updateParentClass("mic-label", data.mic);
            updateParentClass("speaker-label", data.speaker);
        } catch (error) {
            console.error("Failed to fetch device info:", error);
        }
    }

    return {loadMicGain, updateDeviceLabels};
})();

// ===================== MOTOR TEST PANEL =====================

const MotorPanel = (() => {
    function sendMotorTest(motor) {
        fetch("/test-motor", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({motor})
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    showNotification("Motor error: " + data.error, "error", 4000);
                } else {
                    showNotification(`Tested ${motor}`, "success", 1500);
                    if (data.service_was_active) {
                        showNotification(
                            "Billy was stopped for hardware test. Please restart Billy again when done.",
                            "warning",
                            7000
                        );
                        ServiceStatus.fetchStatus();
                    }
                }
            })
            .catch(err => showNotification("Motor test failed: " + err, "error"));
    }

    // Attach events after DOM loaded
    function bindUI() {
        ["mouth", "head", "tail"].forEach(motor => {
            const btn = document.getElementById(`test-${motor}-btn`);
            if (btn) {
                btn.addEventListener("click", function () {
                    sendMotorTest(motor);
                });
            }
        });
    }

    return {bindUI};
})();

// ===================== COLLAPSIBLE SECTIONS =====================

const Sections = (() => {
    function collapsible() {
        document.querySelectorAll('.collapsible-section').forEach(section => {
            const header = section.querySelector('h3');
            if (!header) return;

            // Add icon if not present
            let icon = header.querySelector('.material-icons');
            if (!icon) {
                icon = document.createElement('span');
                icon.className = 'material-icons transition-transform duration-200 ml-2 rotate-0';
                icon.textContent = 'expand_more';
                header.appendChild(icon);
            } else {
                icon.classList.add('transition-transform', 'duration-200', 'ml-2');
                icon.classList.add('rotate-0');
            }

            // Restore state from localStorage
            const id = section.id;
            const collapsed = localStorage.getItem('collapse_' + id) === 'closed';

            icon.classList.toggle('rotate-180', !collapsed);
            icon.classList.toggle('rotate-0', collapsed);
            header.classList.toggle('mb-4', !collapsed);

            [...section.children].forEach(child => {
                if (child !== header) child.classList.toggle('hidden', collapsed);
            });

            // Click to toggle
            header.addEventListener('click', () => {
                const collapsed = section.classList.toggle('collapsed');
                [...section.children].forEach(child => {
                    if (child !== header) child.classList.toggle('hidden', collapsed);
                });
                icon.classList.toggle('rotate-180', !collapsed);
                icon.classList.toggle('rotate-0', collapsed);

                // Toggle mb-4 on h3 only when expanded
                header.classList.toggle('mb-4', !collapsed);

                localStorage.setItem('collapse_' + id, collapsed ? 'closed' : 'open');
            });
        });
    }

    return {collapsible};
})();

// ===================== IMPORT / EXPORT =====================

function exportSettings() {
    fetch('/get-env').then(res => res.text()).then(text => {
        const blob = new Blob([text], {type: "application/octet-stream"});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "billy.env";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
}

function importSettings(input) {
    const file = input.files[0];
    if (!file) return;
    if (!file.name.endsWith('.env')) {
        showNotification("Only .env files are allowed.", "error");
        return;
    }
    const reader = new FileReader();
    reader.onload = function (e) {
        fetch('/save-env', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content: e.target.result})
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === "ok") {
                    showNotification("Settings imported. Restarting...", "success");
                    setTimeout(() => location.reload(), 2000);
                } else {
                    showNotification(data.error || "Failed to import settings.", "error");
                }
            });
    };
    reader.readAsText(file);
}

function exportPersona() {
    const a = document.createElement('a');
    a.href = '/persona/export';
    a.download = 'persona.ini';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function importPersona(input) {
    const file = input.files[0];
    if (!file) return;
    if (!file.name.endsWith('.ini')) {
        showNotification("Only .ini files are allowed.", "error");
        return;
    }
    const formData = new FormData();
    formData.append('file', file);
    fetch('/persona/import', {
        method: 'POST',
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === "ok") {
                showNotification("Persona imported. Restarting...", "success");
                setTimeout(() => location.reload(), 2000);
            } else {
                showNotification(data.error || "Failed to import persona.", "error");
            }
        });
}

// ===================== INITIALIZE =====================

document.addEventListener("DOMContentLoaded", () => {
    LogPanel.bindUI();
    LogPanel.fetchLogs();
    ServiceStatus.fetchStatus();
    setInterval(LogPanel.fetchLogs, 5000);
    setInterval(ServiceStatus.fetchStatus, 10000);
    AudioPanel.updateDeviceLabels();
    PersonaForm.loadPersona();
    AudioPanel.loadMicGain();
    SettingsForm.handleSettingsSave();
    PersonaForm.handlePersonaSave();
    WakeWordPanel.init();
    window.addBackstoryField = PersonaForm.addBackstoryField;
    MotorPanel.bindUI();
    Sections.collapsible();
});
