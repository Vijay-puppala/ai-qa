"""Page-object base class (FR-017).

Deliberately minimal. No application under test is known yet, so anything
beyond navigation and a typed handle on the page would be inventing an
abstraction with no caller.
"""

from __future__ import annotations

from playwright.sync_api import Page


class BasePage:
    """Common behaviour for page objects.

    Subclasses declare their own locators and expose intent-named methods
    (``submit_login``, not ``click_button``), so a recorded ``codegen`` draft
    gets refactored into something that survives a UI change.
    """

    #: Path appended to the configured base URL. Subclasses override.
    path: str = "/"

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")

    @property
    def url(self) -> str:
        return f"{self.base_url}/{self.path.lstrip('/')}"

    def open(self) -> "BasePage":
        """Navigate to this page and return self for chaining."""
        self.page.goto(self.url)
        return self
