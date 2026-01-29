"""Shared test helpers for integration tests."""

import json

from aiohttp import web
from aiohttp.test_utils import make_mocked_request
from yarl import URL


class MockResponse:
    """Wrapper to make web.Response behave like ClientResponse for tests."""

    def __init__(self, response):
        self._response = response
        self.status = response.status
        self.content_type = response.content_type
        self.headers = response.headers
        self._text = None
        self._json = None

    async def text(self):
        """Get response text."""
        if self._text is None:
            self._text = (
                self._response.text
                if hasattr(self._response, "text")
                else (
                    await self._response.text()
                    if hasattr(self._response, "__await__")
                    else str(self._response)
                )
            )
            if not isinstance(self._text, str):
                self._text = await self._text
        return self._text

    async def json(self):
        """Get response JSON."""
        if self._json is None:
            text = await self.text()
            self._json = json.loads(text)
        return self._json

    async def read(self):
        """Read response bytes."""
        text = await self.text()
        return text.encode("utf-8")


async def call_handler(app, method, path, headers=None, json_data=None):
    """Helper to call a handler through the app's router and middleware without binding to ports.

    This avoids PermissionError issues on macOS when TestServer tries to bind to ports.
    Uses app._handle() which processes requests through middleware and routing.
    Returns a MockResponse wrapper that behaves like ClientResponse.
    """
    # Normalize path (remove multiple slashes) - but preserve query string
    if "?" in path:
        path_part, query_part = path.split("?", 1)
        normalized_path = path_part.replace("//", "/").replace("//", "/")
        if normalized_path != "/" and normalized_path.endswith("/"):
            normalized_path = normalized_path[:-1]
        normalized_path = f"{normalized_path}?{query_part}"
    else:
        normalized_path = path.replace("//", "/").replace("//", "/")
        if normalized_path != "/" and normalized_path.endswith("/"):
            normalized_path = normalized_path[:-1]

    # Create a proper URL
    url = URL(f"http://localhost{normalized_path}")

    # Create a mocked request with proper URL and app
    request = make_mocked_request(method, str(url), headers=headers or {}, app=app)

    # Add json method if needed
    if json_data:

        async def mock_json():
            return json_data

        request.json = mock_json  # type: ignore[assignment,method-assign]

    # Use app._handle() which processes through middleware and routing
    try:
        response = await app._handle(request)
        # Check if response is an HTTPException (like 405 Method Not Allowed)
        if hasattr(response, "status_code") and response.status_code in [405, 404]:
            return MockResponse(web.Response(status=response.status_code, text=str(response)))
        return MockResponse(response)
    except web.HTTPMethodNotAllowed as e:
        # Handle 405 Method Not Allowed
        return MockResponse(web.Response(status=405, text=str(e)))
    except web.HTTPNotFound as e:
        # Handle 404 Not Found
        return MockResponse(web.Response(status=404, text=str(e)))
    except Exception as e:
        # If handling fails, return 404
        return MockResponse(web.Response(status=404, text=f"Not Found: {e}"))
