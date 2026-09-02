/**
 * OBS Flow - Theme & Font Size Management
 * Handles persistent light/dark theme toggling and font size switching with zero FOUC (Flash of Unstyled Content).
 */

/**
 * Initializes the theme from localStorage or system preference.
 * This should be executed as early as possible in the <head> to prevent FOUC.
 */
function initTheme() {
    const savedTheme = localStorage.getItem("theme") || "auto";
    if (savedTheme !== "auto") {
        document.documentElement.setAttribute("data-theme", savedTheme);
    }
}

/**
 * Initializes the font size from localStorage.
 * This should be executed as early as possible in the <head> to prevent FOUC.
 */
function initFontSize() {
    const savedSize = localStorage.getItem("font-size") || "small";
    document.documentElement.setAttribute("data-font-size", savedSize);
}

/**
 * Toggles the theme between light and dark modes and persists the choice.
 */
function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const activeTheme = current || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const nextTheme = activeTheme === "dark" ? "light" : "dark";

    document.documentElement.setAttribute("data-theme", nextTheme);
    localStorage.setItem("theme", nextTheme);
}

// Run initializations immediately upon script load in <head>
initTheme();
initFontSize();

// Bind event listeners once the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle
    const toggleBtn = document.getElementById("theme-toggle");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", (e) => {
            e.preventDefault();
            toggleTheme();
        });
    }

    // Font Size Switcher
    const fontBtns = document.querySelectorAll('.font-size-btn');
    if (fontBtns.length > 0) {
        const currentSize = document.documentElement.getAttribute("data-font-size") || "small";

        // Highlight the active button on load
        fontBtns.forEach(btn => {
            if (btn.getAttribute('data-size') === currentSize) {
                btn.classList.add('active');
            }

            // Handle click events
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const size = btn.getAttribute('data-size');

                document.documentElement.setAttribute("data-font-size", size);
                localStorage.setItem("font-size", size);

                // Update active classes
                fontBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });
    }
});
