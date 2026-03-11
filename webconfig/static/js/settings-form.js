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

    const bindEnvEditorCard = () => {
        const envEditorCard = document.getElementById("env-editor-card");
        const envEditorBtnWrapper = document.getElementById("env-editor-btn-wrapper");
        const openEnvEditorBtn = document.getElementById("open-env-editor-modal-btn");

        if (!envEditorCard || !envEditorBtnWrapper || !openEnvEditorBtn) return;

        envEditorCard.addEventListener("click", (e) => {
            if (e.target.closest("#open-env-editor-modal-btn")) return;
            const isHidden = envEditorBtnWrapper.classList.contains("hidden");
            envEditorBtnWrapper.classList.toggle("hidden", !isHidden);
        });

        openEnvEditorBtn.addEventListener("click", (e) => {
            e.stopPropagation();
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

    const NEWS_SOURCE_TEMPLATES = {
        google_news_headlines: {
            name: "Google News (Headlines)",
            url: "https://news.google.com/rss?hl=en-GB&gl=GB&ceid=GB:en",
            topics: ["general", "headlines"],
        },
        google_news_localized: {
            name: "Google News (Localized search)",
            url: "https://news.google.com/rss/search?q={{query}}&hl=en-GB&gl=GB&ceid=GB:en",
            topics: ["general", "headlines"],
        },
        open_meteo_forecast: {
            name: "Open-Meteo Forecast (Amsterdam)",
            url: "https://api.open-meteo.com/v1/forecast?latitude=52.3676&longitude=4.9041&timezone=Europe%2FAmsterdam",
            topics: ["weather", "forecast"],
        },
        espn_premier_league: {
            name: "ESPN Scoreboard (Premier League)",
            url: "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
            topics: ["sports", "epl", "soccer", "football"],
        },
        espn_soccer_news: {
            name: "ESPN Soccer News (Serie A)",
            url: "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/news",
            topics: ["sports", "soccer", "football", "news", "serie a", "italy"],
        },
        espn_team_info_napoli: {
            name: "ESPN Team Info (Napoli)",
            url: "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/teams/114",
            topics: ["sports", "soccer", "football", "team", "napoli", "serie a"],
        },
        billy_project_releases: {
            name: "Billy Project Releases",
            url: "https://github.com/Thokoop/billy-b-assistant/releases.atom",
            topics: ["billy", "project", "release", "update", "changelog"],
        },
    };

    const isDynamicSourceUrl = (rawUrl) => {
        let candidate = String(rawUrl || "");
        if (!candidate) return false;
        candidate = candidate
            .replaceAll("&amp;", "&")
            .replaceAll("&#123;", "{")
            .replaceAll("&#125;", "}");

        if (/\{\{\s*query\s*\}\}/i.test(candidate)) return true;
        if (/\{\s*query\s*\}/i.test(candidate)) return true;
        if (/%7B%7B\s*query\s*%7D%7D/i.test(candidate)) return true;
        if (/%7B\s*query\s*%7D/i.test(candidate)) return true;

        try {
            // Handle single and double encoded URLs.
            for (let i = 0; i < 2; i += 1) {
                const decoded = decodeURIComponent(candidate);
                if (decoded === candidate) break;
                candidate = decoded;
                if (/\{\{\s*query\s*\}\}/i.test(candidate)) return true;
                if (/\{\s*query\s*\}/i.test(candidate)) return true;
                if (/%7B%7B\s*query\s*%7D%7D/i.test(candidate)) return true;
                if (/%7B\s*query\s*%7D/i.test(candidate)) return true;
            }
        } catch {
            // Ignore decode errors; final fallback below.
        }
        return false;
    };

    const applyNewsSourceTemplate = (templateKey) => {
        const nameInput = document.getElementById("news-source-name");
        const urlInput = document.getElementById("news-source-url");
        const topicsInput = document.getElementById("news-source-topics");
        if (!nameInput || !urlInput || !topicsInput) return;

        const template = NEWS_SOURCE_TEMPLATES[templateKey];
        if (!template) return;

        nameInput.value = template.name || "";
        urlInput.value = template.url || "";
        topicsInput.value = (template.topics || []).join(", ");
    };

    const renderNewsSources = (sources) => {
        const list = document.getElementById("news-sources-list");
        if (!list) return;
        list.innerHTML = "";

        if (!sources || sources.length === 0) {
            list.innerHTML = '<div class="text-sm text-slate-400">No sources configured.</div>';
            return;
        }

        const escapeHtml = (value) => String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");

        sources.forEach((source) => {
            const row = document.createElement("div");
            row.className = "relative bg-zinc-900/70 border border-zinc-700 rounded-lg p-4 flex flex-wrap items-start gap-4 transition-colors hover:border-zinc-500";
            row.innerHTML = `
                <div class="grow min-w-[220px] pr-20">
                    <div class="text-sm font-semibold text-slate-100 mb-1" data-view-name>${escapeHtml(source.name)}</div>
                    <a href="${escapeHtml(source.url)}" target="_blank" rel="noopener"
                       class="text-xs text-blue-300 hover:text-cyan-300 break-all underline" data-view-url>${escapeHtml(source.url)}</a>
                    <div class="text-xs text-cyan-300 mt-1" data-view-topics>${(source.topics || []).length ? escapeHtml((source.topics || []).join(", ")) : "general"}</div>
                    <div class="text-xs text-slate-400 mt-1" data-view-query>${isDynamicSourceUrl(source.url) ? "query: dynamic" : "query: static feed"}</div>
                </div>
                <div class="absolute top-3 right-3 flex items-center gap-2">
                    <button type="button" class="text-zinc-500 hover:text-amber-400 p-1 rounded transition-colors" data-action="edit" title="Edit source">
                        <span class="material-icons text-sm">edit</span>
                    </button>
                    <button type="button" class="text-zinc-500 hover:text-rose-400 p-1 rounded transition-colors" data-action="delete" title="Delete source">
                        <span class="material-icons text-sm">delete</span>
                    </button>
                </div>
                <div class="hidden w-full mt-2 p-3 rounded border border-zinc-700 bg-zinc-900/50 space-y-2" data-edit-panel>
                    <div class="grid gap-2">
                        <input type="text" class="w-full p-2 bg-zinc-800 border border-zinc-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-cyan-500" data-edit-name value="${escapeHtml(source.name)}" placeholder="Source name">
                        <input type="url" class="w-full p-2 bg-zinc-800 border border-zinc-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-cyan-500" data-edit-url value="${escapeHtml(source.url)}" placeholder="URL (optional {{query}}): https://example.com/feed.xml">
                    </div>
                    <input type="text" class="w-full p-2 bg-zinc-800 border border-zinc-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-cyan-500" data-edit-topics value="${escapeHtml((source.topics || []).join(", "))}" placeholder="Keywords (comma-separated)">
                    <div class="flex items-center justify-between gap-2">
                        <button type="button" class="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-slate-200 transition-colors" data-action="cancel">
                            <span class="material-icons text-sm leading-none">close</span>Cancel
                        </button>
                        <button type="button" class="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors" data-action="save">
                            <span class="material-icons text-sm leading-none">save</span>Save
                        </button>
                    </div>
                </div>
            `;

            const edit = row.querySelector('[data-action="edit"]');
            const remove = row.querySelector('[data-action="delete"]');
            const save = row.querySelector('[data-action="save"]');
            const cancel = row.querySelector('[data-action="cancel"]');
            const editPanel = row.querySelector('[data-edit-panel]');

            if (edit && editPanel) {
                edit.addEventListener("click", () => {
                    editPanel.classList.toggle("hidden");
                    edit.innerHTML = editPanel.classList.contains("hidden")
                        ? '<span class="material-icons text-sm">edit</span>'
                        : '<span class="material-icons text-sm">close</span>';
                    edit.title = editPanel.classList.contains("hidden")
                        ? "Edit source"
                        : "Close editor";
                });
            }
            if (remove) {
                remove.addEventListener("click", async () => {
                    const response = await fetch(`/news/sources/${source.id}`, {method: "DELETE"});
                    if (!response.ok) {
                        showNotification("Failed to delete source", "error", 3000);
                    }
                    await loadNewsSources();
                });
            }
            if (cancel && editPanel) {
                cancel.addEventListener("click", () => {
                    editPanel.classList.add("hidden");
                    if (edit) {
                        edit.innerHTML = '<span class="material-icons text-sm">edit</span>';
                        edit.title = "Edit source";
                    }
                });
            }
            if (save) {
                save.addEventListener("click", async () => {
                    const payload = {
                        name: (row.querySelector('[data-edit-name]')?.value || "").trim(),
                        url: (row.querySelector('[data-edit-url]')?.value || "").trim(),
                        topics: (row.querySelector('[data-edit-topics]')?.value || "").trim(),
                    };
                    if (!payload.name || !payload.url) {
                        showNotification("Name and URL are required", "warning", 2500);
                        return;
                    }

                    const response = await fetch(`/news/sources/${source.id}`, {
                        method: "PATCH",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify(payload),
                    });
                    const data = await response.json();
                    if (!response.ok) {
                        showNotification(data.error || "Failed to save source", "error", 3000);
                        return;
                    }
                    showNotification("Source updated", "success", 2000);
                    await loadNewsSources();
                });
            }

            list.appendChild(row);
        });
    };

    const loadNewsSources = async () => {
        try {
            const res = await fetch("/news/sources");
            const data = await res.json();
            renderNewsSources(data.sources || []);
        } catch (error) {
            console.error("Failed to load news sources:", error);
            showNotification("Failed to load news sources", "error", 3000);
        }
    };

    const bindNewsSources = () => {
        const modal = document.getElementById("news-sources-modal");
        const openBtn = document.getElementById("news-sources-btn");
        const closeBtn = document.getElementById("close-news-sources-modal");
        const nameInput = document.getElementById("news-source-name");
        const urlInput = document.getElementById("news-source-url");
        const topicsInput = document.getElementById("news-source-topics");
        const addActions = document.getElementById("add-news-source-actions");
        const cancelAddBtn = document.getElementById("cancel-add-news-source-btn");
        const addBtn = document.getElementById("add-news-source-btn");
        if (!addBtn) return;
        let backdropPointerDown = false;

        const updateAddActionsVisibility = () => {
            if (!addActions || !nameInput || !urlInput) return;
            const hasRequiredValues = Boolean(nameInput.value.trim() && urlInput.value.trim());
            addActions.classList.toggle("hidden", !hasRequiredValues);
        };

        const openModal = async () => {
            if (!modal) return;
            modal.classList.remove("hidden");
            if (nameInput) nameInput.focus();
            updateAddActionsVisibility();
            await loadNewsSources();
        };

        const closeModal = () => {
            if (!modal) return;
            modal.classList.add("hidden");
        };

        if (openBtn) {
            openBtn.addEventListener("click", () => {
                openModal();
            });
        }
        if (closeBtn) {
            closeBtn.addEventListener("click", closeModal);
        }
        if (modal) {
            modal.addEventListener("mousedown", (event) => {
                backdropPointerDown = event.target === modal;
            });
            modal.addEventListener("click", (event) => {
                if (event.target === modal && backdropPointerDown) {
                    closeModal();
                }
                backdropPointerDown = false;
            });
        }

        if (cancelAddBtn) {
            cancelAddBtn.addEventListener("click", () => {
                if (nameInput) nameInput.value = "";
                if (urlInput) urlInput.value = "";
                if (topicsInput) topicsInput.value = "";
                updateAddActionsVisibility();
            });
        }

        if (nameInput) {
            nameInput.addEventListener("input", updateAddActionsVisibility);
        }
        if (urlInput) {
            urlInput.addEventListener("input", updateAddActionsVisibility);
        }

        const toggleExamplesBtn = document.getElementById("toggle-news-examples-btn");
        const examplesList = document.getElementById("news-examples-list");
        const examplesToggleIcon = document.getElementById("news-examples-toggle-icon");
        const examplesToggleLabel = document.getElementById("news-examples-toggle-label");
        if (toggleExamplesBtn && examplesList && examplesToggleIcon) {
            const updateExamplesToggle = () => {
                const collapsed = examplesList.classList.contains("hidden");
                examplesToggleIcon.textContent = collapsed ? "expand_more" : "expand_less";
                if (examplesToggleLabel) {
                    examplesToggleLabel.textContent = collapsed ? "Show examples" : "Hide examples";
                }
            };
            updateExamplesToggle();
            toggleExamplesBtn.addEventListener("click", () => {
                examplesList.classList.toggle("hidden");
                updateExamplesToggle();
            });
        }
        document.querySelectorAll(".news-template-use-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const templateKey = btn.getAttribute("data-template-key");
                applyNewsSourceTemplate(templateKey || "");
                updateAddActionsVisibility();
            });
        });

        addBtn.addEventListener("click", async () => {
            const name = (nameInput?.value || "").trim();
            const url = (urlInput?.value || "").trim();
            const topics = (topicsInput?.value || "").trim();

            if (!name || !url) {
                showNotification("Source and URL are required", "warning", 2500);
                return;
            }

            const response = await fetch("/news/sources", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    name,
                    url,
                    topics,
                }),
            });
            const data = await response.json();
            if (!response.ok) {
                showNotification(data.error || "Failed to add source", "error", 3000);
                return;
            }

            if (nameInput) nameInput.value = "";
            if (urlInput) urlInput.value = "";
            if (topicsInput) topicsInput.value = "";
            updateAddActionsVisibility();
            showNotification("News source added", "success", 2500);
            renderNewsSources(data.sources || []);
        });

        updateAddActionsVisibility();
        loadNewsSources();
    };

    return {
        handleSettingsSave,
        populateDropdowns,
        saveDropdownSelections,
        initMouthArticulationSlider,
        refreshFromConfig,
        bindFactoryReset,
        bindEnvEditorCard,
        bindNewsSources,
    };
})();

// Make SettingsForm globally available
window.SettingsForm = SettingsForm;
