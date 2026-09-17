import urllib.parse

def is_safe_url(url: str) -> bool:
    """
    Validates that a URL is safe to be used as a bookmark.
    It must be a relative URL starting with '/' and must not contain a scheme or netloc.
    """
    if not url or not url.startswith("/"):
        return False

    try:
        parsed = urllib.parse.urlparse(url)
        # Ensure there's no scheme (like http, https, javascript, data) and no netloc (like evil.com)
        if parsed.scheme or parsed.netloc:
            return False
        return True
    except ValueError:
        return False
