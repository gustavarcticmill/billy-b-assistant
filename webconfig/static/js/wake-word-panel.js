// ===================== WAKE WORD PANEL =====================
const WakeWordPanel = (() => {
    // Private state
    let statusInterval = null;
    let eventInterval = null;
    let stopArmed = false;
    let stopTimer = null;
    let calState = { ambient: null, phrase: null, suggested: null };

    const CAL_ADVANCE_DELAY = 1500;

    // Badge color map keyed by state
    const badgeStyles = {
        listening:   { bg: "bg-emerald-500/20", text: "text-emerald-400", dot: "bg-emerald-400", pulse: true },
        disabled:    { bg: "bg-zinc-600/20",    text: "text-zinc-400",    dot: "bg-zinc-400",    pulse: false },
        paused:      { bg: "bg-amber-500/20",   text: "text-amber-400",  dot: "bg-amber-400",   pulse: false },
        error:       { bg: "bg-rose-500/20",    text: "text-rose-400",   dot: "bg-rose-400",    pulse: false },
        unavailable: { bg: "bg-zinc-600/20",    text: "text-zinc-500",   dot: "bg-zinc-500",    pulse: false },
    };

    // Event type icon mapping
    const eventIcons = {
        detection: { icon: "mic",                 color: "text-emerald-400" },
        error:     { icon: "error_outline",       color: "text-rose-400" },
        started:   { icon: "power_settings_new",  color: "text-amber-400" },
        stopped:   { icon: "power_settings_new",  color: "text-amber-400" },
    };
    const defaultEventIcon = { icon: "info", color: "text-slate-400" };

    // === Public init ===

    function init() {
        const simulateBtn = document.getElementById("ww-simulate-btn");
        const stopBtn = document.getElementById("ww-stop-btn");
        const refreshBtn = document.getElementById("ww-refresh-btn");
        const enableToggle = document.getElementById("ww-enable-toggle");
        const ambientBtn = document.getElementById("ww-cal-ambient-btn");
        const phraseBtn = document.getElementById("ww-cal-phrase-btn");
        const applyBtn = document.getElementById("ww-cal-apply-btn");

        if (simulateBtn) simulateBtn.addEventListener("click", handleSimulate);
        if (stopBtn) stopBtn.addEventListener("click", handleStop);
        if (refreshBtn) refreshBtn.addEventListener("click", handleRefresh);
        if (enableToggle) enableToggle.addEventListener("change", handleToggle);
        if (ambientBtn) ambientBtn.addEventListener("click", handleCalAmbient);
        if (phraseBtn) phraseBtn.addEventListener("click", handleCalPhrase);
        if (applyBtn) applyBtn.addEventListener("click", handleCalApply);

        // Start polling -- runs continuously, never paused on collapse
        pollStatus();
        statusInterval = setInterval(pollStatus, 3000);
        eventInterval = setInterval(pollEvents, 2000);
    }

    // === Status polling ===

    async function pollStatus() {
        try {
            const res = await fetch("/wake-word/status");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            updateStatusBadge(data);
            // Sync enable toggle
            const toggle = document.getElementById("ww-enable-toggle");
            if (toggle) toggle.checked = data.enabled;
        } catch (err) {
            updateStatusBadge(null);
        }
    }

    function deriveState(data) {
        if (!data) return "unavailable";
        if (data.error) return "error";
        if (data.enabled === false) return "disabled";
        if (data.running === false && data.enabled === true) return "unavailable";
        if (data.running === true) return "listening";
        return "unavailable";
    }

    function updateStatusBadge(data) {
        const badge = document.getElementById("ww-status-badge");
        const dot = document.getElementById("ww-status-dot");
        const text = document.getElementById("ww-status-text");
        if (!badge || !dot || !text) return;

        const state = deriveState(data);
        const style = badgeStyles[state] || badgeStyles.unavailable;

        badge.className = `flex items-center gap-2 px-3 py-1.5 rounded-full ${style.bg}`;
        dot.className = `w-2 h-2 rounded-full ${style.dot}${style.pulse ? " animate-pulse" : ""}`;
        text.className = `text-xs font-semibold ${style.text}`;
        text.textContent = state.charAt(0).toUpperCase() + state.slice(1);
    }

    // === Enable/Disable toggle ===

    async function handleToggle() {
        const toggle = document.getElementById("ww-enable-toggle");
        const checked = toggle.checked;
        try {
            const res = await fetch("/wake-word/runtime-config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ enabled: checked }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            showNotification(
                checked ? "Wake word detection enabled" : "Wake word detection disabled",
                checked ? "success" : "info"
            );
        } catch (err) {
            // Revert checkbox on error
            toggle.checked = !checked;
            showNotification("Failed to update wake word: " + err.message, "error");
        }
    }

    // === Action buttons ===

    async function handleSimulate() {
        try {
            const res = await fetch("/wake-word/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "simulate" }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            showNotification("Detection simulated", "success");
        } catch (err) {
            showNotification("Simulation failed: " + err.message, "error");
        }
    }

    function handleStop() {
        const btn = document.getElementById("ww-stop-btn");
        if (!btn) return;

        if (!stopArmed) {
            // First click: arm the button
            stopArmed = true;
            btn.innerHTML = '<span class="material-icons text-base">stop</span> Hold to Stop';
            btn.classList.remove("bg-zinc-800", "hover:bg-zinc-700", "text-white");
            btn.classList.add("bg-rose-500/20", "text-rose-400");
            stopTimer = setTimeout(() => {
                resetStopButton();
            }, 2000);
        } else {
            // Second click: execute stop
            clearTimeout(stopTimer);
            resetStopButton();
            executeStop();
        }
    }

    function resetStopButton() {
        stopArmed = false;
        const btn = document.getElementById("ww-stop-btn");
        if (!btn) return;
        btn.innerHTML = '<span class="material-icons text-base">stop</span> Stop Session';
        btn.classList.remove("bg-rose-500/20", "text-rose-400");
        btn.classList.add("bg-zinc-800", "hover:bg-zinc-700", "text-white");
    }

    async function executeStop() {
        try {
            const res = await fetch("/wake-word/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "stop" }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            showNotification("Session stopped", "info");
        } catch (err) {
            showNotification("Stop failed: " + err.message, "error");
        }
    }

    async function handleRefresh() {
        try {
            const res = await fetch("/wake-word/status");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            updateStatusBadge(data);
            const toggle = document.getElementById("ww-enable-toggle");
            if (toggle) toggle.checked = data.enabled;
            showNotification("Status refreshed", "info");
        } catch (err) {
            updateStatusBadge(null);
            showNotification("Refresh failed: " + err.message, "error");
        }
    }

    // === Event log ===

    async function pollEvents() {
        try {
            const res = await fetch("/wake-word/events");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            if (!data.events || data.events.length === 0) return;

            const log = document.getElementById("ww-event-log");
            const emptyDiv = document.getElementById("ww-event-empty");
            const countEl = document.getElementById("ww-event-count");
            if (!log) return;

            // Hide empty state
            if (emptyDiv) emptyDiv.classList.add("hidden");

            // Check auto-scroll before prepending
            const wasAtTop = log.scrollTop === 0;

            // Prepend new events (newest first in the array)
            for (let i = data.events.length - 1; i >= 0; i--) {
                const event = data.events[i];
                const entry = createEventEntry(event);
                log.prepend(entry);
            }

            // Cap at 50 entries (plus the hidden empty div)
            while (log.children.length > 51) {
                log.removeChild(log.lastChild);
            }

            // Update count
            if (countEl) {
                const visibleCount = log.querySelectorAll("[data-event-entry]").length;
                countEl.textContent = `${visibleCount} events`;
            }

            // Auto-scroll: keep user at top to see newest
            if (wasAtTop) {
                log.scrollTop = 0;
            }
        } catch (err) {
            // Silent failure on event poll -- no notification spam
        }
    }

    function createEventEntry(event) {
        const iconInfo = eventIcons[event.type] || defaultEventIcon;
        const entry = document.createElement("div");
        entry.className = "flex items-start gap-2 py-2 px-3 border-b border-zinc-700/50 last:border-0";
        entry.setAttribute("data-event-entry", "true");

        // Format timestamp
        let timeStr = "";
        try {
            const dt = new Date(event.timestamp);
            timeStr = dt.toLocaleTimeString("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            });
        } catch (e) {
            timeStr = event.timestamp || "";
        }

        entry.innerHTML = `
            <span class="material-icons text-base ${iconInfo.color} mt-0.5 shrink-0">${iconInfo.icon}</span>
            <div class="flex-1 min-w-0">
                <div class="flex items-baseline justify-between gap-2">
                    <span class="text-sm text-white truncate">${escapeHtml(event.type || "unknown")}</span>
                    <span class="text-xs text-slate-400 shrink-0">${timeStr}</span>
                </div>
                <div class="text-xs text-slate-400 truncate">${escapeHtml(event.detail || "")}</div>
            </div>
        `;
        return entry;
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    // === Calibration wizard ===

    async function handleCalAmbient() {
        const btn = document.getElementById("ww-cal-ambient-btn");
        const recording = document.getElementById("ww-cal-recording");
        const statusEl = document.getElementById("ww-cal-status");
        const countdownEl = document.getElementById("ww-cal-countdown");
        const step1Content = document.getElementById("ww-cal-step1-content");

        if (!btn || !recording || !statusEl || !countdownEl) return;

        // Disable button and show recording state
        btn.disabled = true;
        btn.classList.add("opacity-50", "cursor-not-allowed");
        step1Content.classList.add("hidden");
        recording.classList.remove("hidden");
        statusEl.textContent = "Recording ambient noise...";

        // Client-side countdown
        let remaining = 3;
        countdownEl.textContent = `${remaining} seconds remaining`;
        const countdownInterval = setInterval(() => {
            remaining--;
            if (remaining > 0) {
                countdownEl.textContent = `${remaining} seconds remaining`;
            } else {
                countdownEl.textContent = "Processing...";
                clearInterval(countdownInterval);
            }
        }, 1000);

        try {
            const res = await fetch("/wake-word/calibrate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mode: "ambient" }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            clearInterval(countdownInterval);
            calState.ambient = data;
            calState.suggested = data.suggested_threshold;

            // Show results grid
            const results = document.getElementById("ww-cal-results");
            if (results) results.classList.remove("hidden");
            setElText("ww-cal-ambient-rms", data.rms_mean);
            setElText("ww-cal-peak-rms", data.rms_peak);
            setElText("ww-cal-suggested-threshold", data.suggested_threshold);

            // Hide recording state
            recording.classList.add("hidden");

            // Auto-advance to Step 2 after delay
            setTimeout(() => {
                updateStepIndicator(1, "completed");
                updateStepIndicator(2, "active");
                step1Content.classList.add("hidden");
                const step2Content = document.getElementById("ww-cal-step2-content");
                if (step2Content) step2Content.classList.remove("hidden");
            }, CAL_ADVANCE_DELAY);
        } catch (err) {
            clearInterval(countdownInterval);
            recording.classList.add("hidden");
            step1Content.classList.remove("hidden");
            btn.disabled = false;
            btn.classList.remove("opacity-50", "cursor-not-allowed");
            showNotification("Calibration failed: " + err.message, "error");
        }
    }

    async function handleCalPhrase() {
        const btn = document.getElementById("ww-cal-phrase-btn");
        const recording = document.getElementById("ww-cal-recording");
        const statusEl = document.getElementById("ww-cal-status");
        const countdownEl = document.getElementById("ww-cal-countdown");
        const step2Content = document.getElementById("ww-cal-step2-content");

        if (!btn || !recording || !statusEl || !countdownEl) return;

        // Disable button and show recording state
        btn.disabled = true;
        btn.classList.add("opacity-50", "cursor-not-allowed");
        step2Content.classList.add("hidden");
        recording.classList.remove("hidden");
        statusEl.textContent = "Say the wake word now...";

        // Client-side countdown
        let remaining = 3;
        countdownEl.textContent = `${remaining} seconds remaining`;
        const countdownInterval = setInterval(() => {
            remaining--;
            if (remaining > 0) {
                countdownEl.textContent = `${remaining} seconds remaining`;
            } else {
                countdownEl.textContent = "Processing...";
                clearInterval(countdownInterval);
            }
        }, 1000);

        try {
            const res = await fetch("/wake-word/calibrate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mode: "phrase" }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            clearInterval(countdownInterval);
            calState.phrase = data;

            // Update results grid with phrase data
            setElText("ww-cal-phrase-peak", data.rms_peak);
            const results = document.getElementById("ww-cal-results");
            if (results) results.classList.remove("hidden");

            // Hide recording state
            recording.classList.add("hidden");

            // Auto-advance to Step 3 after delay
            setTimeout(() => {
                updateStepIndicator(2, "completed");
                updateStepIndicator(3, "active");
                step2Content.classList.add("hidden");
                const step3Content = document.getElementById("ww-cal-step3-content");
                if (step3Content) step3Content.classList.remove("hidden");
                setElText("ww-cal-suggested-value", calState.suggested);
            }, CAL_ADVANCE_DELAY);
        } catch (err) {
            clearInterval(countdownInterval);
            recording.classList.add("hidden");
            step2Content.classList.remove("hidden");
            btn.disabled = false;
            btn.classList.remove("opacity-50", "cursor-not-allowed");
            showNotification("Calibration failed: " + err.message, "error");
        }
    }

    async function handleCalApply() {
        const persistCheckbox = document.getElementById("ww-cal-persist");
        const persist = persistCheckbox ? persistCheckbox.checked : true;

        try {
            let res;
            if (persist) {
                res = await fetch("/wake-word/calibrate/apply", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ threshold: calState.suggested }),
                });
            } else {
                res = await fetch("/wake-word/runtime-config", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ threshold: calState.suggested }),
                });
            }
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            showNotification("Calibration applied", "success");
            resetCalibrationWizard();
        } catch (err) {
            showNotification("Failed to apply calibration: " + err.message, "error");
            // Keep wizard at Step 3 for retry
        }
    }

    // === Calibration helpers ===

    function updateStepIndicator(stepNum, state) {
        const stepEl = document.getElementById(`ww-cal-step-${stepNum}`);
        if (!stepEl) return;
        const circle = stepEl.querySelector("span:first-child");
        const label = stepEl.querySelector("span:last-child");
        if (!circle || !label) return;

        if (state === "active") {
            circle.className = "w-6 h-6 rounded-full bg-emerald-500 text-white text-xs font-semibold flex items-center justify-center";
            circle.innerHTML = `${stepNum}`;
            label.className = "text-xs text-slate-300";
        } else if (state === "completed") {
            circle.className = "w-6 h-6 rounded-full bg-emerald-500 text-white text-xs font-semibold flex items-center justify-center";
            circle.innerHTML = '<span class="material-icons text-sm">check</span>';
            label.className = "text-xs text-slate-300";
        } else {
            // future / default
            circle.className = "w-6 h-6 rounded-full bg-zinc-700 text-zinc-400 text-xs font-semibold flex items-center justify-center";
            circle.innerHTML = `${stepNum}`;
            label.className = "text-xs text-zinc-500";
        }
    }

    function resetCalibrationWizard() {
        calState = { ambient: null, phrase: null, suggested: null };

        // Reset step indicators
        updateStepIndicator(1, "active");
        updateStepIndicator(2, "future");
        updateStepIndicator(3, "future");

        // Show step 1, hide step 2/3
        const step1 = document.getElementById("ww-cal-step1-content");
        const step2 = document.getElementById("ww-cal-step2-content");
        const step3 = document.getElementById("ww-cal-step3-content");
        const recording = document.getElementById("ww-cal-recording");
        const results = document.getElementById("ww-cal-results");

        if (step1) step1.classList.remove("hidden");
        if (step2) step2.classList.add("hidden");
        if (step3) step3.classList.add("hidden");
        if (recording) recording.classList.add("hidden");
        if (results) results.classList.add("hidden");

        // Re-enable buttons
        const ambientBtn = document.getElementById("ww-cal-ambient-btn");
        const phraseBtn = document.getElementById("ww-cal-phrase-btn");
        if (ambientBtn) {
            ambientBtn.disabled = false;
            ambientBtn.classList.remove("opacity-50", "cursor-not-allowed");
        }
        if (phraseBtn) {
            phraseBtn.disabled = false;
            phraseBtn.classList.remove("opacity-50", "cursor-not-allowed");
        }

        // Reset result values
        setElText("ww-cal-ambient-rms", "--");
        setElText("ww-cal-peak-rms", "--");
        setElText("ww-cal-suggested-threshold", "--");
        setElText("ww-cal-phrase-peak", "--");
        setElText("ww-cal-suggested-value", "--");
    }

    function setElText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value !== null && value !== undefined ? value : "--";
    }

    return { init };
})();

// Make WakeWordPanel globally available
window.WakeWordPanel = WakeWordPanel;
