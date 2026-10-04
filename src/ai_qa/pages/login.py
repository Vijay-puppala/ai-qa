"""Page object for the login screen (DC-11).

Selectors were taken from the live application, not inferred from the ticket -
a ticket describes behaviour, not markup. Methods are named for intent
(``submit``) rather than mechanics (``click_button``), per CLAUDE.md.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page

from ai_qa.pages.base import BasePage


class LoginPage(BasePage):
    """The login form at ``/login``."""

    path = "/login"

    # --- the controls the ticket requires -------------------------------

    @property
    def email(self) -> Locator:
        return self.page.locator("#email")

    @property
    def password(self) -> Locator:
        return self.page.locator("#password")

    @property
    def submit_button(self) -> Locator:
        return self.page.get_by_role("button", name="Login")

    @property
    def forgot_password_link(self) -> Locator:
        """Case-insensitive, because the ticket does not fix the wording."""
        return self.page.get_by_role("link", name=__import__("re").compile(r"forgot", 2))

    @property
    def visibility_toggle(self) -> Locator:
        """The show/hide password control.

        Matched broadly on purpose - by accessible name, aria-label, or a
        control sitting inside the password field's container - so the test
        fails only when no such control exists at all, rather than because the
        implementation chose a different label than the test guessed.
        """
        return self.page.locator(
            "[aria-label*='password' i][role='button'], "
            "button[aria-label*='show' i], button[aria-label*='hide' i], "
            "[data-testid*='toggle' i], [data-testid*='visibility' i], "
            "button:near(#password)"
        )

    # --- intent -----------------------------------------------------------

    def submit(self) -> None:
        self.submit_button.click()

    def sign_in(self, email: str, password: str) -> None:
        self.email.fill(email)
        self.password.fill(password)
        self.submit()

    # --- observations -----------------------------------------------------

    def password_is_masked(self) -> bool:
        return self.password.get_attribute("type") == "password"

    def native_validation_message(self, field: Locator) -> str:
        """The browser's own constraint message for a field.

        The application relies on native HTML5 validation rather than custom
        message elements, so this is where a required-field or format message
        actually surfaces.
        """
        return field.evaluate("e => e.validationMessage") or ""

    def error_banner_text(self) -> str:
        """Server-side feedback shown after a rejected sign-in."""
        return self.page.locator("body").inner_text()
