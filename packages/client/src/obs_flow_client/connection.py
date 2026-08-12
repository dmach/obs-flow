"""Connection management for the OBS Flow client.

This module provides the Connection class, which handles HTTP communication
with the OBS Flow server using connection pooling via requests.Session.
"""

from types import TracebackType
from typing import Self

import requests


class Connection:
    """Manages the HTTP connection to the OBS Flow server.

    This class encapsulates a requests.Session to perform connection pooling
    and keep-alive, and provides helper methods to perform requests.
    """

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        """Initializes the connection.

        Args:
            base_url: The base URL of the OBS Flow server (e.g., 'http://localhost:8000').
            timeout: Default timeout in seconds for all requests.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def post(self, path: str, data: bytes) -> bytes:
        """Sends a POST request with raw bytes and returns raw bytes response.

        Args:
            path: The API endpoint path (e.g., '/api/v1/pr/sync').
            data: The raw request body bytes.

        Returns:
            The raw response body bytes.

        Raises:
            requests.HTTPError: If the HTTP request returned an unsuccessful status code.
            requests.RequestException: For other connection or request errors.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = self.session.post(url, data=data, timeout=self.timeout)
        response.raise_for_status()
        return response.content

    def close(self) -> None:
        """Closes the underlying requests session."""
        self.session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()


def create_connection(base_url: str, timeout: float = 10.0) -> Connection:
    """Initializes and returns a Connection instance.

    Args:
        base_url: The base URL of the OBS Flow server.
        timeout: Default timeout in seconds for all requests.

    Returns:
        An initialized Connection instance.
    """
    return Connection(base_url=base_url, timeout=timeout)
