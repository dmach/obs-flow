// "Select all" checkboxes: <input type="checkbox" data-select-all="NAME"> toggles every
// checkbox named NAME. Delegated on document so it also covers rows swapped in by htmx.
document.addEventListener('change', (e) => {
    const name = e.target.dataset?.selectAll;
    if (!name) {
        return;
    }
    document.querySelectorAll(`input[type="checkbox"][name="${name}"]`).forEach(cb => {
        cb.checked = e.target.checked;
    });
});

// Bind event listeners once the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
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

function initDebounceCountdowns() {
    document.querySelectorAll('.debounce-countdown').forEach(el => {
        if (el._countdownInterval) return;

        const expiresStr = el.getAttribute('data-expires');
        if (!expiresStr) return;
        const expires = new Date(expiresStr);
        const timerEl = el.querySelector('.countdown-timer');

        function tick() {
            const now = new Date();
            const diffMs = expires - now;
            if (diffMs <= 0) {
                if (timerEl) timerEl.textContent = '00m 00s';
                clearInterval(el._countdownInterval);
                el._countdownInterval = null;
                if (window.htmx) {
                    window.htmx.trigger(el, 'countdown-expired');
                }
            } else {
                const totalSec = Math.floor(diffMs / 1000);
                const days = Math.floor(totalSec / 86400);
                const hours = Math.floor((totalSec % 86400) / 3600);
                const minutes = Math.floor((totalSec % 3600) / 60);
                const seconds = totalSec % 60;
                let parts = [];
                if (days > 0) parts.push(days + 'd');
                if (hours > 0 || days > 0) parts.push(hours + 'h');
                parts.push(String(minutes).padStart(2, '0') + 'm');
                parts.push(String(seconds).padStart(2, '0') + 's');
                if (timerEl) timerEl.textContent = parts.join(' ');
            }
        }

        tick();
        el._countdownInterval = setInterval(tick, 1000);
    });
}

document.addEventListener('DOMContentLoaded', initDebounceCountdowns);
document.addEventListener('htmx:afterSwap', initDebounceCountdowns);
