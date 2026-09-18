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
