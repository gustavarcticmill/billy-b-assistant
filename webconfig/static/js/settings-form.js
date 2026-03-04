// ===================== SETTINGS FORM =====================
const SettingsForm = (() => {
    const populateDropdowns = (cfg) => {
        // Populate dropdown values with saved configuration
        const dropdowns = [
            { id: 'OPENAI_MODEL', key: 'OPENAI_MODEL' },
            { id: 'VOICE', key: 'VOICE' },
            { id: 'RUN_MODE', key: 'RUN_MODE' },
            { id: 'TURN_EAGERNESS', key: 'TURN_EAGERNESS' },
            { id: 'BILLY_MODEL', key: 'BILLY_MODEL' },
            { id: 'BILLY_PINS_SELECT', key: 'BILLY_PINS' },
            { id: 'HA_LANG', key: 'HA_LANG' }
        ];

        dropdowns.forEach(({ id, key }) => {
            const element = document.getElementById(id);
            if (element) {
                // First try to get from localStorage (user's last selection)
                const savedValue = localStorage.getItem(`dropdown_${id}`);
                // Then fall back to config value
                const configValue = cfg[key];
                const valueToSet = savedValue || configValue;
                
                if (valueToSet) {
                    element.value = valueToSet;
                }
            }
        });
    };

    const saveDropdownSelections = () => {
        // Save dropdown selections to localStorage when they change
        const dropdowns = [
            'OPENAI_MODEL', 'VOICE', 'RUN_MODE', 'TURN_EAGERNESS',
            'BILLY_MODEL', 'BILLY_PINS_SELECT', 'HA_LANG'
        ];

        dropdowns.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => {
                    localStorage.setItem(`dropdown_${id}`, element.value);
                });
            }
        });
    };

    const handleSettingsSave = () => {
        document.getElementById("config-form").addEventListener("submit", async function (e) {
            e.preventDefault();

            const formData = new FormData(this);
            const payload = Object.fromEntries(formData.entries());

            const flaskPortInput = document.getElementById("FLASK_PORT");
            const oldPort = parseInt(flaskPortInput.getAttribute("data-original")) || 80;
            const newPort = parseInt(payload["FLASK_PORT"] || "80");

            const hostnameInput = document.getElementById("hostname");
            const oldHostname = (hostnameInput.getAttribute("data-original") || hostnameInput.defaultValue || "").trim();
            const newHostname = (formData.get("hostname") || "").trim();

            const pinSelect = document.getElementById("BILLY_PINS_SELECT");
            if (pinSelect) {
                payload.BILLY_PINS = pinSelect.value; // "new" | "legacy"
            }

            // Manually add MOUTH_ARTICULATION value
            const mouthArticulationInput = document.getElementById("MOUTH_ARTICULATION");
            if (mouthArticulationInput) {
                payload.MOUTH_ARTICULATION = mouthArticulationInput.value;
            }

            // Manually add SHOW_RC_VERSIONS value (only set to True when checked)
            const showRCVersionsCheckbox = document.getElementById("SHOW_RC_VERSIONS");
            if (showRCVersionsCheckbox && showRCVersionsCheckbox.checked) {
                payload.SHOW_RC_VERSIONS = 'True';
            } else {
                payload.SHOW_RC_VERSIONS = 'False';
            }

            // Manually add FLAP_ON_BOOT value (only set to True when checked)
            const flapOnBootCheckbox = document.getElementById("FLAP_ON_BOOT");
            if (flapOnBootCheckbox && flapOnBootCheckbox.checked) {
                payload.FLAP_ON_BOOT = 'True';
            } else {
                payload.FLAP_ON_BOOT = 'False';
            }

            let hostnameChanged = false;

            const saveResponse = await fetch("/save", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });
            const saveResult = await saveResponse.json();
            const portChanged = saveResult.port_changed || (oldPort !== newPort);

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

            // Auto-refresh configuration instead of restarting services
            try {
                const refreshResponse = await fetch("/config/auto-refresh", {method: "POST"});
                const refreshData = await refreshResponse.json();
                
                if (refreshData.status === "ok") {
                    showNotification("Settings saved and applied", "success");
                    
                    // Update UI with new configuration
                    if (refreshData.config) {
                        // Update dropdowns with new values
                        const dropdowns = [
                            'OPENAI_MODEL', 'VOICE', 'RUN_MODE', 'TURN_EAGERNESS',
                            'BILLY_MODEL', 'BILLY_PINS_SELECT', 'HA_LANG'
                        ];
                        dropdowns.forEach(id => {
                            const element = document.getElementById(id);
                            if (element && refreshData.config[id]) {
                                element.value = refreshData.config[id];
                                localStorage.setItem(`dropdown_${id}`, refreshData.config[id]);
                            }
                        });
                        
                        // Refresh user profile panel if it exists
                        if (window.UserProfilePanel && window.UserProfilePanel.refreshUserProfile) {
                            window.UserProfilePanel.refreshUserProfile();
                        }
                    }
                } else {
                    console.error("Auto-refresh failed, falling back to restart:", refreshData.error || "Auto-refresh failed");
                    await fetch("/restart-billy", {method: "POST"});
                    showNotification("Settings saved – Billy restarted", "success");
                    return;
                }
            } catch (error) {
                console.error("Auto-refresh failed, falling back to restart:", error);
                // Fallback to restart Billy service if auto-refresh fails
                await fetch("/restart-billy", {method: "POST"});
                showNotification("Settings saved – Billy restarted", "success");
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

    const bindFactoryReset = () => {
        const resetBtn = document.getElementById("factory-reset-btn");
        const resetBtnWrapper = document.getElementById("factory-reset-btn-wrapper");
        const resetCard = document.getElementById("reset-defaults-card");
        const modal = document.getElementById("factory-reset-modal");
        const closeBtn = document.getElementById("close-factory-reset-modal");
        const cancelBtn = document.getElementById("cancel-factory-reset");
        const confirmBtn = document.getElementById("confirm-factory-reset");
        const envCheckbox = document.getElementById("factory-reset-env");
        const profilesCheckbox = document.getElementById("factory-reset-profiles");
        const personasCheckbox = document.getElementById("factory-reset-personas");
        const logsCheckbox = document.getElementById("factory-reset-logs");
        const gitCheckbox = document.getElementById("factory-reset-git");
        const wifiCheckbox = document.getElementById("factory-reset-wifi");
        const rebootCheckbox = document.getElementById("factory-reset-reboot");
        const advancedWrap = document.getElementById("factory-reset-advanced");
        const advancedToggle = document.getElementById("toggle-factory-advanced");

        if (!resetBtn || !resetBtnWrapper) return;
        if (!modal || !closeBtn || !cancelBtn || !confirmBtn) return;
        if (wifiCheckbox && rebootCheckbox) {
            wifiCheckbox.addEventListener("change", () => {
                if (wifiCheckbox.checked) {
                    rebootCheckbox.checked = true;
                    rebootCheckbox.disabled = true;
                } else {
                    rebootCheckbox.disabled = false;
                }
            });
        }
        if (advancedWrap && advancedToggle) {
            advancedToggle.addEventListener("click", () => {
                const isHidden = advancedWrap.classList.contains("hidden");
                advancedWrap.classList.toggle("hidden", !isHidden);
                advancedToggle.textContent = isHidden
                    ? "Hide advanced settings"
                    : "Show advanced settings";
            });
        }

        const openModal = () => {
            modal.classList.remove("hidden");
        };
        const closeModal = () => {
            modal.classList.add("hidden");
        };

        if (resetCard) {
            resetCard.addEventListener("click", (e) => {
                const isHidden = resetBtnWrapper.classList.contains("hidden");
                if (isHidden) {
                    resetBtnWrapper.classList.remove("hidden");
                } else {
                    resetBtnWrapper.classList.add("hidden");
                }
            });
        }

        resetBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            openModal();
        });

        closeBtn.addEventListener("click", closeModal);
        cancelBtn.addEventListener("click", closeModal);
        modal.addEventListener("click", (e) => {
            if (e.target === modal) closeModal();
        });

        confirmBtn.addEventListener("click", async () => {
            const options = {
                env: envCheckbox?.checked ?? false,
                profiles: profilesCheckbox?.checked ?? false,
                personas: personasCheckbox?.checked ?? false,
                logs: logsCheckbox?.checked ?? false,
                git: gitCheckbox?.checked ?? false,
                wifi: wifiCheckbox?.checked ?? false,
                reboot: rebootCheckbox?.checked ?? false,
            };

            const anySelected = Object.values(options).some(Boolean);
            if (!anySelected) {
                showNotification("Select at least one reset option.", "warning", 4000);
                return;
            }

            confirmBtn.disabled = true;
            confirmBtn.classList.add("opacity-50", "cursor-not-allowed");
            resetBtn.disabled = true;
            resetBtn.classList.add("opacity-50", "cursor-not-allowed");
            showNotification("Running reset to defaults...", "warning", 4000);

            try {
                const response = await fetch("/factory-reset", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({confirm: true, options}),
                });
                const data = await response.json();

                if (response.ok && data.status === "ok") {
                    const summary = [];
                    if (data.removed?.env) summary.push(".env");
                    if (data.removed?.versions) summary.push("versions.ini");
                    if (data.removed?.profiles?.length) summary.push(`${data.removed.profiles.length} profile(s)`);
                    if (data.requested?.personas) {
                        const personaCount = data.removed?.personas?.length || 0;
                        summary.push(`${personaCount} persona(s)`);
                    }
                    if (data.logs_cleared) summary.push("service logs");
                    if (data.git_reset) summary.push("git worktree");
                    if (data.requested?.wifi) {
                        summary.push("Wi-Fi connection");
                    }
                    const msg = summary.length
                        ? `Reset to defaults complete: ${summary.join(", ")}`
                        : "Reset to defaults complete.";
                    let postfix = "";
                    if (data.rebooting) {
                        postfix = " Rebooting now...";
                    } else if (data.restarting_services) {
                        postfix = " Restarting UI...";
                    }
                    showNotification(`${msg}${postfix}`, "success", 6000);
                    if (data.restarting_services) {
                        try {
                            await fetch("/restart", {method: "POST"});
                            setTimeout(() => location.reload(), 3000);
                        } catch (restartErr) {
                            console.error("Failed to restart UI:", restartErr);
                        }
                    }
                    closeModal();
                } else {
                    const errors = data.errors?.length ? data.errors.join("; ") : (data.error || "Reset to defaults incomplete");
                    showNotification(errors, "error", 8000);
                }
            } catch (error) {
                console.error("Reset to defaults failed:", error);
                showNotification("Reset to defaults failed", "error", 6000);
            } finally {
                confirmBtn.disabled = false;
                confirmBtn.classList.remove("opacity-50", "cursor-not-allowed");
                resetBtn.disabled = false;
                resetBtn.classList.remove("opacity-50", "cursor-not-allowed");
            }
        });
    };

    fetch('/hostname')
        .then(res => res.json())
        .then(data => {
            if (data.hostname) {
                const input = document.getElementById('hostname');
                input.value = data.hostname;
                input.setAttribute('data-original', data.hostname);
            }
        });

    const flaskPortInput = document.getElementById("FLASK_PORT");
    if (flaskPortInput) {
        flaskPortInput.setAttribute("data-original", flaskPortInput.value);
    }

    const initMouthArticulationSlider = () => {
        // Use the same slider pattern as mic gain
        setupSlider("mouth-articulation-bar", "mouth-articulation-fill", "MOUTH_ARTICULATION", 1, 10);
    };

    function setupSlider(barId, fillId, inputId, min, max) {
        const bar = document.getElementById(barId);
        const fill = document.getElementById(fillId);
        const input = document.getElementById(inputId);

        if (!bar || !fill || !input) return;

        let isDragging = false;
        const updateUI = (val) => {
            const percent = ((val - min) / (max - min)) * 100;
            fill.style.width = `${percent}%`;
            fill.dataset.value = val;
            // Ensure input value is set for form submission
            input.value = val;
            input.setAttribute('value', val);
            // Update the value display
            const valueDisplay = document.getElementById("mouth-articulation-value");
            if (valueDisplay) {
                valueDisplay.textContent = val;
            }
        };
        const updateFromMouse = (e) => {
            const rect = bar.getBoundingClientRect();
            const percent = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
            const val = Math.round(min + percent * (max - min));
            input.value = val;
            // Ensure the input value is properly set for form submission
            input.setAttribute('value', val);
            input.dispatchEvent(new Event("input", {bubbles: true}));
            updateUI(val);
        };
        bar.addEventListener("mousedown", (e) => { isDragging = true; updateFromMouse(e); });
        document.addEventListener("mousemove", (e) => { if (isDragging) updateFromMouse(e); });
        document.addEventListener("mouseup", () => { isDragging = false; });
        input.addEventListener("input", () => updateUI(Number(input.value)));
        updateUI(Number(input.value));
    }

    const refreshFromConfig = (config) => {
        // Update dropdowns with new configuration values
        const dropdowns = [
            'OPENAI_MODEL', 'VOICE', 'RUN_MODE', 'TURN_EAGERNESS',
            'BILLY_MODEL', 'BILLY_PINS_SELECT', 'HA_LANG'
        ];
        dropdowns.forEach(id => {
            const element = document.getElementById(id);
            if (element && config[id]) {
                element.value = config[id];
                localStorage.setItem(`dropdown_${id}`, config[id]);
            }
        });
    };

    return {
        handleSettingsSave,
        populateDropdowns,
        saveDropdownSelections,
        initMouthArticulationSlider,
        refreshFromConfig,
        bindFactoryReset,
    };
})();

// Make SettingsForm globally available
window.SettingsForm = SettingsForm;
