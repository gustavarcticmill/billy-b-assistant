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

function toggleInputVisibility(inputId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(`${inputId}_icon`);
    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";
    icon.textContent = isHidden ? "visibility_off" : "visibility";
}

function toggleDropdown(btn) {
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
        if (!menu.classList.contains('hidden') && !menu.parentElement.contains(btn)) {
            menu.classList.add('hidden');
            const arrow = menu.parentElement.querySelector('.dropdown-toggle .material-icons');
            if (arrow) arrow.classList.remove('rotate-180');
        }
    });
    let dropdown = btn.closest('.relative').querySelector('.dropdown-menu');
    if (!dropdown) return;
    dropdown.classList.toggle('hidden');
    const arrow = btn.querySelector('.material-icons');
    if (arrow) arrow.classList.toggle('rotate-180');
}

function toggleTooltip(el) {
    if (!el) return;
    el.classList.toggle("text-cyan-400");

    const explicitTargetId = el.getAttribute("data-tooltip-target");
    if (explicitTargetId) {
        const explicitTooltip = document.getElementById(explicitTargetId);
        if (explicitTooltip) {
            const visible = explicitTooltip.getAttribute("data-visible") === "true";
            explicitTooltip.setAttribute("data-visible", visible ? "false" : "true");
            return;
        }
    }

    const label = el.closest("label");
    let tooltip = null;
    if (label && label.parentElement) {
        tooltip = label.parentElement.querySelector("[data-tooltip]");
    }
    if (!tooltip) {
        const container =
            el.closest(".relative") ||
            el.parentElement ||
            el.closest("div");
        if (container) {
            tooltip =
                container.querySelector("[data-tooltip]") ||
                container.parentElement?.querySelector("[data-tooltip]");
        }
    }
    if (!tooltip) return;

    const visible = tooltip.getAttribute("data-visible") === "true";
    tooltip.setAttribute("data-visible", visible ? "false" : "true");
}

document.addEventListener('click', (e) => {
    // Close dropdowns when clicking outside
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
        if (!menu.classList.contains('hidden') && !menu.closest('.relative').contains(e.target)) {
            menu.classList.add('hidden');
            const arrow = menu.parentElement.querySelector('.dropdown-toggle .material-icons');
            if (arrow) arrow.classList.remove('rotate-180');
        }
    });
    
    // Close tooltips when clicking outside
    document.querySelectorAll('[data-tooltip]').forEach(tooltip => {
        if (tooltip.getAttribute('data-visible') === 'true' && !tooltip.contains(e.target)) {
            let helpIcon = null;
            if (tooltip.id) {
                helpIcon = document.querySelector(
                    `[data-tooltip-target="${tooltip.id}"]`
                );
            }
            if (!helpIcon) {
                const container = tooltip.parentElement;
                helpIcon = container?.querySelector('.material-icons');
            }
            if (helpIcon && !helpIcon.contains(e.target)) {
                tooltip.setAttribute('data-visible', 'false');
                helpIcon.classList.remove('text-cyan-400');
            }
        }
    });
});

// ===================== LOADING OVERLAY =====================
const LoadingOverlay = (() => {
    const overlayId = "loading-overlay";
    const textId = "loading-overlay-text";
    const reloadFlagKey = "billy:reload_on_ws_reconnect";

    const show = (message = "Restarting Billy... reconnecting interface.") => {
        const overlay = document.getElementById(overlayId);
        const text = document.getElementById(textId);
        if (!overlay) return;
        if (text) text.textContent = message;
        overlay.classList.remove("hidden");
    };

    const hide = () => {
        const overlay = document.getElementById(overlayId);
        if (!overlay) return;
        overlay.classList.add("hidden");
    };

    const isVisible = () => {
        const overlay = document.getElementById(overlayId);
        return !!overlay && !overlay.classList.contains("hidden");
    };

    window.addEventListener("billy:websocket:connected", () => {
        if (isVisible()) {
            hide();
        }
        if (sessionStorage.getItem(reloadFlagKey) === "1") {
            sessionStorage.removeItem(reloadFlagKey);
            setTimeout(() => {
                window.location.reload();
            }, 200);
        }
    });

    return { show, hide, isVisible };
})();

window.LoadingOverlay = LoadingOverlay;
