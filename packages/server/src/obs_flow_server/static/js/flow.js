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

    // Submit GET forms without sending empty form fields, which is much cleaner and user-friendly.
    document.querySelectorAll('form[data-clean-url="true"]').forEach(form => {
        form.addEventListener('submit', function(e) {
            // Prevent the browser's default form submission to handle it via JS.
            e.preventDefault();

            // Determine the target URL from the form's action attribute with a fallback to the current page path.
            let actionUrl = this.getAttribute('action');
            if (!actionUrl) {
                actionUrl = window.location.pathname;
            }

            // Override action URL if the clicked submit button has a specific formaction attribute.
            if (e.submitter && e.submitter.hasAttribute('formaction')) {
                actionUrl = e.submitter.getAttribute('formaction');
            }

            const url = new URL(actionUrl, window.location.origin);
            const formData = new FormData(this);
            for (const [key, value] of formData.entries()) {
                if (value && value.trim() !== '') {
                    // Append only non-empty parameters to the URL query string.
                    url.searchParams.append(key, value);
                }
            }

            // Redirect the browser to the newly constructed clean URL.
            window.location.href = url.toString();
        });
    });
});
